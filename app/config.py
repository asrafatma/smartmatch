import os
from datetime import timedelta
from dotenv import load_dotenv

# Load .env if present
load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DEFAULT_SECRET_KEY = "smartmatch-default-insecure-dev-key-change-me"
DEFAULT_JWT_SECRET_KEY = "smartmatch-jwt-default-key-change-me"


def _resolve_upload_folder(path: str) -> str:
    """Always return an absolute path so saving (CWD-relative) and serving
    (Flask resolves relative paths against the app package) agree."""
    if not path:
        path = "uploads"
    if not os.path.isabs(path):
        path = os.path.join(PROJECT_ROOT, path)
    return os.path.abspath(path)


def _env_bool(name: str, default: str = "0") -> bool:
    return os.getenv(name, default).strip().lower() in ("1", "true", "yes")

class Config:
    # Flask Settings
    FLASK_ENV = os.getenv("FLASK_ENV", "development")
    DEBUG = _env_bool("FLASK_DEBUG")
    SECRET_KEY = os.getenv("SECRET_KEY", DEFAULT_SECRET_KEY)

    # JWT Settings
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", DEFAULT_JWT_SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(seconds=int(os.getenv("JWT_ACCESS_TOKEN_EXPIRES", "86400")))

    # Database Settings
    MONGODB_URI = os.getenv("MONGODB_URI", "")
    MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "smartmatch")
    # If a real MONGODB_URI is configured but unreachable, fall back to in-memory mock?
    # Defaults to off in production so data is never silently written to volatile memory.
    MONGODB_ALLOW_MOCK_FALLBACK = _env_bool(
        "MONGODB_ALLOW_MOCK_FALLBACK",
        "0" if os.getenv("FLASK_ENV", "development") == "production" else "1"
    )

    # Optional invite code that allows self-registration as an administrator.
    # When empty, public registration can only create student accounts.
    ADMIN_INVITE_CODE = os.getenv("ADMIN_INVITE_CODE", "").strip()

    # Gemini AI Settings
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
    # Default to current generation stable multimodal model
    GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
    GEMINI_TIMEOUT_SECONDS = int(os.getenv("GEMINI_TIMEOUT_SECONDS", "30"))

    # Upload & Media Settings
    UPLOAD_FOLDER = _resolve_upload_folder(os.getenv("UPLOAD_FOLDER", "uploads"))
    # Maximum size of a single image file (spec: 5 MB demo cap -> 413 when exceeded)
    MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_BYTES", str(5 * 1024 * 1024)))
    # Whole-request cap (image + form fields). Slightly above the image cap.
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", str(6 * 1024 * 1024)))
    ALLOWED_IMAGE_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
    # Mirror uploaded images into MongoDB GridFS so they survive restarts on hosts with
    # ephemeral disks (Render/Railway free tiers). Only used with a real MongoDB connection.
    IMAGE_STORAGE_GRIDFS = _env_bool("IMAGE_STORAGE_GRIDFS", "1")

    # CORS: the frontend is served by Flask itself (same origin), so cross-origin access is
    # disabled by default. Set a comma-separated list of origins only if a separate frontend
    # host is used. "*" is accepted for local experiments only.
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "").strip()

    # Incident dates must fall in this window (rejects typos such as year 0202 or the future)
    MIN_INCIDENT_DATE = os.getenv("MIN_INCIDENT_DATE", "2020-01-01")

    # Claims
    MAX_CLAIM_ATTEMPTS = int(os.getenv("MAX_CLAIM_ATTEMPTS", "3"))
    # Fraction of the finder's private clue keywords that an answer must contain to verify
    CLAIM_VERIFICATION_THRESHOLD = float(os.getenv("CLAIM_VERIFICATION_THRESHOLD", "0.6"))

    # Simple in-memory rate limiting for sensitive endpoints (per client IP)
    RATE_LIMIT_ENABLED = _env_bool("RATE_LIMIT_ENABLED", "1")
    RATE_LIMITS = {
        "login": (10, 60),      # 10 requests / 60 s
        "register": (5, 60),
        "claim": (10, 60),
        "analyze": (10, 60),
    }

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

    # Fixed compatibility dictionaries used by the deterministic matcher (partial credit).
    # Values are normalized forms produced by app/ai/normalizer.py.
    COMPATIBLE_OBJECT_TYPES = [
        {"wallet", "card_holder"},
        {"water_bottle", "cup_mug"},
        {"headphones", "earbuds"},
        {"laptop", "tablet"},
    ]
    COLOR_FAMILIES = {
        "dark_blue": "blue", "light_blue": "blue", "blue": "blue", "navy": "blue", "teal": "blue", "cyan": "blue",
        "dark_red": "red", "red": "red", "pink": "red",
        "dark_gray": "gray", "gray": "gray", "silver": "gray",
        "black": "black",
        "white": "white", "beige": "white",
        "gold": "yellow", "yellow": "yellow",
        "brown": "brown", "tan": "brown",
        "green": "green", "olive": "green",
        "orange": "orange", "purple": "purple",
    }

    # Algorithm & Config Versions (bump CONFIG_VERSION whenever weights/dictionaries change)
    ALGORITHM_VERSION = "1.1.0"
    CONFIG_VERSION = "2026.2"
    EXTRACTION_VERSION = "1.0.0"

class TestingConfig(Config):
    TESTING = True
    FLASK_ENV = "testing"
    DEBUG = False
    MONGODB_URI = "mock"
    ADMIN_INVITE_CODE = "test-admin-invite-code"
    RATE_LIMIT_ENABLED = False
    IMAGE_STORAGE_GRIDFS = False
    SECRET_KEY = "ci-testing-flask-secret-key-smartmatch"
    JWT_SECRET_KEY = "ci-testing-jwt-secret-key-smartmatch"
