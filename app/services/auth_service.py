from flask_jwt_extended import create_access_token
from app.repositories.user_repository import UserRepository
from app.utils.security import hash_password, check_password
from app.utils.validators import validate_registration_input, validate_login_input

class AuthService:
    @classmethod
    def register(cls, data: dict, default_role: str = "student") -> tuple[dict | None, str | None]:
        valid, msg = validate_registration_input(data)
        if not valid:
            return None, msg

        email = data["email"].strip().lower()
        existing = UserRepository.find_by_email(email)
        if existing:
            return None, "An account with this email address already exists."

        # Allow 'admin' role only if explicitly allowed, else student
        role = data.get("role", default_role)
        if role not in ("student", "admin"):
            role = "student"

        pwd_hash = hash_password(data["password"])
        user = UserRepository.create(
            name=data["name"],
            email=email,
            password_hash=pwd_hash,
            role=role
        )

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

        email = data["email"].strip().lower()
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
