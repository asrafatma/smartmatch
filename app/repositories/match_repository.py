from datetime import datetime, timezone
from bson import ObjectId
from app.repositories.db import get_db

class MatchRepository:
    @staticmethod
    def _format(doc):
        if not doc:
            return None
        doc = dict(doc)
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        if "lost_report_id" in doc and isinstance(doc["lost_report_id"], ObjectId):
            doc["lost_report_id"] = str(doc["lost_report_id"])
        if "found_report_id" in doc and isinstance(doc["found_report_id"], ObjectId):
            doc["found_report_id"] = str(doc["found_report_id"])
        if "created_at" in doc and isinstance(doc["created_at"], datetime):
            doc["created_at"] = doc["created_at"].isoformat()
        return doc

    @classmethod
    def save_match(cls, data: dict) -> dict:
        db = get_db()
        now = datetime.now(timezone.utc)
        doc = dict(data)
        doc["created_at"] = now
        
        lost_id = doc.get("lost_report_id")
        found_id = doc.get("found_report_id")
        
        # Upsert by pair
        res = db.matches.find_one_and_update(
            {"lost_report_id": str(lost_id), "found_report_id": str(found_id)},
            {"$set": doc},
            upsert=True,
            return_document=True
        )
        if res:
            return cls._format(res)
        # Fallback if find_one_and_update returns None on insert in some mock versions
        inserted = db.matches.find_one({"lost_report_id": str(lost_id), "found_report_id": str(found_id)})
        return cls._format(inserted)

    @classmethod
    def find_by_report_id(cls, report_id: str, limit: int = 50) -> list[dict]:
        db = get_db()
        rid = str(report_id)
        cursor = db.matches.find({
            "$or": [
                {"lost_report_id": rid},
                {"found_report_id": rid}
            ]
        }).sort("score", -1).limit(limit)
        return [cls._format(doc) for doc in cursor]

    @classmethod
    def delete_by_report_id(cls, report_id: str) -> int:
        db = get_db()
        rid = str(report_id)
        res = db.matches.delete_many({
            "$or": [
                {"lost_report_id": rid},
                {"found_report_id": rid}
            ]
        })
        return res.deleted_count
