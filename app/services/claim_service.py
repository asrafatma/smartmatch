from pymongo.errors import DuplicateKeyError
from app.repositories.claim_repository import ClaimRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.user_repository import UserRepository
from flask import current_app
from app.repositories.verification_repository import VerificationRepository
from app.services.verification_service import answer_matches_clue
from app.utils.validators import validate_claim_input, as_str

# Report statuses that can still receive ownership claims
CLAIMABLE_REPORT_STATUSES = ("active", "claim_pending")
# Claims the finder is allowed to see/decide: passed the private-clue check, or the finder
# configured no clue (manual review of the free-text evidence).
REVIEWABLE_VERIFICATION = ("verified", "not_required")


class ClaimService:
    @classmethod
    def submit_claim(
        cls,
        report_id: str,
        claimant_id: str,
        verification_answers: str
    ) -> tuple[dict | None, str | None, int]:
        verification_answers = as_str(verification_answers)
        valid, msg = validate_claim_input({"verification_answers": verification_answers})
        if not valid:
            return None, msg, 400

        report = ReportRepository.find_by_id(as_str(report_id))
        if not report:
            return None, "Target report not found", 404
        report_id = report["id"]

        # Cannot claim a lost report (claims are made against found items)
        if report.get("report_type") != "found":
            return None, "Claims can only be submitted against found item reports.", 400

        # Submitter cannot claim their own report
        if str(report.get("user_id")) == str(claimant_id):
            return None, "You cannot submit an ownership claim on an item you reported having found.", 400

        # Check existing claim by this claimant
        existing = ClaimRepository.find_by_report_and_claimant(report_id, claimant_id)
        if existing and existing.get("status") == "approved":
            return existing, None, 200

        # Resolved / closed / inactive reports no longer accept claims
        if report.get("status") not in CLAIMABLE_REPORT_STATUSES:
            return None, "This item is no longer accepting ownership claims.", 409

        # Server-side verification against the finder's private clue (never sent to clients)
        clue = VerificationRepository.get_clue(report_id)
        if clue:
            threshold = current_app.config.get("CLAIM_VERIFICATION_THRESHOLD", 0.6)
            verification_status = "verified" if answer_matches_clue(verification_answers, clue, threshold) else "failed"
        else:
            verification_status = "not_required"

        max_attempts = ClaimRepository.MAX_ATTEMPTS
        locked_msg = f"Maximum verification attempts ({max_attempts}) exceeded. This claim is locked."

        if existing:
            if existing.get("status") == "locked":
                return None, locked_msg, 429
            if existing.get("verification_status") == "verified" and existing.get("status") == "pending":
                # Already verified and waiting for the finder; nothing to retry
                return existing, None, 200

            updated = ClaimRepository.record_attempt(existing["id"], verification_answers, verification_status)
            if not updated:
                # Already at the attempt limit (also guards concurrent/replayed requests)
                ClaimRepository.lock(existing["id"])
                return None, locked_msg, 429
            if updated.get("status") == "locked":
                cls._sync_report_status(report)
                return None, locked_msg, 429
            if verification_status == "failed":
                remaining = max_attempts - updated.get("attempt_count", max_attempts)
                return None, cls._failed_msg(remaining), 400
            cls._mark_claim_pending(report)
            return updated, None, 200

        try:
            created = ClaimRepository.create(
                report_id=report_id,
                claimant_id=claimant_id,
                verification_answers=verification_answers,
                verification_status=verification_status,
            )
        except DuplicateKeyError:
            # Concurrent duplicate submission: the unique index allows only one claim per user/item
            return None, "A claim for this item is already being processed. Please retry.", 409

        if verification_status == "failed":
            return None, cls._failed_msg(max_attempts - 1), 400

        cls._mark_claim_pending(report)
        return created, None, 201

    @staticmethod
    def _failed_msg(remaining: int) -> str:
        # Generic message: never reveal which part of the private clue was missing
        return (f"Verification failed: your answer does not match the finder's private ownership details. "
                f"{max(0, remaining)} attempt(s) remaining.")

    @staticmethod
    def _mark_claim_pending(report: dict):
        # Only move active reports into claim_pending; never resurrect resolved/closed ones
        if report.get("status") == "active":
            ReportRepository.update_status(report["id"], "claim_pending")

    @staticmethod
    def _sync_report_status(report: dict):
        """Return a claim_pending report to active once no claims await review."""
        fresh = ReportRepository.find_by_id(report["id"])
        if fresh and fresh.get("status") == "claim_pending" \
                and ClaimRepository.count_pending_for_report(report["id"]) == 0:
            ReportRepository.update_status(report["id"], "active")

    @classmethod
    def review_claim(
        cls,
        claim_id: str,
        reviewer_id: str,
        reviewer_role: str,
        action: str,
        notes: str = None
    ) -> tuple[dict | None, str | None, int]:
        claim = ClaimRepository.find_by_id(claim_id)
        if not claim:
            return None, "Claim not found", 404

        report = ReportRepository.find_by_id(claim.get("report_id"))
        if not report:
            return None, "Associated report not found", 404

        is_finder = str(report.get("user_id")) == str(reviewer_id)
        is_admin = reviewer_role == "admin"

        if not (is_finder or is_admin):
            return None, "Permission denied: only the item finder or an administrator may review claims.", 403

        # User cannot review their own claim if they were the claimant
        if str(claim.get("claimant_id")) == str(reviewer_id):
            return None, "You cannot review your own claim.", 403

        action = as_str(action).lower()
        if action not in ("approved", "rejected"):
            return None, "Invalid review action. Must be 'approved' or 'rejected'.", 400

        notes = as_str(notes)[:1000] or None

        if claim.get("status") != "pending":
            return None, f"This claim has already been {claim.get('status')} and cannot be reviewed again.", 409

        if action == "approved" and claim.get("verification_status", "not_required") not in REVIEWABLE_VERIFICATION:
            return None, "This claim has not passed ownership verification and cannot be approved.", 409

        if action == "approved" and report.get("status") not in CLAIMABLE_REPORT_STATUSES:
            return None, "This item is already resolved or closed; no further claims can be approved.", 409

        # Atomic: only succeeds if the claim is still pending (guards concurrent reviews)
        updated_claim = ClaimRepository.update_status(
            claim_id=claim["id"],
            status=action,
            reviewer_id=reviewer_id,
            notes=notes,
            expected_status="pending"
        )
        if not updated_claim:
            return None, "This claim was already reviewed by someone else.", 409

        if action == "approved":
            ReportRepository.update_status(report["id"], "resolved")
            # Only one owner per item: close out competing claims
            ClaimRepository.reject_pending_for_report(
                report["id"],
                reviewer_id=reviewer_id,
                notes="Another ownership claim was approved for this item.",
                exclude_claim_id=claim["id"]
            )
        else:
            cls._sync_report_status(report)

        return updated_claim, None, 200

    @classmethod
    def get_claim(cls, claim_id: str, user_id: str, user_role: str) -> tuple[dict | None, str | None, int]:
        claim = ClaimRepository.find_by_id(claim_id)
        if not claim:
            return None, "Claim not found", 404

        report = ReportRepository.find_by_id(claim.get("report_id"))
        is_claimant = str(claim.get("claimant_id")) == str(user_id)
        is_finder = bool(report) and str(report.get("user_id")) == str(user_id)
        is_admin = user_role == "admin"

        if not (is_claimant or is_finder or is_admin):
            return None, "Access denied to private claim details", 403

        claimant = UserRepository.find_by_id(claim.get("claimant_id"))
        if claimant:
            claim["claimant_name"] = claimant.get("name")
            if claim.get("status") == "approved":
                claim["claimant_email"] = claimant.get("email")

        return claim, None, 200

    @classmethod
    def _enrich(cls, claims: list[dict]) -> list[dict]:
        cache = {}
        for c in claims:
            rid = c["report_id"]
            if rid not in cache:
                cache[rid] = ReportRepository.find_by_id(rid)
            rep = cache[rid]
            c["report_title"] = rep.get("title") if rep else "Unknown Report"
            c["report_image"] = rep.get("image_path") if rep else ""
        return claims

    @classmethod
    def list_pending_for_reviewer(cls, user_id: str, user_role: str) -> list[dict]:
        """Lists pending claims that this user (finder or admin) has authority to review."""
        if user_role == "admin":
            return cls._enrich(ClaimRepository.list_all(
                status="pending", mask_private=False, verification_statuses=list(REVIEWABLE_VERIFICATION)
            ))

        # Regular finder: only pending claims on found reports this user created
        user_reports = ReportRepository.list_reports(
            filters={"user_id": user_id, "report_type": "found"}, limit=500
        )
        report_ids = {r["id"] for r in user_reports}
        pending = ClaimRepository.list_all(
            status="pending", mask_private=False, limit=500,
            verification_statuses=list(REVIEWABLE_VERIFICATION)
        )
        return cls._enrich([c for c in pending if c["report_id"] in report_ids])

    @classmethod
    def list_for_claimant(cls, user_id: str) -> list[dict]:
        return cls._enrich(ClaimRepository.list_by_claimant(user_id))
