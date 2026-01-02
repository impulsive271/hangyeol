from flask import Blueprint, render_template, request, send_file
import io
import pandas as pd
import re
from services.analysis_service import AnalysisService
from services.generation_service import GenerationService

main_bp = Blueprint('main', __name__)

analysis_service = AnalysisService()
generation_service = GenerationService()

@main_bp.route("/")
def index():
    return render_template("index.html")

@main_bp.route("/grade", methods=["GET", "POST"])
def grade():
    graded_text = None
    analysis_result = [] 
    last_sentence = ""
    debug_log = "" 
    visualization_data = {}
    text_segments = []

    if request.method == "POST":
        last_sentence = request.form.get("sentence", "")
        graded_text, analysis_result, debug_log = analysis_service.get_sentence_grade(last_sentence)
        visualization_data, text_segments = analysis_service.get_visualization_data(analysis_result, last_sentence)

    return render_template("grade.html", 
                           graded_text=graded_text, 
                           analysis_result=analysis_result, 
                           last_sentence=last_sentence,
                           debug_log=debug_log,
                           visualization_data=visualization_data,
                           text_segments=text_segments)

@main_bp.route("/grade/upload", methods=["POST"])
def grade_upload():
    if 'file' not in request.files: return "파일 없음", 400
    file = request.files['file']
    if file.filename == '': return "파일 이름 없음", 400
    
    if file:
        try:
            processed_data = []

            # A. 텍스트 파일 (.txt) 
            if file.filename.lower().endswith('.txt'):
                content = file.read().decode('utf-8')
                sentences = re.split(r'(?<=[.?!])\s+', content)
                clean_sentences = [s.strip() for s in sentences if s.strip()]

                for sentence in clean_sentences:
                    grade_result, analysis_list, _ = analysis_service.get_sentence_grade(sentence)
                    processed_data.append({
                        "일괄 판독문장": sentence,
                        "판독등급": grade_result,
                        "상세로그": str(analysis_list) 
                    })

            # B. 엑셀/CSV 파일 (.xlsx, .csv)
            else:
                df = pd.read_excel(file) if file.filename.endswith('.xlsx') else pd.read_csv(file, encoding='utf-8')
                target_col = next((c for c in df.columns if '문장' in str(c) or 'sentence' in str(c).lower()), df.columns[0])
                
                for _, row in df.iterrows():
                    sentence = str(row[target_col])
                    grade_result, analysis_list, _ = analysis_service.get_sentence_grade(sentence)
                    processed_data.append({
                        "일괄 판독문장": sentence,
                        "판독등급": grade_result,
                        "상세로그": str(analysis_list)
                    })
            
            result_df = pd.DataFrame(processed_data)
            result_df = result_df[['일괄 판독문장', '판독등급', '상세로그']]

            output = io.BytesIO()
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

@main_bp.route("/generate", methods=["GET", "POST"])
def generate():
    final_sentence = ""
    final_analysis = []
    final_grade = ""
    rejected_history = [] 
    visualization_data = None
    text_segments = None
    
    if request.method == "POST":
        grades = request.form.getlist("grades")
        keyword = request.form.get("keyword", "").strip()
        hint = request.form.get("hint", "").strip()
        
        final_sentence, final_analysis, final_grade, rejected_history = generation_service.generate_with_validation(
            grades, keyword, hint, analysis_service
        )

    if final_sentence:
        visualization_data, text_segments = analysis_service.get_visualization_data(final_analysis, final_sentence)

    return render_template(
        "generate.html", 
        generated_sentence=final_sentence,
        analysis_result=final_analysis,
        final_grade=final_grade,
        rejected_history=rejected_history,
        visualization_data=visualization_data,
        text_segments=text_segments
    )

@main_bp.route("/quiz")
def quiz():
    return render_template("quiz.html")

@main_bp.route("/quiz/matching")
def quiz_matching():
    return render_template("matching_quiz.html")
