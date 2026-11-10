from flask import Blueprint, jsonify, current_app
from app.repositories.db import Database
from app.config import Config

health_bp = Blueprint("health", __name__)

@health_bp.route("/api/health", methods=["GET"])
def health_check():
    db_mock = Database.is_mock()
    db_status = "in-memory (mock/offline mode)" if db_mock else "connected (MongoDB Atlas/cluster)"
    
    has_gemini_key = bool(current_app.config.get("GEMINI_API_KEY", "").strip())
    ai_status = f"active ({Config.GEMINI_MODEL})" if has_gemini_key else "fallback mode (manual/rule-based)"

    return jsonify({
        "status": "healthy",
        "service": "SmartMatch Lost & Found API",
        "version": Config.ALGORITHM_VERSION,
        "database": {
            "status": "healthy",
            "driver": db_status
        },
        "ai_engine": {
            "status": ai_status,
            "multimodal_enabled": has_gemini_key
        },
        "matching_algorithm": {
            "version": Config.ALGORITHM_VERSION,
            "config_version": Config.CONFIG_VERSION,
            "mode": "deterministic"
        }
    }), 200
