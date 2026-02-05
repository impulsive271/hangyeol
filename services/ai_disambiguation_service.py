import json

class AIDisambiguationService:
    def disambiguate(self, client, model_name, sentence, ambiguous_items):
        """
        AI를 사용하여 모호한 단어들의 의미를 결정합니다.
        
        :param client: AI API Client
        :param model_name: AI 모델명
        :param sentence: 문맥 문장
        :param ambiguous_items: 모호한 항목 리스트
        :return: (결과 dict, raw_response)
        """
        if not client or not ambiguous_items: return {}, "AI 미사용"
        
        prompt = f"""
        당신은 한국어 어휘 분석 전문가입니다. 주어진 문맥을 바탕으로 동음이의어의 가장 적절한 의미를 판단하세요.
        문맥: "{sentence}"
        
        [분석 대상 목록]
        """
        for i, item in enumerate(ambiguous_items):
            # 0-Index를 1-Index로 변환하여 표시 (사용자/AI 친화적)
            idx = i + 1
            options = []
            for cand in item['candidates']:
                desc = cand.get('desc') or cand.get('meaning') or "의미 정보 없음"
                options.append(f"(ID:{cand['uid']}) {desc}")
            
            options_str = ", ".join(options)
            prompt += f"[{idx}] 단어: '{item['word']}' -> 후보: [{options_str}]\n"
            
        prompt += """
        [출력 규칙]
        1. 오직 JSON 형식으로만 응답하세요. (마크다운 코드 블록 ```json 사용 금지)
        2. Key는 위 목록의 [번호]를 문자열로 사용하세요. (예: "1", "2")
        3. Value는 선택한 ID 값(문자열)만 넣으세요.
        4. 예시: {"1": "272", "2": "677"}
        """
        
        raw_response = ""
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            raw_response = response.text
            
            clean_json_str = raw_response.replace('```json', '').replace('```', '').strip()
            if clean_json_str.endswith(',') or clean_json_str.endswith(',}'): 
                 clean_json_str = clean_json_str.rstrip(',}') + "}"
                 
            ai_data = json.loads(clean_json_str)
            return ai_data, raw_response

        except Exception as e:
            error_msg = f"Error: {e} | Raw: {raw_response}"
            return {}, error_msg
