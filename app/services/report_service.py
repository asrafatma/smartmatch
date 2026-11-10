import json
from datetime import datetime, timezone
from app.repositories.report_repository import ReportRepository
from app.repositories.user_repository import UserRepository
from app.utils.file_handler import validate_image_file, save_upload_image
from app.utils.validators import validate_report_input
from app.ai.report_analyzer import ReportAnalyzer
from app.ai.normalizer import Normalizer
from app.config import Config

class ReportService:
    @classmethod
    def create_report(
        cls,
        user_id: str,
        form_data: dict,
        file_storage,
        upload_folder: str
    ) -> tuple[dict | None, str | None, int]:
        """
        Creates a new Lost or Found report, requiring a photo and running AI attribute extraction.
        Returns (created_report, error_message, status_code).
        """
        # 1. Validate Form Inputs
        valid, msg = validate_report_input(form_data)
        if not valid:
            return None, msg, 400

        # 2. Validate Mandatory Photograph
        is_valid_img, img_err = validate_image_file(file_storage)
        if not is_valid_img:
            return None, img_err, 400

        # 3. Save Image Securely
        try:
            rel_image_path, abs_image_path = save_upload_image(file_storage, upload_folder)
        except Exception as e:
            return None, f"Failed to save image: {str(e)}", 500

        title = form_data["title"].strip()
        description = form_data["description"].strip()
        category = form_data["category"].strip().lower()
        report_type = form_data["report_type"].strip().lower()
        location = form_data["location"].strip()
        incident_date = form_data["incident_date"].strip()

        # 4. AI Attribute Extraction with guaranteed fallback
        ai_result, ai_status, error_type = ReportAnalyzer.analyze(
            title=title,
            description=description,
            category=category,
            image_path=abs_image_path
        )

        # 5. Extract and normalize attributes
        extracted_attrs = ai_result.get("attributes", {})
        norm_attrs = Normalizer.normalize_attributes(extracted_attrs)

        # If user explicitly sent custom/manual attributes in form_data JSON, honor confirmed overrides
        if "attributes" in form_data:
            try:
                user_attrs = form_data["attributes"]
                if isinstance(user_attrs, str):
                    user_attrs = json.loads(user_attrs)
                if isinstance(user_attrs, dict):
                    norm_attrs = Normalizer.normalize_attributes(user_attrs)
            except Exception:
                pass

        # 6. Build Report Document
        report_data = {
            "user_id": user_id,
            "report_type": report_type,
            "title": title,
            "description": description,
            "category": Normalizer.normalize_category(category),
            "location": location,
            "incident_date": incident_date,
            "image_path": rel_image_path,
            "attributes": norm_attrs,
            "object_type": Normalizer.normalize_object_type(ai_result.get("object_type", title)),
            "user_stated_details": ai_result.get("user_stated_details", []),
            "visually_observed_details": ai_result.get("visually_observed_details", []),
            "unknowns": ai_result.get("unknowns", []),
            "image_quality": ai_result.get("image_quality", "adequate"),
            "ai_status": ai_status,
            "extraction_version": Config.EXTRACTION_VERSION,
            "status": "active"
        }

        created = ReportRepository.create(report_data)
        return created, None, 201

    @classmethod
    def get_report(cls, report_id: str, requesting_user_id: str = None) -> tuple[dict | None, str | None, int]:
        report = ReportRepository.find_by_id(report_id)
        if not report:
            return None, "Report not found", 404

        # Mask private contact details: public response only shows submitter name, not raw email
        submitter = UserRepository.find_by_id(report.get("user_id"))
        report_copy = dict(report)
        if submitter:
            report_copy["submitter_name"] = submitter.get("name", "Campus Member")
            # Only reveal email if requester is the submitter themselves
            if requesting_user_id and str(requesting_user_id) == str(report.get("user_id")):
                report_copy["submitter_email"] = submitter.get("email")
            else:
                report_copy["submitter_email"] = "[PROTECTED — AVAILABLE UPON APPROVED CLAIM]"
        else:
            report_copy["submitter_name"] = "Anonymous Submitter"
            report_copy["submitter_email"] = "[PROTECTED]"

        return report_copy, None, 200

    @classmethod
    def update_report(
        cls,
        report_id: str,
        user_id: str,
        user_role: str,
        update_data: dict
    ) -> tuple[dict | None, str | None, int]:
        report = ReportRepository.find_by_id(report_id)
        if not report:
            return None, "Report not found", 404

        is_owner = str(report.get("user_id")) == str(user_id)
        is_admin = user_role == "admin"

        if not (is_owner or is_admin):
            return None, "Permission denied: you cannot modify this report.", 403

        allowed_fields = {"title", "description", "category", "location", "incident_date", "attributes", "status"}
        fields_to_update = {}

        for k, v in update_data.items():
            if k in allowed_fields:
                if k == "attributes" and isinstance(v, dict):
                    fields_to_update["attributes"] = Normalizer.normalize_attributes(v)
                elif k == "category":
                    fields_to_update["category"] = Normalizer.normalize_category(v)
                elif k == "status":
                    if v in ("active", "claim_pending", "under_review", "resolved", "inactive", "closed"):
                        fields_to_update["status"] = v
                else:
                    fields_to_update[k] = v

        if not fields_to_update:
            return None, "No valid fields provided for update", 400

        updated = ReportRepository.update(report_id, fields_to_update)
        return updated, None, 200

    @classmethod
    def delete_report(cls, report_id: str, user_id: str, user_role: str) -> tuple[bool, str | None, int]:
        report = ReportRepository.find_by_id(report_id)
        if not report:
            return False, "Report not found", 404

        is_owner = str(report.get("user_id")) == str(user_id)
        is_admin = user_role == "admin"

        if not (is_owner or is_admin):
            return False, "Permission denied: you cannot delete this report.", 403

        # Mark as closed/inactive rather than hard delete to preserve history, or remove if unlinked
        ReportRepository.update_status(report_id, "closed")
        return True, None, 200

    @classmethod
    def list_reports(cls, filters: dict, page: int = 1, limit: int = 20) -> dict:
        page = max(1, page)
        limit = max(1, min(100, limit))
        skip = (page - 1) * limit

        total = ReportRepository.count(filters)
        items = ReportRepository.list_reports(filters=filters, skip=skip, limit=limit)

        return {
            "items": items,
            "total": total,
            "page": page,
            "limit": limit,
            "pages": (total + limit - 1) // limit if limit > 0 else 1
        }
