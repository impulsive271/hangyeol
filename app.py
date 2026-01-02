from flask import Flask
from config import Config
from services.morph_service import MorphService
from services.data_service import DataService
from routes.main_routes import main_bp
from routes.api_routes import api_bp

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Services
morph_service = MorphService()
data_service = DataService()
data_service.initialize(morph_service)

# Register Blueprints
app.register_blueprint(main_bp)
app.register_blueprint(api_bp)

if __name__ == "__main__":
    app.run(debug=True)