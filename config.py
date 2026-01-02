import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'hangyeol_secret_key')
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    # Add other configuration variables here if needed
