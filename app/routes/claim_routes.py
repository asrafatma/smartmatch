from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.services.claim_service import ClaimService
from app.repositories.claim_repository import ClaimRepository

claim_bp = Blueprint("claims", __name__)

@claim_bp.route("", methods=["POST"])
@jwt_required()
def submit_claim():
    claimant_id = get_jwt_identity()
    data = request.get_json(silent=True) or {}
    report_id = data.get("report_id")
    answers = data.get("verification_answers", "")

    if not report_id:
        return jsonify({"success": False, "error": "report_id is required"}), 400

    claim, err, status_code = ClaimService.submit_claim(
        report_id=report_id,
        claimant_id=claimant_id,
        verification_answers=answers
    )

    if err:
        return jsonify({"success": False, "error": err}), status_code

    return jsonify({
        "success": True,
        "message": "Ownership claim submitted successfully",
        "data": claim
    }), status_code

@claim_bp.route("", methods=["GET"])
@jwt_required()
def list_claims():
    user_id = get_jwt_identity()
    claims_jwt = get_jwt()
    user_role = claims_jwt.get("role", "student")

    scope = request.args.get("scope", "mine")
    if scope == "review":
        # Returns claims this user is authorized to review (as finder or admin)
        claims = ClaimService.list_pending_for_reviewer(user_id, user_role)
    else:
        # Returns claims this user submitted
        claims = ClaimRepository.list_by_claimant(user_id)

    return jsonify({
        "success": True,
        "count": len(claims),
        "data": claims
    }), 200

@claim_bp.route("/<claim_id>", methods=["GET"])
@jwt_required()
def get_claim(claim_id):
    user_id = get_jwt_identity()
    claims_jwt = get_jwt()
    user_role = claims_jwt.get("role", "student")

    claim, err, status_code = ClaimService.get_claim(claim_id, user_id, user_role)
    if err:
        return jsonify({"success": False, "error": err}), status_code

    return jsonify({
        "success": True,
        "data": claim
    }), 200

@claim_bp.route("/<claim_id>", methods=["PATCH"])
@jwt_required()
def review_claim(claim_id):
    reviewer_id = get_jwt_identity()
    claims_jwt = get_jwt()
    reviewer_role = claims_jwt.get("role", "student")

    data = request.get_json(silent=True) or {}
    action = data.get("status") or data.get("action")
    notes = data.get("notes")

    if not action:
        return jsonify({"success": False, "error": "Review status ('approved' or 'rejected') is required"}), 400

    reviewed, err, status_code = ClaimService.review_claim(
        claim_id=claim_id,
        reviewer_id=reviewer_id,
        reviewer_role=reviewer_role,
        action=action,
        notes=notes
    )

    if err:
        return jsonify({"success": False, "error": err}), status_code

    return jsonify({
        "success": True,
        "message": f"Claim {action} successfully",
        "data": reviewed
    }), 200
