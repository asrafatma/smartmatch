from datetime import datetime, timezone
from bson import ObjectId
from pymongo import ReturnDocument
from app.repositories.db import get_db


def _oid(value):
    return ObjectId(value) if isinstance(value, str) else value


class ClaimRepository:
    MAX_ATTEMPTS = 3

    @staticmethod
    def _format(doc, mask_private=False):
        if not doc:
            return None
        doc = dict(doc)
        doc["id"] = str(doc["_id"])
        doc.pop("_id", None)
        for f in ("report_id", "claimant_id", "reviewed_by"):
            if isinstance(doc.get(f), ObjectId):
                doc[f] = str(doc[f])
        for dt_field in ["created_at", "reviewed_at", "updated_at"]:
            if dt_field in doc and isinstance(doc[dt_field], datetime):
                doc[dt_field] = doc[dt_field].isoformat()

        if mask_private and "verification_answers" in doc:
            doc["verification_answers"] = "[PRIVATE VERIFICATION DETAILS HIDDEN]"
        return doc

    @classmethod
    def create(
        cls,
        report_id: str,
        claimant_id: str,
        verification_answers: str,
        verification_status: str = "not_required",
        status: str = "pending",
        attempt_count: int = 1,
    ) -> dict:
        """
        verification_status: verified | failed | not_required (finder has no private clue)
        status (finder decision): pending | approved | rejected | locked
        """
        db = get_db()
        now = datetime.now(timezone.utc)
        doc = {
            "report_id": str(report_id),
            "claimant_id": str(claimant_id),
            "verification_answers": verification_answers.strip(),
            "verification_status": verification_status,
            "status": status,
            "attempt_count": attempt_count,
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
    def find_by_id(cls, claim_id, mask_private: bool = False) -> dict | None:
        db = get_db()
        try:
            doc = db.claims.find_one({"_id": _oid(claim_id)})
            return cls._format(doc, mask_private=mask_private)
        except Exception:
            return None

    @classmethod
    def find_by_report_and_claimant(cls, report_id: str, claimant_id: str) -> dict | None:
        db = get_db()
        doc = db.claims.find_one({"report_id": str(report_id), "claimant_id": str(claimant_id)})
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
    def list_all(cls, status: str = None, mask_private: bool = False, limit: int = 100,
                 verification_statuses: list[str] = None) -> list[dict]:
        db = get_db()
        q = {}
        if status:
            q["status"] = status
        if verification_statuses:
            q["verification_status"] = {"$in": verification_statuses}
        cursor = db.claims.find(q).sort("created_at", -1).limit(limit)
        return [cls._format(doc, mask_private=mask_private) for doc in cursor]

    @classmethod
    def update_status(
        cls, claim_id, status: str, reviewer_id: str, notes: str = None, expected_status: str = None
    ) -> dict | None:
        """Updates the finder decision. With expected_status the update is atomic and only
        applies while the claim is still in that status (returns None otherwise)."""
        db = get_db()
        try:
            oid = _oid(claim_id)
            now = datetime.now(timezone.utc)
            q = {"_id": oid}
            if expected_status:
                q["status"] = expected_status
            res = db.claims.update_one(q, {"$set": {
                "status": status,
                "reviewed_by": str(reviewer_id),
                "reviewed_at": now,
                "review_notes": notes,
                "updated_at": now
            }})
            if res.matched_count == 0:
                return None
            return cls.find_by_id(oid)
        except Exception:
            return None

    @classmethod
    def record_attempt(cls, claim_id, new_answers: str, verification_status: str) -> dict | None:
        """
        Atomically records a new verification attempt. The filter only matches while the claim
        is below the attempt limit and not locked/approved, so concurrent or replayed requests
        can never exceed MAX_ATTEMPTS. Returns None when the claim is already at the limit.
        A verified answer re-opens the claim for the finder (status pending); a failed answer
        that reaches the limit locks the claim.
        """
        db = get_db()
        try:
            oid = _oid(claim_id)
            now = datetime.now(timezone.utc)
            doc = db.claims.find_one_and_update(
                {
                    "_id": oid,
                    "attempt_count": {"$lt": cls.MAX_ATTEMPTS},
                    "status": {"$nin": ["locked", "approved"]},
                },
                {
                    "$inc": {"attempt_count": 1},
                    "$set": {
                        "verification_answers": new_answers.strip(),
                        "verification_status": verification_status,
                        "status": "pending",
                        "reviewed_by": None,
                        "reviewed_at": None,
                        "review_notes": None,
                        "updated_at": now,
                    },
                },
                return_document=ReturnDocument.AFTER,
            )
            if not doc:
                return None
            # Lock when the limit is reached without a successful verification
            if doc["attempt_count"] >= cls.MAX_ATTEMPTS and verification_status != "verified":
                db.claims.update_one({"_id": oid, "status": "pending"},
                                     {"$set": {"status": "locked", "updated_at": now}})
                doc["status"] = "locked"
            return cls._format(doc)
        except Exception:
            return None

    @classmethod
    def lock(cls, claim_id) -> None:
        db = get_db()
        db.claims.update_one({"_id": _oid(claim_id)},
                             {"$set": {"status": "locked", "updated_at": datetime.now(timezone.utc)}})

    @classmethod
    def reject_pending_for_report(
        cls, report_id: str, reviewer_id: str = None, notes: str = None, exclude_claim_id: str = None
    ) -> int:
        """Rejects every still-pending claim on a report (e.g. after another claim is approved)."""
        db = get_db()
        q = {"report_id": str(report_id), "status": "pending"}
        if exclude_claim_id:
            try:
                q["_id"] = {"$ne": ObjectId(exclude_claim_id)}
            except Exception:
                pass
        now = datetime.now(timezone.utc)
        res = db.claims.update_many(q, {"$set": {
            "status": "rejected",
            "reviewed_by": str(reviewer_id) if reviewer_id else None,
            "reviewed_at": now,
            "review_notes": notes,
            "updated_at": now
        }})
        return res.modified_count

    @classmethod
    def count_pending_for_report(cls, report_id: str) -> int:
        db = get_db()
        return db.claims.count_documents({"report_id": str(report_id), "status": "pending"})

    @classmethod
    def count_by_status(cls, status: str) -> int:
        db = get_db()
        return db.claims.count_documents({"status": status})
