import os
from flask import Flask, jsonify, send_from_directory
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from app.config import Config
from app.repositories.db import init_db

def create_app(config_class=Config):
    app = Flask(
        __name__,
        static_folder="static",
        template_folder="templates"
    )
    app.config.from_object(config_class)

    # Initialize CORS
    cors_origins = app.config.get("CORS_ORIGINS", "*")
    if cors_origins == "*":
        CORS(app)
    else:
        origins = [o.strip() for o in cors_origins.split(",") if o.strip()]
        CORS(app, origins=origins)

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
        return response

    # Ensure upload directory exists
    upload_folder = app.config.get("UPLOAD_FOLDER", "uploads")
    os.makedirs(upload_folder, exist_ok=True)

    # Serve uploads securely
    @app.route("/uploads/<path:filename>")
    def serve_upload(filename):
        return send_from_directory(upload_folder, filename)

    # Initialize Database connection & indexes
    init_db(app)

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
