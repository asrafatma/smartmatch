from datetime import datetime, timezone
from bson import ObjectId
from app.repositories.db import get_db

class AILogRepository:
    @staticmethod
    def _format(doc):
        if not doc:
            return None
        doc = dict(doc)
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        if "created_at" in doc and isinstance(doc["created_at"], datetime):
            doc["created_at"] = doc["created_at"].isoformat()
        return doc

    @classmethod
    def log(
        cls,
        report_id: str,
        model_name: str,
        prompt_version: str,
        extraction_version: str,
        status: str,
        error_type: str = None
    ) -> dict:
        db = get_db()
        now = datetime.now(timezone.utc)
        doc = {
            "report_id": str(report_id) if report_id else None,
            "model_name": model_name,
            "prompt_version": prompt_version,
            "extraction_version": extraction_version,
            "status": status,
            "error_type": error_type,
            "created_at": now
        }
        res = db.ai_logs.insert_one(doc)
        doc["_id"] = res.inserted_id
        return cls._format(doc)

    @classmethod
    def list_logs(cls, limit: int = 50) -> list[dict]:
        db = get_db()
        cursor = db.ai_logs.find().sort("created_at", -1).limit(limit)
        return [cls._format(doc) for doc in cursor]
