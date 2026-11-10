from datetime import datetime, timezone
from bson import ObjectId
from app.repositories.db import get_db

class UserRepository:
    @staticmethod
    def _format(doc):
        if not doc:
            return None
        doc = dict(doc)
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        return doc

    @classmethod
    def create(cls, name: str, email: str, password_hash: str, role: str = "student") -> dict:
        db = get_db()
        email_clean = email.strip().lower()
        now = datetime.now(timezone.utc)
        user_doc = {
            "name": name.strip(),
            "email": email_clean,
            "password_hash": password_hash,
            "role": role,
            "is_active": True,
            "created_at": now,
            "updated_at": now
        }
        res = db.users.insert_one(user_doc)
        user_doc["_id"] = res.inserted_id
        return cls._format(user_doc)

    @classmethod
    def find_by_email(cls, email: str) -> dict | None:
        db = get_db()
        if not email:
            return None
        doc = db.users.find_one({"email": email.strip().lower()})
        return cls._format(doc)

    @classmethod
    def find_by_id(cls, user_id: str | ObjectId) -> dict | None:
        db = get_db()
        try:
            oid = ObjectId(user_id) if isinstance(user_id, str) else user_id
            doc = db.users.find_one({"_id": oid})
            return cls._format(doc)
        except Exception:
            return None

    @classmethod
    def list_all(cls, limit: int = 100) -> list[dict]:
        db = get_db()
        cursor = db.users.find().limit(limit)
        return [cls._format(doc) for doc in cursor]

    @classmethod
    def count(cls) -> int:
        db = get_db()
        return db.users.count_documents({})
