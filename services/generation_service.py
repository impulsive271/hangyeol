import google.generativeai as genai
from config import Config

class GenerationService:
    def __init__(self):
        self.model = None
        self._init_ai()

    def _init_ai(self):
        api_key = Config.GOOGLE_API_KEY
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self.model = genai.GenerativeModel(
                    "models/gemini-2.0-flash-lite-preview-02-05",
                    generation_config={"response_mime_type": "text/plain"} # Default to text
                )
            except Exception as e:
                print(f"⚠️ GenerationService AI Init Failed: {e}")

    def generate_ai_sentence(self, grades, keyword, hint=""):
        if not self.model: return "오류: AI 모델이 초기화되지 않았습니다."

        prompt = "당신은 한국어 어휘 및 난이도 전문 출제위원입니다.\n다음 조건에 맞춰 학습용 예문을 단 하나만 작성하세요.\n"
        
        target_levels = [int(g) for g in grades if g.isdigit()] if grades and "all" not in grades else []
        
        if target_levels:
            max_lvl = max(target_levels)
            prompt += f"\n[난이도 목표]: TOPIK {max_lvl}급 이하 (엄격 준수)\n"
            
            if max_lvl <= 2:
                prompt += "- 어휘: 기초적인 생활 어휘만 사용하세요.\n"
                prompt += "- 문장 구조: 단문 위주의 아주 짧고 단순한 문장 (길이 최소화).\n"
                prompt += "- 문법: 연결 어미나 파생어를 피하고, 아주 기본적인 조사만 사용하세요.\n"
            elif max_lvl <= 4:
                prompt += "- 어휘: 일상무 주제의 중급 어휘 사용.\n"
                prompt += "- 문장 구조: 너무 복잡한 수식어구는 피하세요.\n"
            else:
                prompt += "- 어휘: 고급 어휘와 추상적 표현 사용 가능.\n"
        else:
            prompt += "- 난이도: 자연스러운 한국어 문장\n"

        if keyword:
            hint_str = f" (문맥 힌트: {hint})" if hint and hint != 'nan' else ""
            prompt += f"\n- 필수 포함 단어: '{keyword}'{hint_str}\n  * 주의: 형태를 변형하지 말고 그대로 포함하세요.\n"
        
        prompt += "\n[출력 제약사항]\n1. 설명 금지, 오직 예문 1개만 출력.\n2. 마크다운, 따옴표, 불필요한 기호 사용 금지.\n3. 반드시 한국어 마침표(.)로 끝낼 것."
        
        try:
            return self.model.generate_content(prompt).text.strip().replace("**", "").replace('"', "")
        except Exception as e: return f"오류: {str(e)}"

    def generate_with_validation(self, grades, keyword, hint, analysis_service):
        import re 
        
        target_max_level = 6
        if "all" not in grades and grades:
            try:
                target_max_level = max([int(g) for g in grades])
            except: pass
            
        max_retries = 5
        current_try = 0
        forbidden_words = [] 
        
        final_sentence = ""
        final_analysis = []
        final_grade = ""
        rejected_history = []

        while current_try < max_retries:
            current_hint = hint
            if forbidden_words:
                current_hint += f" (절대 사용 금지 단어: {', '.join(forbidden_words)})"
            
            temp_sentence = self.generate_ai_sentence(grades, keyword, current_hint)
            
            if "오류" in temp_sentence:
                final_sentence = temp_sentence
                break 

            # 검증 (AnalysisService 사용)
            temp_grade_str, temp_analysis, _ = analysis_service.get_sentence_grade(temp_sentence)
            
            violation_found = False
            violation_words = []

            if "all" not in grades:
                for item in temp_analysis:
                    if '급' in item['level']:
                        try:
                            level_num = int(re.sub(r'[^0-9]', '', item['level']))
                            if level_num > target_max_level:
                                violation_found = True
                                violation_words.append(f"{item['form']}({item['level']})")
                                if item['form'] not in forbidden_words:
                                    forbidden_words.append(item['form'])
                        except: pass
            
            if not violation_found:
                final_sentence = temp_sentence
                final_analysis = temp_analysis
                final_grade = temp_grade_str
                break
            else:
                rejected_history.append({
                    'sentence': temp_sentence,
                    'reason': f"등급 초과 단어 발견: {', '.join(violation_words)}"
                })
                current_try += 1
        
        if not final_sentence and rejected_history:
            print("모든 생성 시도 실패 (Strict Validation)")
            
        return final_sentence, final_analysis, final_grade, rejected_history
