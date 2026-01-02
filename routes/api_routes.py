from flask import Blueprint, request, jsonify
from services.corpus_service import CorpusService
from services.analysis_service import AnalysisService
from services.quiz_service import QuizService

api_bp = Blueprint('api', __name__)

corpus_service = CorpusService()
analysis_service = AnalysisService()
quiz_service = QuizService()

@api_bp.route("/api/search")
def search_keyword():
    query = request.args.get("q", "").strip()
    search_type = request.args.get("type", "word")
    return jsonify(corpus_service.search_keyword(query, search_type))

@api_bp.route('/analyze_sentence_for_quiz', methods=['POST'])
def analyze_sentence_for_quiz():
    data = request.json
    try:
        morphs = analysis_service.analyze_morphs(data.get('sentence', ''))
        return jsonify({'morphs': morphs})
    except Exception as e:
        return jsonify({'error': str(e)})

@api_bp.route('/generate_quiz_action', methods=['POST'])
def generate_quiz_action():
    data = request.json
    max_grade = max([int(g) for g in data.get('grades', [])] or [1])
    quiz_type = data.get('quiz_type', 'binary')
    target = data.get('target', '') 
    context = data.get('context', '')
    user_prompt = data.get('user_prompt', '') 

    return jsonify(quiz_service.generate_quiz_item(target, max_grade, quiz_type, context, user_prompt))

@api_bp.route('/api/generate-matching', methods=['POST'])
def generate_matching_quiz():
    data = request.json
    input_words = data.get('words', [])
    return jsonify(quiz_service.generate_matching_quiz(input_words))
