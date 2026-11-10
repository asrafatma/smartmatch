import logging
import os
import re
from flask import Flask, jsonify, send_from_directory, request, Response, abort
from werkzeug.exceptions import HTTPException
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from app.config import Config, DEFAULT_SECRET_KEY, DEFAULT_JWT_SECRET_KEY
from app.repositories.db import init_db

def create_app(config_class=Config):
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates"
    )
    app.config.from_object(config_class)

    # Behind a hosting proxy (Render/Railway/etc.) trust X-Forwarded-* so HTTPS and client IPs
    # are detected correctly (used by HSTS and rate limiting).
    if os.getenv("TRUST_PROXY", "1" if app.config.get("FLASK_ENV") == "production" else "0") in ("1", "true", "yes"):
        from werkzeug.middleware.proxy_fix import ProxyFix
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Refuse to boot a production deployment with the publicly known default secrets.
    if app.config.get("FLASK_ENV") == "production" and not app.config.get("TESTING"):
        if app.config.get("SECRET_KEY") in (None, "", DEFAULT_SECRET_KEY) or                 app.config.get("JWT_SECRET_KEY") in (None, "", DEFAULT_JWT_SECRET_KEY):
            raise RuntimeError(
                "SECRET_KEY and JWT_SECRET_KEY must be set to strong unique values in production."
            )

    # CORS: same-origin by default (Flask serves the frontend). Only enable for explicit origins.
    cors_origins = (app.config.get("CORS_ORIGINS") or "").strip()
    if cors_origins == "*":
        CORS(app, resources={r"/api/*": {"origins": "*"}})
    elif cors_origins:
        origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
        CORS(app, resources={r"/api/*": {"origins": origins}})

    # Initialize JWT
    jwt = JWTManager(app)

    @jwt.unauthorized_loader
    def unauthorized_callback(callback):
        return jsonify({
            "success": False,
            "error": "Authorization token is missing or invalid",
            "code": "UNAUTHORIZED"
        }), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(callback):
        return jsonify({
            "success": False,
            "error": "Provided token is invalid or malformed",
            "code": "INVALID_TOKEN"
        }), 401

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({
            "success": False,
            "error": "Token has expired, please log in again",
            "code": "TOKEN_EXPIRED"
        }), 401

    # Security headers
    @app.after_request
    def set_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if request.is_secure:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response

    # Ensure upload directory exists
    upload_folder = os.path.abspath(app.config.get("UPLOAD_FOLDER", "uploads"))
    app.config["UPLOAD_FOLDER"] = upload_folder
    os.makedirs(upload_folder, exist_ok=True)

    # Serve uploads: only server-generated names are valid; fall back to persistent GridFS copy
    safe_name = re.compile(r"^[A-Za-z0-9_\-]+\.(jpg|jpeg|png|webp)$")

    @app.route("/uploads/<path:filename>")
    def serve_upload(filename):
        if not safe_name.match(filename):
            abort(404)
        if os.path.isfile(os.path.join(upload_folder, filename)):
            return send_from_directory(upload_folder, filename, max_age=86400)
        from app.utils.file_handler import load_persisted_image
        stored = load_persisted_image(filename)
        if stored is None:
            abort(404)
        data, mime = stored
        # Re-cache locally so subsequent requests are served from disk
        try:
            with open(os.path.join(upload_folder, filename), "wb") as f:
                f.write(data)
        except OSError:
            pass
        resp = Response(data, mimetype=mime)
        resp.headers["Cache-Control"] = "public, max-age=86400"
        return resp

    # JSON errors for the API; never leak stack traces
    def _api_error(status: int, code: str, message: str):
        return jsonify({"success": False, "error": message, "code": code}), status

    @app.errorhandler(413)
    def too_large(e):
        limit_mb = app.config.get("MAX_IMAGE_BYTES", 5 * 1024 * 1024) // (1024 * 1024)
        return _api_error(413, "FILE_TOO_LARGE", f"Upload exceeds the maximum allowed size of {limit_mb}MB.")

    @app.errorhandler(HTTPException)
    def http_error(e):
        if request.path.startswith("/api/"):
            return _api_error(e.code or 500, (e.name or "ERROR").upper().replace(" ", "_"), e.description or e.name)
        return e

    @app.errorhandler(Exception)
    def unhandled_error(e):
        if isinstance(e, HTTPException):
            return http_error(e)
        logging.getLogger(__name__).exception("Unhandled server error: %s", e)
        if app.config.get("TESTING"):
            raise e
        return _api_error(500, "INTERNAL_ERROR", "An unexpected server error occurred.")

    # Initialize Database connection & indexes
    init_db(app)

    from app.repositories.claim_repository import ClaimRepository
    ClaimRepository.MAX_ATTEMPTS = int(app.config.get("MAX_CLAIM_ATTEMPTS", 3))

    # Register blueprints
    from app.routes.health_routes import health_bp
    from app.routes.auth_routes import auth_bp
    from app.routes.report_routes import report_bp
    from app.routes.match_routes import match_bp
    from app.routes.claim_routes import claim_bp
    from app.routes.admin_routes import admin_bp
    from app.routes.frontend_routes import frontend_bp

    app.register_blueprint(health_bp)
    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(report_bp, url_prefix="/api/reports")
    app.register_blueprint(match_bp, url_prefix="/api/matches")
    app.register_blueprint(claim_bp, url_prefix="/api/claims")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(frontend_bp)

    return app
