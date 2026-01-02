from flask import Flask
from config import Config
from routes.main_routes import main_bp
from routes.api_routes import api_bp

app = Flask(__name__)
app.config.from_object(Config)

# Register Blueprints
app.register_blueprint(main_bp)
app.register_blueprint(api_bp)

if __name__ == "__main__":
    app.run(debug=True)