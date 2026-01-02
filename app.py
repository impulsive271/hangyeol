from flask import Flask
from config import Config
from services.morph_service import MorphService
from services.grade_database import GradeDatabase
from routes.main_routes import main_bp
from routes.api_routes import api_bp

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Services
morph_service = MorphService()
grade_database = GradeDatabase()
grade_database.initialize(morph_service)

# Register Blueprints
app.register_blueprint(main_bp)
app.register_blueprint(api_bp)

if __name__ == "__main__":
    app.run(debug=True)