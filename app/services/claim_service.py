from app.repositories.claim_repository import ClaimRepository
from app.repositories.report_repository import ReportRepository
from app.repositories.user_repository import UserRepository
from app.utils.validators import validate_claim_input

class ClaimService:
    @classmethod
    def submit_claim(
        cls,
        report_id: str,
        claimant_id: str,
        verification_answers: str
    ) -> tuple[dict | None, str | None, int]:
        valid, msg = validate_claim_input({"verification_answers": verification_answers})
        if not valid:
            return None, msg, 400

        report = ReportRepository.find_by_id(report_id)
        if not report:
            return None, "Target report not found", 404

        # Cannot claim a lost report (claims are made against found items)
        if report.get("report_type") != "found":
            return None, "Claims can only be submitted against found item reports.", 400

        # Submitter cannot claim their own report
        if str(report.get("user_id")) == str(claimant_id):
            return None, "You cannot submit an ownership claim on an item you reported having found.", 400

        # Check existing claim by this claimant
        existing = ClaimRepository.find_by_report_and_claimant(report_id, claimant_id)
        if existing:
            if existing.get("status") == "locked":
                return None, "Maximum verification attempts exceeded. This claim is locked.", 403
            if existing.get("status") == "approved":
                return existing, None, 200

            # Record a new verification attempt
            updated = ClaimRepository.record_attempt(existing["id"], verification_answers)
            if updated.get("status") == "locked":
                return None, "Verification limit reached (3 attempts). Claim is now locked.", 403
            return updated, None, 200

        # Create new claim
        created = ClaimRepository.create(
            report_id=report_id,
            claimant_id=claimant_id,
            verification_answers=verification_answers
        )

        # Update report status to claim_pending
        ReportRepository.update_status(report_id, "claim_pending")
        return created, None, 201

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

        action = action.strip().lower()
        if action not in ("approved", "rejected"):
            return None, "Invalid review action. Must be 'approved' or 'rejected'.", 400

        updated_claim = ClaimRepository.update_status(
            claim_id=claim_id,
            status=action,
            reviewer_id=reviewer_id,
            notes=notes
        )

        # Update report status accordingly
        if action == "approved":
            ReportRepository.update_status(report["id"], "resolved")
        else:
            # If rejected, return report to active if no other pending claims
            pending_claims = [c for c in ClaimRepository.list_by_report_id(report["id"]) if c["status"] == "pending"]
            if not pending_claims:
                ReportRepository.update_status(report["id"], "active")

        return updated_claim, None, 200

    @classmethod
    def get_claim(cls, claim_id: str, user_id: str, user_role: str) -> tuple[dict | None, str | None, int]:
        claim = ClaimRepository.find_by_id(claim_id)
        if not claim:
            return None, "Claim not found", 404

        report = ReportRepository.find_by_id(claim.get("report_id"))
        is_claimant = str(claim.get("claimant_id")) == str(user_id)
        is_finder = report and str(report.get("user_id")) == str(user_id)
        is_admin = user_role == "admin"

        if not (is_claimant or is_finder or is_admin):
            return None, "Access denied to private claim details", 403

        # Add claimant and finder details
        claimant = UserRepository.find_by_id(claim.get("claimant_id"))
        if claimant:
            claim["claimant_name"] = claimant.get("name")
            if claim.get("status") == "approved":
                claim["claimant_email"] = claimant.get("email")

        return claim, None, 200

    @classmethod
    def list_pending_for_reviewer(cls, user_id: str, user_role: str) -> list[dict]:
        """Lists pending claims that this user (finder or admin) has authority to review."""
        if user_role == "admin":
            all_claims = ClaimRepository.list_all(status="pending", mask_private=False)
            enriched = []
            for c in all_claims:
                rep = ReportRepository.find_by_id(c["report_id"])
                c["report_title"] = rep.get("title") if rep else "Unknown Report"
                c["report_image"] = rep.get("image_path") if rep else ""
                enriched.append(c)
            return enriched

        # If regular student / finder: list claims for reports created by this user
        user_reports = ReportRepository.list_reports(filters={"user_id": user_id, "report_type": "found"}, limit=100)
        report_ids = {r["id"] for r in user_reports}
        
        all_claims = ClaimRepository.list_all(mask_private=False)
        relevant = []
        for c in all_claims:
            if c["report_id"] in report_ids:
                rep = ReportRepository.find_by_id(c["report_id"])
                c["report_title"] = rep.get("title") if rep else "Unknown Report"
                c["report_image"] = rep.get("image_path") if rep else ""
                relevant.append(c)
        return relevant
