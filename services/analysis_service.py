import re
import json
from google import genai
from config import Config
from services.morph_service import MorphService
from services.grade_database import GradeDatabase
from services.grade_profiler import GradeProfiler

class AnalysisService:
    def __init__(self):
        self.morph = MorphService()
        self.data = GradeDatabase()
        self.profiler = GradeProfiler(self.data)
        self.client = None
        self.model_name = Config.GEMINI_MODEL_NAME
        self._init_ai()
    
    def _init_ai(self):
        api_key = Config.GOOGLE_API_KEY
        if api_key:
            try:
                self.client = genai.Client(api_key=api_key)
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
        analysis_data, max_level, debug_log = self.profiler.profile(
            tokens, 
            sentence, 
            client=self.client,
            model_name=self.model_name
        )

        # [MODIFIED] 단순 등급 산정 대신 빈도수 집계
        grade_stats = {f"{i}급": 0 for i in range(1, 7)}
        grade_stats["등급 없음"] = 0
        grade_stats["기타"] = 0
        grade_stats["전체"] = 0 # [NEW] 합계 (문장부호 제외, 숫자 포함)
        
        for item in analysis_data:
            lvl = item.get('level', '')
            tag = item.get('tag_code', '')
            
            # [NEW] 문장 부호(S로 시작) 처리
            if tag and tag.startswith('S'):
                grade_stats["기타"] += 1
                
                # [NEW] 숫자(SN)는 합계에 포함, 나머지는 제외
                if tag == 'SN':
                    grade_stats["전체"] += 1
                
                continue
            
            # S로 시작하지 않는 단어들은 모두 합계에 포함
            grade_stats["전체"] += 1

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



