import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

class Config:
    # Flask Settings
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = os.getenv("FLASK_DEBUG", "0").lower() in ("1", "true", "yes")
    SECRET_KEY = os.getenv("SECRET_KEY", "smartmatch-default-insecure-dev-key-change-me")
    
    # JWT Settings
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "smartmatch-jwt-default-key-change-me")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "86400")))
    
    # Database Settings
    MONGODB_URI = os.getenv("MONGODB_URI", "")
    MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "smartmatch")
    
    # Gemini AI Settings
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    # Default to current generation stable multimodal model
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
    
    # Upload & Media Settings
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads"))
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(10 * 1024 * 1024)))  # 10 MB limit
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    
    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")
    
    # Deterministic Matching Weights (Total = 100)
    MATCHING_WEIGHTS = {
        "category": 20,
        "object_type": 15,
        "brand_or_logo": 15,
        "color": 15,
        "material_and_shape": 10,
        "distinctive_features": 15,
        "location": 5,
        "date": 5,
    }
    
    # Score Thresholds
    STRONG_MATCH_THRESHOLD = 70
    POSSIBLE_MATCH_THRESHOLD = 40
    
    # Algorithm & Config Versions
    ALGORITHM_VERSION = "1.0.0"
    CONFIG_VERSION = "2026.1"
    EXTRACTION_VERSION = "1.0.0"

class TestingConfig(Config):
    TESTING = True
    FLASK_ENV = "testing"
    DEBUG = False
    MONGODB_URI = "mock"
    SECRET_KEY = "ci-testing-flask-secret-key-smartmatch"
    JWT_SECRET_KEY = "ci-testing-jwt-secret-key-smartmatch"
