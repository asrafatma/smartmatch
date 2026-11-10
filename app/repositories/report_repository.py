from datetime import datetime, timezone
from bson import ObjectId
from app.repositories.db import get_db

class ReportRepository:
    @staticmethod
    def _format(doc):
        if not doc:
            return None
        doc = dict(doc)
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        if "user_id" in doc and isinstance(doc["user_id"], ObjectId):
            doc["user_id"] = str(doc["user_id"])
        # Format dates as ISO string if datetime
        for dt_field in ["incident_date", "created_at", "updated_at"]:
            if dt_field in doc and isinstance(doc[dt_field], datetime):
                doc[dt_field] = doc[dt_field].isoformat()
        return doc

    @classmethod
    def create(cls, data: dict) -> dict:
        db = get_db()
        now = datetime.now(timezone.utc)
        doc = dict(data)
        doc["created_at"] = now
        doc["updated_at"] = now
        if "status" not in doc:
            doc["status"] = "active"
        if "user_id" in doc and isinstance(doc["user_id"], str):
            try:
                doc["user_id"] = ObjectId(doc["user_id"])
            except Exception:
                pass

        res = db.reports.insert_one(doc)
        doc["_id"] = res.inserted_id
        return cls._format(doc)

    @classmethod
    def find_by_id(cls, report_id: str | ObjectId) -> dict | None:
        db = get_db()
        try:
            oid = ObjectId(report_id) if isinstance(report_id, str) else report_id
            doc = db.reports.find_one({"_id": oid})
            return cls._format(doc)
        except Exception:
            return None

    @classmethod
    def find_active_by_type(cls, report_type: str) -> list[dict]:
        db = get_db()
        cursor = db.reports.find({
            "report_type": report_type,
            "status": "active"
        }).sort("created_at", -1)
        return [cls._format(doc) for doc in cursor]

    @classmethod
    def list_reports(cls, filters: dict = None, skip: int = 0, limit: int = 50) -> list[dict]:
        db = get_db()
        q = {}
        if filters:
            for k, v in filters.items():
                if v is not None and v != "":
                    if k == "user_id" and isinstance(v, str):
                        try:
                            q[k] = ObjectId(v)
                        except Exception:
                            q[k] = v
                    elif k in ("report_type", "status", "category"):
                        q[k] = v
                    elif k == "search":
                        # Case-insensitive title/desc search
                        q["$or"] = [
                            {"title": {"$regex": v, "$options": "i"}},
                            {"description": {"$regex": v, "$options": "i"}},
                            {"location": {"$regex": v, "$options": "i"}}
                        ]
                    elif k == "location":
                        q["location"] = {"$regex": v, "$options": "i"}

        cursor = db.reports.find(q).sort("created_at", -1).skip(skip).limit(limit)
        return [cls._format(doc) for doc in cursor]

    @classmethod
    def count(cls, filters: dict = None) -> int:
        db = get_db()
        q = {}
        if filters:
            for k, v in filters.items():
                if v is not None and v != "":
                    if k == "user_id" and isinstance(v, str):
                        try:
                            q[k] = ObjectId(v)
                        except Exception:
                            q[k] = v
                    elif k in ("report_type", "status", "category"):
                        q[k] = v
        return db.reports.count_documents(q)

    @classmethod
    def update(cls, report_id: str | ObjectId, update_data: dict) -> dict | None:
        db = get_db()
        try:
            oid = ObjectId(report_id) if isinstance(report_id, str) else report_id
            data = dict(update_data)
            data["updated_at"] = datetime.now(timezone.utc)
            db.reports.update_one({"_id": oid}, {"$set": data})
            return cls.find_by_id(oid)
        except Exception:
            return None

    @classmethod
    def update_status(cls, report_id: str | ObjectId, status: str) -> bool:
        db = get_db()
        try:
            oid = ObjectId(report_id) if isinstance(report_id, str) else report_id
            res = db.reports.update_one(
                {"_id": oid},
                {"$set": {"status": status, "updated_at": datetime.now(timezone.utc)}}
            )
            return res.modified_count > 0 or res.matched_count > 0
        except Exception:
            return False

    @classmethod
    def delete(cls, report_id: str | ObjectId) -> bool:
        db = get_db()
        try:
            oid = ObjectId(report_id) if isinstance(report_id, str) else report_id
            res = db.reports.delete_one({"_id": oid})
            return res.deleted_count > 0
        except Exception:
            return False
