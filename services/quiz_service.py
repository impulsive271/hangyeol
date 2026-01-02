import google.generativeai as genai
import json
from config import Config

class QuizService:
    def __init__(self):
        self.model = None
        self._init_ai()

    def _init_ai(self):
        api_key = Config.GOOGLE_API_KEY
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(
                    "models/gemini-2.0-flash-lite-preview-02-05", # Quiz might need smarter model? Stick to existing.
                    generation_config={"response_mime_type": "application/json"}
                )
            except Exception as e:
                print(f"⚠️ QuizService AI Init Failed: {e}")

    def generate_quiz_item(self, target, level, quiz_type, context_sentence, user_prompt=""):
        if not self.model: return {"error": "AI 모델 미초기화"}

        type_desc = "양자택일(Binary Choice)" if quiz_type == 'binary' else "4지선다(Multiple Choice)"
        
        custom_instruction = ""
        if user_prompt:
            custom_instruction = f"\n[사용자 특별 요청사항]: {user_prompt} (이 요청을 최우선으로 반영할 것)\n"

        if context_sentence:
            clean_target = target.split(' (')[0] if '(' in target else target
            prompt = f"""당신은 한국어 선생님입니다.
원문: "{context_sentence}"
정답: "{clean_target}"
유형: {type_desc}
난이도: {level}급
{custom_instruction}
지시: 1. 정답을 빈칸(____)으로 처리하여 퀴즈 질문 문장(question_text)을 완성하세요. 
2. question_text에는 빈칸이 포함된 불완전한 문장만 넣으세요.
출력 포맷(JSON): {{"question_text": "...", "options": ["..."], "answer_index": 0, "explanation": "..."}}"""
        else:
            prompt = f"""한국어 문제 출제자입니다.
단어: '{target}' 활용
난이도: {level}급
유형: {type_desc}
{custom_instruction}
지시: 1. 정답을 빈칸(____)으로 처리하여 퀴즈 질문 문장(question_text)을 완성하세요. 
2. question_text에는 빈칸이 포함된 불완전한 문장만 넣으세요.
출력 포맷(JSON): {{"question_text": "...", "options": ["..."], "answer_index": 0, "explanation": "..."}}"""
            
        try:
            raw_response = self.model.generate_content(prompt).text
            
            clean_json_str = raw_response.strip().replace("```json", "").replace("```", "")
            clean_json_str = clean_json_str.replace('\n', '').replace('\t', '') 

            start_index = clean_json_str.find('{')
            end_index = clean_json_str.rfind('}')
            if start_index != -1 and end_index != -1 and start_index < end_index:
                 clean_json_str = clean_json_str[start_index : end_index + 1]

            return json.loads(clean_json_str)
            
        except Exception as e: 
            return {"error": "AI 생성 실패: JSON 파싱 오류", "details": str(e), "raw_data": raw_response}

    def generate_matching_quiz(self, input_words):
        # Used for /api/generate-matching
        if not self.model: return {"status": "error", "message": "AI 모델 미초기화"}

        prompt = f"""
        당신은 한국어 교육 전문가입니다. 다음 요청에 따라 '단어-뜻 연결 퀴즈' 데이터를 JSON으로 만들어주세요.

        1. 입력된 단어: {input_words}
        2. 목표:
           - 입력된 단어를 포함하여 총 3~4개의 단어가 되도록 하세요.
           - 추가되는 단어는 입력된 단어와 난이도(초급/중급)나 주제가 비슷한 것으로 선정하세요.
           - 각 단어의 뜻을 외국인 학습자가 이해하기 쉽게 한국어 한 문장으로 간결하게 풀이하세요.
        3. 출력 형식 (JSON 리스트만 출력, 마크다운 코드블록 제외):
        [
            {{"id": "word_1", "word": "입력단어", "meaning": "쉬운 뜻풀이"}},
            {{"id": "word_2", "word": "추가단어", "meaning": "쉬운 뜻풀이"}},
            {{"id": "word_3", "word": "추가단어", "meaning": "쉬운 뜻풀이"}}
        ]
        """

        try:
            response = self.model.generate_content(prompt)
            text_response = response.text.replace('```json', '').replace('```', '').strip()
            quiz_data = json.loads(text_response)
            return {"status": "success", "data": quiz_data}

        except Exception as e:
            return {"status": "error", "message": str(e)}
