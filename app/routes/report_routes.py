from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt, verify_jwt_in_request
from app.services.report_service import ReportService
from app.services.contact_service import ContactService

report_bp = Blueprint("reports", __name__)

@report_bp.route("", methods=["POST"])
@jwt_required()
def create_report():
    user_id = get_jwt_identity()
    form_data = request.form.to_dict()
    file_storage = request.files.get("image")
    upload_folder = current_app.config["UPLOAD_FOLDER"]

    created, err, status_code = ReportService.create_report(
        user_id=user_id,
        form_data=form_data,
        file_storage=file_storage,
        upload_folder=upload_folder
    )

    if err:
        return jsonify({"success": False, "error": err}), status_code

    return jsonify({
        "success": True,
        "message": "Report submitted successfully",
        "data": created
    }), 201

@report_bp.route("", methods=["GET"])
def list_reports():
    filters = {
        "report_type": request.args.get("report_type"),
        "category": request.args.get("category"),
        "status": request.args.get("status", "active"),
        "search": request.args.get("search"),
        "location": request.args.get("location")
    }
    # Allow filtering by user_id
    if request.args.get("user_id"):
        filters["user_id"] = request.args.get("user_id")

    page = int(request.args.get("page", 1))
    limit = int(request.args.get("limit", 20))

    result = ReportService.list_reports(filters, page=page, limit=limit)
    return jsonify({
        "success": True,
        "data": result
    }), 200

@report_bp.route("/<report_id>", methods=["GET"])
def get_report(report_id):
    req_user_id = None
    try:
        verify_jwt_in_request(optional=True)
        req_user_id = get_jwt_identity()
    except Exception:
        pass

    report, err, status_code = ReportService.get_report(report_id, requesting_user_id=req_user_id)
    if err:
        return jsonify({"success": False, "error": err}), status_code

    return jsonify({
        "success": True,
        "data": report
    }), 200

@report_bp.route("/<report_id>", methods=["PATCH"])
@jwt_required()
def update_report(report_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role", "student")
    update_data = request.get_json(silent=True) or {}

    updated, err, status_code = ReportService.update_report(
        report_id=report_id,
        user_id=user_id,
        user_role=user_role,
        update_data=update_data
    )

    if err:
        return jsonify({"success": False, "error": err}), status_code

    return jsonify({
        "success": True,
        "message": "Report updated successfully",
        "data": updated
    }), 200

@report_bp.route("/<report_id>", methods=["DELETE"])
@jwt_required()
def delete_report(report_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role", "student")

    success, err, status_code = ReportService.delete_report(
        report_id=report_id,
        user_id=user_id,
        user_role=user_role
    )

    if err:
        return jsonify({"success": False, "error": err}), status_code

    return jsonify({
        "success": True,
        "message": "Report closed successfully"
    }), 200

@report_bp.route("/<report_id>/contact", methods=["GET"])
@jwt_required()
def get_contact_info(report_id):
    user_id = get_jwt_identity()
    claims = get_jwt()
    user_role = claims.get("role", "student")

    contact, err, status_code = ContactService.get_authorized_contact(
        report_id=report_id,
        requesting_user_id=user_id,
        user_role=user_role
    )

    if err:
        return jsonify({"success": False, "error": err}), status_code

    return jsonify({
        "success": True,
        "data": contact
    }), 200
