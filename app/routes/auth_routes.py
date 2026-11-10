from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity, get_jwt
from app.services.auth_service import AuthService

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    result, err = AuthService.register(data)
    if err:
        return jsonify({"success": False, "error": err}), 400
    return jsonify({
        "success": True,
        "message": "User registered successfully",
        "data": result
    }), 201

@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    result, err = AuthService.login(data)
    if err:
        return jsonify({"success": False, "error": err}), 401
    return jsonify({
        "success": True,
        "message": "Login successful",
        "data": result
    }), 200

@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    current_user_id = get_jwt_identity()
    user = AuthService.get_current_user(current_user_id)
    if not user:
        return jsonify({"success": False, "error": "User profile not found"}), 404
    return jsonify({
        "success": True,
        "data": user
    }), 200
