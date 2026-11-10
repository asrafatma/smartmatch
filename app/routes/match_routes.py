from flask import Blueprint, jsonify, request
from app.services.matching_service import MatchingEngine
from app.repositories.report_repository import ReportRepository

match_bp = Blueprint("matches", __name__)

@match_bp.route("/<report_id>", methods=["GET"])
def get_matches(report_id):
    report = ReportRepository.find_by_id(report_id)
    if not report:
        return jsonify({"success": False, "error": "Report not found"}), 404

    limit = int(request.args.get("limit", 20))
    matches = MatchingEngine.find_matches_for_report(report_id, limit=limit)

    return jsonify({
        "success": True,
        "base_report": {
            "id": report["id"],
            "title": report["title"],
            "report_type": report["report_type"],
            "category": report["category"],
            "image_path": report["image_path"],
            "attributes": report.get("attributes", {})
        },
        "count": len(matches),
        "data": matches
    }), 200
