import re

class VisualizationService:
    def get_visualization_data(self, analysis_result, sentence):
        """
        분석 결과와 원본 문장을 받아 시각화에 필요한 데이터 구조를 생성합니다.
        
        Args:
            analysis_result (list): 형태소 분석 및 등급 분석 결과 리스트
            sentence (str): 원본 문장
            
        Returns:
            tuple: (visualization_data, text_segments)
                - visualization_data (dict): 차트용 데이터 (labels, data)
                - text_segments (list): 텍스트 하이라이팅용 세그먼트 리스트
        """
        grade_counts = {f"{i}급": 0 for i in range(1, 7)}
        text_segments = []
        
        # 차트 데이터 집계
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
        
        # 텍스트 세그먼트 생성 (하이라이팅용)
        # UI 효율성을 위해 유니크 ID 부여
        for i, item in enumerate(analysis_result):
            item['_ui_id'] = f"seg-{i}-{item.get('offset_start', 0)}"
        
        # 오프셋 기준 정렬
        sorted_analysis = sorted(analysis_result, key=lambda x: x.get('offset_start', -1))
        current_cursor = 0
        
        for item in sorted_analysis:
            start = item.get('offset_start')
            length = item.get('offset_len')
            
            if start is None or length is None: continue
            
            # 분석되지 않은 앞부분 텍스트 처리 (일반 텍스트)
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
            
        # 남은 뒷부분 텍스트 처리    
        if current_cursor < len(sentence):
            text_segments.append({
                "text": sentence[current_cursor:],
                "type": "plain"
            })
            
        return visualization_data, text_segments

    def create_chart_data_from_stats(self, grade_stats):
        """
        등급 통계(grade_stats) 딕셔너리를 받아 Chart.js용 visualization_data로 변환합니다.
        
        Args:
            grade_stats (dict): { "1급": 10, "2급": 5, ... } 형태의 통계
            
        Returns:
            dict: { "labels": [...], "data": [...] }
        """
        return {
            "labels": [k for k, v in grade_stats.items() if v > 0],
            "data": [v for v in grade_stats.values() if v > 0]
        }
