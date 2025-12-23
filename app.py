from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
import io
import os
import pandas as pd
from dotenv import load_dotenv
import google.generativeai as genai
from logic import SentenceGrader
import re
import json # [NEW] JSON 처리를 위해 추가

# 1. 설정
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

if api_key:
    genai.configure(api_key=api_key)
    # [설정] 태현님의 요청대로 2.5 Flash 고정
    model = genai.GenerativeModel("models/gemini-2.5-flash")
else:
    model = None

app = Flask(__name__)
app.secret_key = 'hangyeol_secret_key'

# 2. 로직 연결
grader = SentenceGrader()

@app.route("/")
def index():
    return render_template("index.html")

# --- 기능 1: 문장 등급 판독 ---
@app.route("/grade", methods=["GET", "POST"])
def grade():
    graded_text = None
    analysis_result = [] 
    last_sentence = ""
    debug_log = "" 

    if request.method == "POST":
        last_sentence = request.form.get("sentence", "")
        graded_text, analysis_result, debug_log = grader.get_sentence_grade(last_sentence)

    return render_template("grade.html", 
                           graded_text=graded_text, 
                           analysis_result=analysis_result, 
                           last_sentence=last_sentence,
                           debug_log=debug_log)

@app.route("/grade/upload", methods=["POST"])
def grade_upload():
    if 'file' not in request.files: return "파일 없음", 400
    file = request.files['file']
    if file.filename == '': return "파일 이름 없음", 400
    
    if file:
        try:
            # 결과를 담을 리스트
            processed_data = []

            # A. 텍스트 파일 (.txt) 처리 로직 - [요청하신 부분]
            if file.filename.lower().endswith('.txt'):
                # 1. 파일 읽기 (UTF-8)
                content = file.read().decode('utf-8')
                
                # 2. 문장 부호(.?!) 기준으로 분할 (공백 처리 포함)
                # (?<=[.?!]) : 문장 부호 뒤에서 자르되, 부호는 앞 문장에 포함
                sentences = re.split(r'(?<=[.?!])\s+', content)
                
                # 3. 빈 문장 제거 및 리스트화
                clean_sentences = [s.strip() for s in sentences if s.strip()]

                # 4. 각 문장 판독
                for sentence in clean_sentences:
                    grade_result, analysis_list, _ = grader.get_sentence_grade(sentence)
                    processed_data.append({
                        "일괄 판독문장": sentence,
                        "판독등급": grade_result,
                        "상세로그": str(analysis_list) # 분석 데이터를 문자열로 변환하여 저장
                    })

            # B. 엑셀/CSV 파일 (.xlsx, .csv) 처리 로직 - [기존 호환]
            else:
                df = pd.read_excel(file) if file.filename.endswith('.xlsx') else pd.read_csv(file, encoding='utf-8')
                # 대상 컬럼 찾기 ('문장' 또는 'sentence'가 포함된 컬럼, 없으면 첫 번째 컬럼)
                target_col = next((c for c in df.columns if '문장' in str(c) or 'sentence' in str(c).lower()), df.columns[0])
                
                for _, row in df.iterrows():
                    sentence = str(row[target_col])
                    grade_result, analysis_list, _ = grader.get_sentence_grade(sentence)
                    processed_data.append({
                        "일괄 판독문장": sentence,
                        "판독등급": grade_result,
                        "상세로그": str(analysis_list)
                    })
            
            # 5. 결과 DataFrame 생성 및 내보내기
            result_df = pd.DataFrame(processed_data)
            
            # 컬럼 순서 강제 지정 (혹시 모를 순서 섞임 방지)
            result_df = result_df[['일괄 판독문장', '판독등급', '상세로그']]

            output = io.BytesIO()
            # 한글 깨짐 방지를 위해 utf-8-sig 사용
            result_df.to_csv(output, index=False, encoding='utf-8-sig')
            output.seek(0)
            
            return send_file(
                output, 
                mimetype='text/csv', 
                as_attachment=True, 
                download_name='graded_result.csv'
            )

        except Exception as e:
            return f"파일 처리 중 오류 발생: {e}", 500

# --- 기능 2: 문장 생성 ---
@app.route("/generate", methods=["GET", "POST"])
def generate():
    final_sentence = ""
    final_analysis = []
    final_grade = ""
    rejected_history = [] 
    
    if request.method == "POST":
        grades = request.form.getlist("grades")
        keyword = request.form.get("keyword", "").strip()
        hint = request.form.get("hint", "").strip()
        
        target_max_level = 6 
        if "all" not in grades and grades:
            try:
                target_max_level = max([int(g) for g in grades])
            except: pass
            
        max_retries = 3
        current_try = 0
        forbidden_words = [] 

        while current_try < max_retries:
            current_hint = hint
            if forbidden_words:
                current_hint += f" (절대 사용 금지 단어: {', '.join(forbidden_words)})"
            
            temp_sentence = grader.generate_ai_sentence(model, grades, keyword, current_hint)
            
            if "오류" in temp_sentence:
                final_sentence = temp_sentence
                break 

            temp_grade_str, temp_analysis, _ = grader.get_sentence_grade(temp_sentence)
            
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
            final_sentence = rejected_history[-1]['sentence']
            final_grade, final_analysis, _ = grader.get_sentence_grade(final_sentence)

    return render_template(
        "generate.html", 
        generated_sentence=final_sentence,
        analysis_result=final_analysis,
        final_grade=final_grade,
        rejected_history=rejected_history
    )

@app.route("/api/search")
def search_keyword():
    query = request.args.get("q", "").strip()
    search_type = request.args.get("type", "word")
    return jsonify(grader.search_keyword(query, search_type))

# --- 기능 3: 퀴즈 (기존) ---
@app.route("/quiz")
def quiz():
    return render_template("quiz.html")

@app.route('/analyze_sentence_for_quiz', methods=['POST'])
def analyze_sentence_for_quiz():
    data = request.json
    try:
        res = grader.analyzer.analyze(data.get('sentence', ''))
        tokens = res[0][0] 
        morphs = [{'form': t.form, 'tag': t.tag} for t in tokens]
        return jsonify({'morphs': morphs})
    except Exception as e:
        return jsonify({'error': str(e)})

@app.route('/generate_quiz_action', methods=['POST'])
def generate_quiz_action():
    data = request.json
    max_grade = max([int(g) for g in data.get('grades', [])] or [1])
    quiz_type = data.get('quiz_type', 'binary')
    target = data.get('target', '') 
    context = data.get('context', '')
    user_prompt = data.get('user_prompt', '') 

    if not model: return jsonify({"error": "API 키 없음"})
    
    return jsonify(grader.generate_quiz_item(model, target, max_grade, quiz_type, context, user_prompt))

# --- [NEW] 기능 4: 선 잇기 (Matching Quiz) ---

# 1. 페이지 렌더링
@app.route("/quiz/matching")
def quiz_matching():
    # templates/matching_quiz.html 파일이 있어야 합니다.
    return render_template("matching_quiz.html")

# 2. 문제 생성 API
@app.route('/api/generate-matching', methods=['POST'])
def generate_matching_quiz():
    data = request.json
    input_words = data.get('words', []) # 예: ['사과', '바다']

    # AI 프롬프트 구성
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
        # 모델 생성 요청
        response = model.generate_content(prompt)
        # 텍스트 전처리 (마크다운 제거)
        text_response = response.text.replace('```json', '').replace('```', '').strip()
        quiz_data = json.loads(text_response)
        
        return jsonify({"status": "success", "data": quiz_data})

    except Exception as e:
        print(f"매칭 퀴즈 생성 오류: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)