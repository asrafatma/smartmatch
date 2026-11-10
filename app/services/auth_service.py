import hmac
from flask import current_app
from pymongo.errors import DuplicateKeyError
from flask_jwt_extended import create_access_token
from app.repositories.user_repository import UserRepository
from app.utils.security import hash_password, check_password
from app.utils.validators import validate_registration_input, validate_login_input, as_str

class AuthService:
    @classmethod
    def register(cls, data: dict, default_role: str = "student") -> tuple[dict | None, str | None]:
        valid, msg = validate_registration_input(data)
        if not valid:
            return None, msg

        email = as_str(data["email"]).lower()
        existing = UserRepository.find_by_email(email)
        if existing:
            return None, "An account with this email address already exists."

        # Public registration always creates a student. An admin account requires the
        # server-side ADMIN_INVITE_CODE; a client-supplied "role" field alone is ignored.
        role = default_role if default_role in ("student", "admin") else "student"
        if as_str(data.get("role")).lower() == "admin" or as_str(data.get("admin_code")):
            invite_code = current_app.config.get("ADMIN_INVITE_CODE", "")
            supplied = as_str(data.get("admin_code"))
            if not invite_code or not supplied or not hmac.compare_digest(supplied, invite_code):
                return None, "Administrator registration requires a valid admin invite code."
            role = "admin"

        pwd_hash = hash_password(data["password"])
        try:
            user = UserRepository.create(
                name=as_str(data["name"]),
                email=email,
                password_hash=pwd_hash,
                role=role
            )
        except DuplicateKeyError:
            return None, "An account with this email address already exists."

        token = create_access_token(
            identity=user["id"],
            additional_claims={"role": user["role"], "email": user["email"]}
        )

        return {
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"]
            },
            "token": token
        }, None

    @classmethod
    def login(cls, data: dict) -> tuple[dict | None, str | None]:
        valid, msg = validate_login_input(data)
        if not valid:
            return None, msg

        email = as_str(data["email"]).lower()
        user = UserRepository.find_by_email(email)
        if not user or not user.get("is_active", True):
            return None, "Invalid email or password."

        if not check_password(data["password"], user["password_hash"]):
            return None, "Invalid email or password."

        token = create_access_token(
            identity=user["id"],
            additional_claims={"role": user["role"], "email": user["email"]}
        )

        return {
            "user": {
                "id": user["id"],
                "name": user["name"],
                "email": user["email"],
                "role": user["role"]
            },
            "token": token
        }, None

    @classmethod
    def get_current_user(cls, user_id: str) -> dict | None:
        user = UserRepository.find_by_id(user_id)
        if not user:
            return None
        return {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "role": user["role"]
        }
