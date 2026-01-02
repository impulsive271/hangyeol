from flask import Blueprint, render_template, request, send_file
from services.analysis_service import AnalysisService
from services.generation_service import GenerationService

from services.file_processing_service import FileProcessingService

main_bp = Blueprint('main', __name__)

analysis_service = AnalysisService()
generation_service = GenerationService()
file_service = FileProcessingService()

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
            # 파일에서 텍스트 추출
            extracted_text = file_service.extract_text_from_file(file)
            
            # 분석 실행
            graded_text, analysis_result, debug_log = analysis_service.get_sentence_grade(extracted_text)
            visualization_data, text_segments = analysis_service.get_visualization_data(analysis_result, extracted_text)
            
            # grade.html 렌더링 (텍스트 입력창에 추출된 내용 채움)
            return render_template("grade.html", 
                           graded_text=graded_text, 
                           analysis_result=analysis_result, 
                           last_sentence=extracted_text,
                           debug_log=debug_log,
                           visualization_data=visualization_data,
                           text_segments=text_segments)

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
