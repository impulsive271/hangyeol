import os
from dotenv import load_dotenv

load_dotenv()

# [FIX] Supress "Both GOOGLE_API_KEY and GEMINI_API_KEY are set" warning
if 'GOOGLE_API_KEY' in os.environ and 'GEMINI_API_KEY' in os.environ:
    os.environ.pop('GEMINI_API_KEY', None)

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'hangyeol_secret_key')
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    # Add other configuration variables here if needed
