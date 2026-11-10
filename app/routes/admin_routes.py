from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt
from app.repositories.user_repository import UserRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.claim_repository import ClaimRepository
from app.repositories.ai_log_repository import AILogRepository

admin_bp = Blueprint("admin", __name__)

def check_admin_role():
    claims = get_jwt()
    return claims.get("role") == "admin"

@admin_bp.route("/dashboard", methods=["GET"])
@jwt_required()
def admin_dashboard():
    if not check_admin_role():
        return jsonify({"success": False, "error": "Administrator privilege required"}), 403

    total_users = UserRepository.count()
    total_lost = ReportRepository.count({"report_type": "lost"})
    total_found = ReportRepository.count({"report_type": "found"})
    active_reports = ReportRepository.count({"status": "active"})
    resolved_reports = ReportRepository.count({"status": "resolved"})
    pending_claims = len(ClaimRepository.list_all(status="pending"))
    recent_ai_logs = AILogRepository.list_logs(limit=10)

    return jsonify({
        "success": True,
        "data": {
            "stats": {
                "total_users": total_users,
                "total_lost": total_lost,
                "total_found": total_found,
                "active_reports": active_reports,
                "resolved_reports": resolved_reports,
                "pending_claims": pending_claims
            },
            "recent_ai_logs": recent_ai_logs
        }
    }), 200

@admin_bp.route("/reports", methods=["GET"])
@jwt_required()
def admin_reports():
    if not check_admin_role():
        return jsonify({"success": False, "error": "Administrator privilege required"}), 403

    limit = int(request.args.get("limit", 100))
    reports = ReportRepository.list_reports(filters={}, limit=limit)
    return jsonify({
        "success": True,
        "count": len(reports),
        "data": reports
    }), 200

@admin_bp.route("/claims", methods=["GET"])
@jwt_required()
def admin_claims():
    if not check_admin_role():
        return jsonify({"success": False, "error": "Administrator privilege required"}), 403

    claims = ClaimRepository.list_all(mask_private=False, limit=100)
    enriched = []
    for c in claims:
        rep = ReportRepository.find_by_id(c["report_id"])
        c["report_title"] = rep.get("title") if rep else "Unknown Report"
        c["report_type"] = rep.get("report_type") if rep else "unknown"
        enriched.append(c)

    return jsonify({
        "success": True,
        "count": len(enriched),
        "data": enriched
    }), 200
