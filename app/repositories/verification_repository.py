from datetime import datetime, timezone
from app.repositories.db import get_db


class VerificationRepository:
    """
    Stores the finder's private ownership clue for a found report.
    Kept in its own collection so it can never leak through report list/detail/match responses.
    """

    @classmethod
    def set_clue(cls, report_id: str, clue_text: str) -> None:
        db = get_db()
        now = datetime.now(timezone.utc)
        db.verification_clues.update_one(
            {"report_id": str(report_id)},
            {"$set": {"report_id": str(report_id), "clue_text": clue_text.strip(), "updated_at": now},
             "$setOnInsert": {"created_at": now}},
            upsert=True
        )

    @classmethod
    def get_clue(cls, report_id: str) -> str | None:
        db = get_db()
        doc = db.verification_clues.find_one({"report_id": str(report_id)})
        return doc.get("clue_text") if doc else None

    @classmethod
    def has_clue(cls, report_id: str) -> bool:
        return cls.get_clue(report_id) is not None
