from app.repositories.report_repository import ReportRepository
from app.repositories.claim_repository import ClaimRepository
from app.repositories.user_repository import UserRepository

HANDOVER_INSTRUCTIONS = (
    "Please arrange a safe, well-lit campus handover location "
    "(e.g. Student Center or Campus Security Desk). Never share identity documents."
)


class ContactService:
    @classmethod
    def get_authorized_contact(
        cls, report_id: str, requesting_user_id: str, user_role: str = None
    ) -> tuple[dict | None, str | None, int]:
        """
        Contact disclosure rule (design report 9.2):
          (a) the finder of the found report, or
          (b) the claimant whose claim on that report was approved by the finder.
        Everyone else, including administrators, receives 403. There is deliberately no admin
        bypass for contact details. `user_role` is accepted for API compatibility only.
        """
        report = ReportRepository.find_by_id(report_id)
        if not report:
            return None, "Report not found", 404

        if report.get("report_type") != "found":
            return None, "Contact details are only available for found-item reports.", 400

        finder_id = str(report.get("user_id"))
        req_id = str(requesting_user_id)

        claims = ClaimRepository.list_by_report_id(report["id"], mask_private=False)
        approved_claim = next((c for c in claims if c.get("status") == "approved"), None)

        is_finder = req_id == finder_id
        is_approved_claimant = bool(approved_claim) and req_id == str(approved_claim.get("claimant_id"))

        if not (is_finder or is_approved_claimant):
            return None, (
                "Handover contact details are protected and only released to the finder "
                "and the claimant whose ownership claim was approved."
            ), 403

        finder_user = UserRepository.find_by_id(finder_id)
        result = {
            "report_id": report["id"],
            "report_title": report.get("title"),
            "claim_status": "approved" if approved_claim else "no_approved_claim",
            "finder": {
                "name": finder_user.get("name") if finder_user else "Finder",
                "email": finder_user.get("email") if finder_user else None
            },
            "claimant": None,
            "handover_instructions": HANDOVER_INSTRUCTIONS,
        }
        if approved_claim:
            claimant_user = UserRepository.find_by_id(approved_claim.get("claimant_id"))
            result["claimant"] = {
                "name": claimant_user.get("name") if claimant_user else "Claimant",
                "email": claimant_user.get("email") if claimant_user else None
            }
        return result, None, 200
