from datetime import datetime, timezone
from bson import ObjectId
from app.repositories.db import get_db

class ClaimRepository:
    MAX_ATTEMPTS = 3

    @staticmethod
    def _format(doc, mask_private=False):
        if not doc:
            return None
        doc = dict(doc)
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        if "report_id" in doc and isinstance(doc["report_id"], ObjectId):
            doc["report_id"] = str(doc["report_id"])
        if "claimant_id" in doc and isinstance(doc["claimant_id"], ObjectId):
            doc["claimant_id"] = str(doc["claimant_id"])
        if "reviewed_by" in doc and isinstance(doc["reviewed_by"], ObjectId):
            doc["reviewed_by"] = str(doc["reviewed_by"])
        for dt_field in ["created_at", "reviewed_at", "updated_at"]:
            if dt_field in doc and isinstance(doc[dt_field], datetime):
                doc[dt_field] = doc[dt_field].isoformat()

        if mask_private and "verification_answers" in doc:
            # Mask verification answers for unauthorized viewers
            doc["verification_answers"] = "[PRIVATE VERIFICATION DETAILS HIDDEN]"

        return doc

    @classmethod
    def create(cls, report_id: str, claimant_id: str, verification_answers: str) -> dict:
        db = get_db()
        now = datetime.now(timezone.utc)
        doc = {
            "report_id": str(report_id),
            "claimant_id": str(claimant_id),
            "verification_answers": verification_answers.strip(),
            "status": "pending",
            "attempt_count": 1,
            "reviewed_by": None,
            "reviewed_at": None,
            "review_notes": None,
            "created_at": now,
            "updated_at": now
        }
        res = db.claims.insert_one(doc)
        doc["_id"] = res.inserted_id
        return cls._format(doc)

    @classmethod
    def find_by_id(cls, claim_id: str | ObjectId, mask_private: bool = False) -> dict | None:
        db = get_db()
        try:
            oid = ObjectId(claim_id) if isinstance(claim_id, str) else claim_id
            doc = db.claims.find_one({"_id": oid})
            return cls._format(doc, mask_private=mask_private)
        except Exception:
            return None

    @classmethod
    def find_by_report_and_claimant(cls, report_id: str, claimant_id: str) -> dict | None:
        db = get_db()
        doc = db.claims.find_one({
            "report_id": str(report_id),
            "claimant_id": str(claimant_id)
        })
        return cls._format(doc)

    @classmethod
    def list_by_report_id(cls, report_id: str, mask_private: bool = True) -> list[dict]:
        db = get_db()
        cursor = db.claims.find({"report_id": str(report_id)}).sort("created_at", -1)
        return [cls._format(doc, mask_private=mask_private) for doc in cursor]

    @classmethod
    def list_by_claimant(cls, claimant_id: str) -> list[dict]:
        db = get_db()
        cursor = db.claims.find({"claimant_id": str(claimant_id)}).sort("created_at", -1)
        # Claimant can view their own verification answers
        return [cls._format(doc, mask_private=False) for doc in cursor]

    @classmethod
    def list_all(cls, status: str = None, mask_private: bool = False, limit: int = 100) -> list[dict]:
        db = get_db()
        q = {}
        if status:
            q["status"] = status
        cursor = db.claims.find(q).sort("created_at", -1).limit(limit)
        return [cls._format(doc, mask_private=mask_private) for doc in cursor]

    @classmethod
    def update_status(cls, claim_id: str | ObjectId, status: str, reviewer_id: str, notes: str = None) -> dict | None:
        db = get_db()
        try:
            oid = ObjectId(claim_id) if isinstance(claim_id, str) else claim_id
            now = datetime.now(timezone.utc)
            db.claims.update_one(
                {"_id": oid},
                {
                    "$set": {
                        "status": status,
                        "reviewed_by": str(reviewer_id),
                        "reviewed_at": now,
                        "review_notes": notes,
                        "updated_at": now
                    }
                }
            )
            return cls.find_by_id(oid)
        except Exception:
            return None

    @classmethod
    def record_attempt(cls, claim_id: str | ObjectId, new_answers: str) -> dict | None:
        db = get_db()
        try:
            oid = ObjectId(claim_id) if isinstance(claim_id, str) else claim_id
            claim = db.claims.find_one({"_id": oid})
            if not claim:
                return None
            attempts = claim.get("attempt_count", 1) + 1
            new_status = "locked" if attempts >= cls.MAX_ATTEMPTS else "pending"
            
            db.claims.update_one(
                {"_id": oid},
                {
                    "$set": {
                        "verification_answers": new_answers.strip(),
                        "attempt_count": attempts,
                        "status": new_status,
                        "updated_at": datetime.now(timezone.utc)
                    }
                }
            )
            return cls.find_by_id(oid)
        except Exception:
            return None
