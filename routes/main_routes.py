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
    file_stats_list = []
    analysis_result = [] 
    last_sentence = ""
    debug_log = "" 
    visualization_data = {}
    text_segments = []
    file_text_contents = [] # [FIX] Initialize for GET requests

    if request.method == "POST":
        last_sentence = request.form.get("sentence", "")
        grade_stats, analysis_result, debug_log = analysis_service.get_sentence_grade(last_sentence)
        
        # [MODIFIED] 직접 입력 시에도 파일명 '직접 입력'으로 통일
        file_stats_list = [{'filename': '직접 입력', 'stats': grade_stats}]
        for item in analysis_result:
            item['filename'] = '직접 입력'
            
        visualization_data, text_segments = analysis_service.get_visualization_data(analysis_result, last_sentence)
        file_text_contents = [{'filename': '직접 입력', 'segments': text_segments}]

    return render_template("grade.html", 
                           file_stats_list=file_stats_list, 
                           analysis_result=analysis_result, 
                           last_sentence=last_sentence,
                           debug_log=debug_log,
                           visualization_data=visualization_data,
                           file_text_contents=file_text_contents)

@main_bp.route("/grade/upload", methods=["POST"])
def grade_upload():
    if 'file' not in request.files: return "파일 없음", 400
    
    files = request.files.getlist('file')
    if not files or files[0].filename == '': return "파일 이름 없음", 400
    
    file_stats_list = []
    combined_analysis_result = []
    combined_text = []
    full_debug_log = ""

    try:
        # [NEW] 파일별 텍스트 세그먼트 및 종합 데이터 집계
        file_text_contents = []
        overall_grade_counts = {f"{i}급": 0 for i in range(1, 7)}
        overall_grade_counts["등급 없음"] = 0 # [NEW] 등급 없음 추가

        for file in files:
            if not file: continue
            filename = file.filename
            
            # 파일에서 텍스트 추출
            extracted_text = file_service.extract_text_from_file(file)
            
            # 분석 실행
            grade_stats, analysis_result, debug_log = analysis_service.get_sentence_grade(extracted_text)
            
            # [NEW] 파일별 통계 저장
            file_stats_list.append({'filename': filename, 'stats': grade_stats})
            
            # [NEW] 분석 결과에 파일명 추가
            for item in analysis_result:
                item['filename'] = filename
                
            combined_analysis_result.extend(analysis_result)
            combined_text.append(f"[{filename}]\n{extracted_text}")
            full_debug_log += f"--- {filename} ---\n{debug_log}\n"

            # [NEW] 개별 파일 시각화 데이터 생성 (텍스트 세그먼트용)
            # Pie Chart용 카운트 누적
            _, temp_segments = analysis_service.get_visualization_data(analysis_result, extracted_text)
            file_text_contents.append({
                'filename': filename,
                'segments': temp_segments
            })
            
            # 종합 원그래프용 데이터 누적
            for k, v in grade_stats.items():
                if k in overall_grade_counts:
                    overall_grade_counts[k] += v

        full_extracted_text = "\n\n".join(combined_text)
        
        # 종합 Pie Chart 데이터 재구성
        visualization_data = {
            "labels": [k for k, v in overall_grade_counts.items() if v > 0],
            "data": [v for v in overall_grade_counts.values() if v > 0]
        }
        
        # grade.html 렌더링
        return render_template("grade.html", 
                       file_stats_list=file_stats_list, 
                       analysis_result=combined_analysis_result, 
                       last_sentence=full_extracted_text,
                       debug_log=full_debug_log,
                       visualization_data=visualization_data,
                       file_text_contents=file_text_contents)  # [NEW] 전달

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
        rejected_history=rejected_history,
        visualization_data=visualization_data,
        text_segments=text_segments,
        file_stats_list=[] # [FIX] Add empty list to prevent template error
    )

@main_bp.route("/quiz")
def quiz():
    return render_template("quiz.html")

@main_bp.route("/quiz/matching")
def quiz_matching():
    return render_template("matching_quiz.html")
