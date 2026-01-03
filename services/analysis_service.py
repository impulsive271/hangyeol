import re
import json
import google.generativeai as genai
from config import Config
from services.morph_service import MorphService
from services.grade_database import GradeDatabase
from services.grade_profiler import GradeProfiler

class AnalysisService:
    def __init__(self):
        self.morph = MorphService()
        self.data = GradeDatabase()
        self.profiler = GradeProfiler(self.data)
        self.model = None
        self._init_ai()
    
    def _init_ai(self):
        api_key = Config.GOOGLE_API_KEY
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(
                    "models/gemini-2.0-flash-lite-preview-02-05",
                    generation_config={"response_mime_type": "application/json"}
                )
            except Exception as e:
                print(f"⚠️ AnalysisService AI Init Failed: {e}")

    def get_sentence_grade(self, sentence: str):
        if not self.data.is_ready: return "분석 불가", [], "데이터 로드 실패"
        if self.morph.use_mock or not self.morph.analyzer: return "분석 불가", [], "Kiwi 로드 실패"
        
        try:
            res = self.morph.analyze(sentence)
            tokens = res[0][0]
        except Exception as e: return "분석 에러", [], f"Kiwi 분석 오류: {str(e)}"

        # Delegate to GradeProfiler
        analysis_data, max_level, debug_log = self.profiler.profile(tokens, sentence, self.model)

        # [MODIFIED] 단순 등급 산정 대신 빈도수 집계
        grade_stats = {f"{i}급": 0 for i in range(1, 7)}
        grade_stats["등급 없음"] = 0
        grade_stats["기타"] = 0
        
        for item in analysis_data:
            lvl = item.get('level', '')
            tag = item.get('tag_code', '')
            
            # [NEW] 문장 부호(S로 시작) 등은 '기타'로 분류
            if tag and tag.startswith('S'):
                grade_stats["기타"] += 1
                continue

            if lvl and '급' in lvl:
                # "1급", "1~2급" 등 처리 (심플하게 첫 숫자 기준)
                found = re.search(r'([1-6])급', lvl)
                if found:
                    grade_stats[f"{found.group(1)}급"] += 1
                else:
                    grade_stats["등급 없음"] += 1
            else:
                 grade_stats["등급 없음"] += 1

        # Use grade_stats as the first return value instead of single grade string
        return grade_stats, analysis_data, debug_log

    def analyze_morphs(self, sentence):
        if not self.morph.analyzer: return []
        res = self.morph.analyze(sentence)
        tokens = res[0][0]
        return [{'form': t.form, 'tag': t.tag} for t in tokens]

    def get_visualization_data(self, analysis_result, sentence):
        grade_counts = {f"{i}급": 0 for i in range(1, 7)}
        text_segments = []
        
        for item in analysis_result:
            lvl = item.get('level', '')
            if '급' in lvl:
                full_lvl_str = re.sub(r'[^0-9]', '', lvl)
                if full_lvl_str and f"{full_lvl_str}급" in grade_counts:
                    grade_counts[f"{full_lvl_str}급"] += 1

        visualization_data = {
            "labels": [k for k, v in grade_counts.items() if v > 0],
            "data": [v for v in grade_counts.values() if v > 0]
        }
        
        for i, item in enumerate(analysis_result):
            item['_ui_id'] = f"seg-{i}-{item.get('offset_start', 0)}"
        
        sorted_analysis = sorted(analysis_result, key=lambda x: x.get('offset_start', -1))
        current_cursor = 0
        
        for item in sorted_analysis:
            start = item.get('offset_start')
            length = item.get('offset_len')
            
            if start is None or length is None: continue
            
            if start > current_cursor:
                text_segments.append({
                    "text": sentence[current_cursor:start],
                    "type": "plain"
                })
            
            grade_class = "text-grade-none"
            lvl = item.get('level', '')
            if '급' in lvl:
                num = re.sub(r'[^0-9]', '', lvl)
                if num: grade_class = f"text-grade-{num}"
            
            text_segments.append({
                "text": item['form'],
                "type": "graded",
                "class": grade_class,
                "info": item 
            })
            
            current_cursor = max(current_cursor, start + length)
            
        if current_cursor < len(sentence):
            text_segments.append({
                "text": sentence[current_cursor:],
                "type": "plain"
            })
            
        return visualization_data, text_segments

    def analyze_morphs(self, sentence):
        if not self.morph.analyzer: return []
        res = self.morph.analyze(sentence)
        tokens = res[0][0]
        return [{'form': t.form, 'tag': t.tag} for t in tokens]

    def get_visualization_data(self, analysis_result, sentence):
        grade_counts = {f"{i}급": 0 for i in range(1, 7)}
        text_segments = []
        
        for item in analysis_result:
            lvl = item.get('level', '')
            if '급' in lvl:
                full_lvl_str = re.sub(r'[^0-9]', '', lvl)
                if full_lvl_str and f"{full_lvl_str}급" in grade_counts:
                    grade_counts[f"{full_lvl_str}급"] += 1

        visualization_data = {
            "labels": [k for k, v in grade_counts.items() if v > 0],
            "data": [v for v in grade_counts.values() if v > 0]
        }
        
        for i, item in enumerate(analysis_result):
            item['_ui_id'] = f"seg-{i}-{item.get('offset_start', 0)}"
        
        sorted_analysis = sorted(analysis_result, key=lambda x: x.get('offset_start', -1))
        current_cursor = 0
        
        for item in sorted_analysis:
            start = item.get('offset_start')
            length = item.get('offset_len')
            
            if start is None or length is None: continue
            
            if start > current_cursor:
                text_segments.append({
                    "text": sentence[current_cursor:start],
                    "type": "plain"
                })
            
            grade_class = "text-grade-none"
            lvl = item.get('level', '')
            if '급' in lvl:
                num = re.sub(r'[^0-9]', '', lvl)
                if num: grade_class = f"text-grade-{num}"
            
            text_segments.append({
                "text": item['form'],
                "type": "graded",
                "class": grade_class,
                "info": item 
            })
            
            current_cursor = max(current_cursor, start + length)
            
        if current_cursor < len(sentence):
            text_segments.append({
                "text": sentence[current_cursor:],
                "type": "plain"
            })
            
        return visualization_data, text_segments
