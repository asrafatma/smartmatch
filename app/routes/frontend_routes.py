from flask import Blueprint, render_template, send_from_directory, current_app

frontend_bp = Blueprint("frontend", __name__)

@frontend_bp.route("/")
@frontend_bp.route("/dashboard")
@frontend_bp.route("/reports")
@frontend_bp.route("/submit-lost")
@frontend_bp.route("/submit-found")
@frontend_bp.route("/claims")
@frontend_bp.route("/my-reports")
@frontend_bp.route("/admin")
@frontend_bp.route("/login")
@frontend_bp.route("/register")
def index():
    return render_template("index.html")
