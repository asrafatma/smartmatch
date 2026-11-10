from flask import Blueprint, jsonify, current_app
from app.repositories.db import Database
from app.config import Config

health_bp = Blueprint("health", __name__)

@health_bp.route("/api/health", methods=["GET"])
def health_check():
    db_mock = Database.is_mock()
    fallback_reason = Database.fallback_reason()
    db_reachable = Database.ping()

    if not db_reachable:
        db_health = "unhealthy"
    elif fallback_reason:
        # A real database was configured but we are running on volatile memory
        db_health = "degraded"
    else:
        db_health = "healthy"

    db_driver = "in-memory (mock/offline mode)" if db_mock else "connected (MongoDB Atlas/cluster)"

    has_gemini_key = bool(str(current_app.config.get("GEMINI_API_KEY", "")).strip())
    model_name = current_app.config.get("GEMINI_MODEL", Config.GEMINI_MODEL)
    ai_status = f"active ({model_name})" if has_gemini_key else "fallback mode (manual/rule-based)"

    overall = "healthy" if db_health == "healthy" else db_health
    database = {"status": db_health, "driver": db_driver}
    if fallback_reason:
        database["warning"] = (
            f"Configured MongoDB unreachable ({fallback_reason}); data is NOT persisted."
        )

    return jsonify({
        "status": overall,
        "service": "SmartMatch Lost & Found API",
        "version": Config.ALGORITHM_VERSION,
        "database": database,
        "ai_engine": {
            "status": ai_status,
            "multimodal_enabled": has_gemini_key
        },
        "matching_algorithm": {
            "version": Config.ALGORITHM_VERSION,
            "config_version": Config.CONFIG_VERSION,
            "mode": "deterministic"
        }
    }), 200 if db_health != "unhealthy" else 503
