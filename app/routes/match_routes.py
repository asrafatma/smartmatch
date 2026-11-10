from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.services.matching_service import MatchingEngine
from app.repositories.report_repository import ReportRepository
from app.utils.validators import parse_int

match_bp = Blueprint("matches", __name__)

@match_bp.route("/<report_id>", methods=["GET"])
@jwt_required()
def get_matches(report_id):
    report = ReportRepository.find_by_id(report_id)
    if not report:
        return jsonify({"success": False, "error": "Report not found"}), 404

    # Match candidates reveal other users' reports and drive the claim flow, so they are
    # only available to the owner of the base report or an administrator.
    user_id = get_jwt_identity()
    role = get_jwt().get("role", "student")
    if str(report.get("user_id")) != str(user_id) and role != "admin":
        return jsonify({
            "success": False,
            "error": "Only the person who submitted this report can view its matches."
        }), 403

    limit = parse_int(request.args.get("limit"), default=20, minimum=1, maximum=100)
    matches = MatchingEngine.find_matches_for_report(report["id"], limit=limit)

    return jsonify({
        "success": True,
        "base_report": {
            "id": report["id"],
            "title": report.get("title"),
            "report_type": report.get("report_type"),
            "category": report.get("category"),
            "image_path": report.get("image_path"),
            "attributes": report.get("attributes", {})
        },
        "count": len(matches),
        "data": matches
    }), 200
