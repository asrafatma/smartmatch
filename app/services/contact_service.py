from app.repositories.report_repository import ReportRepository
from app.repositories.claim_repository import ClaimRepository
from app.repositories.user_repository import UserRepository

class ContactService:
    @classmethod
    def get_authorized_contact(cls, report_id: str, requesting_user_id: str, user_role: str) -> tuple[dict | None, str | None, int]:
        """
        Retrieves direct handover contact information for an item report.
        Contact details are strictly confidential and only revealed if an approved
        ownership claim exists, and the requester is the claimant, the finder, or an admin.
        """
        report = ReportRepository.find_by_id(report_id)
        if not report:
            return None, "Report not found", 404

        # Find approved claim for this report
        claims = ClaimRepository.list_by_report_id(report_id, mask_private=False)
        approved_claim = next((c for c in claims if c.get("status") == "approved"), None)

        if not approved_claim:
            return None, "Handover contact details are protected and only released upon an approved ownership claim.", 403

        finder_id = str(report.get("user_id"))
        claimant_id = str(approved_claim.get("claimant_id"))
        req_id = str(requesting_user_id)

        is_finder = req_id == finder_id
        is_claimant = req_id == claimant_id
        is_admin = user_role == "admin"

        if not (is_finder or is_claimant or is_admin):
            return None, "You are not authorized to view the contact details for this report.", 403

        finder_user = UserRepository.find_by_id(finder_id)
        claimant_user = UserRepository.find_by_id(claimant_id)

        return {
            "report_id": report_id,
            "report_title": report.get("title"),
            "claim_status": "approved",
            "finder": {
                "name": finder_user.get("name") if finder_user else "Finder",
                "email": finder_user.get("email") if finder_user else None
            },
            "claimant": {
                "name": claimant_user.get("name") if claimant_user else "Claimant",
                "email": claimant_user.get("email") if claimant_user else None
            },
            "handover_instructions": "Please arrange a safe, well-lit campus handover location (e.g. Student Center or Campus Security Desk)."
        }, None, 200
