import json
import logging
import os
import uuid
from bson import ObjectId
from flask import g
from app.repositories.report_repository import ReportRepository
from app.repositories.user_repository import UserRepository
from app.repositories.claim_repository import ClaimRepository
from app.repositories.ai_log_repository import AILogRepository
from app.repositories.verification_repository import VerificationRepository
from app.utils.file_handler import inspect_image, save_upload_image, delete_image_file, ImageValidationError
from app.utils.validators import (
    validate_report_input, validate_report_update, as_str, MAX_TITLE_LENGTH, MAX_DESCRIPTION_LENGTH
)
from app.ai.report_analyzer import ReportAnalyzer
from app.ai.normalizer import Normalizer
from app.config import Config

logger = logging.getLogger(__name__)

# Statuses a report owner may set themselves. Workflow statuses (claim_pending, under_review)
# are driven by the claim process and may only be set manually by an administrator.
OWNER_SETTABLE_STATUSES = {"active", "resolved", "inactive", "closed"}
ADMIN_SETTABLE_STATUSES = OWNER_SETTABLE_STATUSES | {"claim_pending", "under_review"}

class ReportService:


    @staticmethod
    def _parse_json_field(value):
        if value is None or value == "":
            return None
        if isinstance(value, (dict, list)):
            return value
        try:
            return json.loads(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _clean_str_list(value, max_items: int = 20, max_len: int = 200) -> list[str]:
        if not isinstance(value, list):
            return []
        out = []
        for v in value[:max_items]:
            v = as_str(v)[:max_len]
            if v:
                out.append(v)
        return out

    @classmethod
    def analyze_preview(cls, form_data: dict, file_storage, upload_folder: str) -> tuple[dict | None, str | None, int, str | None]:
        """
        Step 1 of the reporting flow: validate the photo + text and return AI attribute
        suggestions WITHOUT saving a report. The user reviews/edits them, then submits.
        Returns (payload, error_message, status_code, error_code).
        """
        title = as_str(form_data.get("title"))
        description = as_str(form_data.get("description"))
        category = as_str(form_data.get("category")).lower() or "other"
        if len(title) < 3 or len(description) < 5:
            return None, "Enter a title (3+ characters) and description (5+ characters) before analysis.", 400, "VALIDATION_ERROR"
        if len(title) > MAX_TITLE_LENGTH or len(description) > MAX_DESCRIPTION_LENGTH:
            return None, "Title or description is too long.", 400, "VALIDATION_ERROR"
        try:
            ext = inspect_image(file_storage)
        except ImageValidationError as e:
            return None, e.message, e.status, e.code

        tmp_dir = os.path.join(upload_folder, "_analysis")
        os.makedirs(tmp_dir, exist_ok=True)
        tmp_path = os.path.join(tmp_dir, f"{uuid.uuid4().hex}.{ext}")
        try:
            file_storage.seek(0)
            file_storage.save(tmp_path)
            result, ai_status, error_type, log_id = ReportAnalyzer.analyze_with_log(
                title=title, description=description, category=category, image_path=tmp_path
            )
        finally:
            delete_image_file(tmp_path)

        normalized = Normalizer.normalize_attributes(result.get("attributes", {}))
        return {
            "analysis_id": log_id,
            "ai_status": ai_status,
            "error_type": error_type,
            "suggestion": {
                "object_type": Normalizer.normalize_object_type(result.get("object_type") or title),
                "category": Normalizer.normalize_category(result.get("category") or category),
                "attributes": normalized,
                "user_stated_details": result.get("user_stated_details", []),
                "visually_observed_details": result.get("visually_observed_details", []),
                "unknowns": result.get("unknowns", []),
                "image_quality": result.get("image_quality", "adequate"),
            },
            "notice": "AI suggestions only. Review and edit before submitting.",
        }, None, 200, None

    @classmethod
    def create_report(
        cls,
        user_id: str,
        form_data: dict,
        file_storage,
        upload_folder: str
    ) -> tuple[dict | None, str | None, int]:
        """
        Creates a new Lost or Found report. A photo is mandatory.
        - If the user confirmed attributes (after the /analyze review step, or manually), those
          are saved as-is (normalized) and AI is not called again.
        - Otherwise AI extraction runs now, with guaranteed rule-based fallback.
        Returns (created_report, error_message, status_code). On error, `flask.g.report_error_code`
        holds a machine-readable code (e.g. PHOTO_REQUIRED).
        """
        g.report_error_code = None

        # 1. Validate mandatory photograph first (spec: missing photo -> 400 PHOTO_REQUIRED)
        try:
            ext = inspect_image(file_storage)
        except ImageValidationError as e:
            g.report_error_code = e.code
            return None, e.message, e.status

        # 2. Validate form inputs
        valid, msg = validate_report_input(form_data)
        if not valid:
            g.report_error_code = "VALIDATION_ERROR"
            return None, msg, 400

        report_type = as_str(form_data["report_type"]).lower()
        clue = as_str(form_data.get("verification_clue"))
        if clue and report_type != "found":
            clue = ""  # private clues only apply to found items
        if clue and not (3 <= len(clue) <= 300):
            g.report_error_code = "VALIDATION_ERROR"
            return None, "Private verification clue must be between 3 and 300 characters.", 400

        confirmed = cls._parse_json_field(form_data.get("confirmed_attributes"))
        if confirmed is None:
            confirmed = cls._parse_json_field(form_data.get("attributes"))  # legacy field name
        if confirmed is not None and not isinstance(confirmed, dict):
            g.report_error_code = "VALIDATION_ERROR"
            return None, "confirmed_attributes must be a JSON object.", 400

        # 3. Save image under a random server-generated name
        try:
            rel_image_path, abs_image_path = save_upload_image(file_storage, upload_folder, ext=ext)
        except Exception as e:
            logger.exception("Failed to save image: %s", e)
            g.report_error_code = "STORAGE_ERROR"
            return None, "Failed to save image. Please try again.", 500

        title = as_str(form_data["title"])
        description = as_str(form_data["description"])
        category = as_str(form_data["category"]).lower()
        location = as_str(form_data["location"])
        incident_date = as_str(form_data["incident_date"])

        report_oid = ObjectId()
        details = cls._parse_json_field(form_data.get("ai_details")) or {}
        if not isinstance(details, dict):
            details = {}

        if confirmed is not None:
            # 4a. User-confirmed attributes (from the review step or manual entry)
            norm_attrs = Normalizer.normalize_attributes(confirmed)
            object_type = Normalizer.normalize_object_type(as_str(confirmed.get("object_type")) or title)
            attribute_source = "user_confirmed"
            ai_status = "manual"
            analysis_id = as_str(form_data.get("analysis_id"))
            if analysis_id:
                log = AILogRepository.find_by_id(analysis_id)
                # Only trust a preview analysis that has not been used for another report
                if log and log.get("report_id") is None and AILogRepository.attach_report(analysis_id, str(report_oid)):
                    ai_status = log.get("status", "manual")
            ai_result = {
                "user_stated_details": cls._clean_str_list(details.get("user_stated_details")),
                "visually_observed_details": cls._clean_str_list(details.get("visually_observed_details")),
                "unknowns": cls._clean_str_list(details.get("unknowns")),
                "image_quality": as_str(details.get("image_quality")) or "adequate",
            }
            if ai_status == "manual" and not ai_result["visually_observed_details"]:
                ai_result["visually_observed_details"] = ["Manual entry: image not processed by AI"]
        else:
            # 4b. No confirmed attributes: run AI now with guaranteed fallback
            try:
                ai_result, ai_status, _error_type = ReportAnalyzer.analyze(
                    title=title, description=description, category=category,
                    image_path=abs_image_path, report_id=str(report_oid)
                )
            except Exception as e:
                logger.exception("Report analysis crashed: %s", e)
                ai_result = ReportAnalyzer.fallback_extract(title, description, category)
                ai_status = "failed"
            norm_attrs = Normalizer.normalize_attributes(ai_result.get("attributes", {}))
            object_type = Normalizer.normalize_object_type(ai_result.get("object_type") or title)
            attribute_source = "ai" if ai_status == "completed" else "rule_based_fallback"

        report_data = {
            "_id": report_oid,
            "user_id": user_id,
            "report_type": report_type,
            "title": title,
            "description": description,
            "category": Normalizer.normalize_category(category),
            "location": location,
            "incident_date": incident_date,
            "image_path": rel_image_path,
            "attributes": norm_attrs,
            "object_type": object_type,
            "user_stated_details": ai_result.get("user_stated_details", []),
            "visually_observed_details": ai_result.get("visually_observed_details", []),
            "unknowns": ai_result.get("unknowns", []),
            "image_quality": ai_result.get("image_quality", "adequate"),
            "ai_status": ai_status,
            "attribute_source": attribute_source,
            "extraction_version": Config.EXTRACTION_VERSION,
            "status": "active"
        }

        try:
            created = ReportRepository.create(report_data)
            if clue:
                VerificationRepository.set_clue(created["id"], clue)
        except Exception as e:
            delete_image_file(abs_image_path)
            logger.exception("Failed to persist report: %s", e)
            g.report_error_code = "STORAGE_ERROR"
            return None, "Failed to save report. Please try again.", 500

        created["has_private_clue"] = bool(clue)
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
                if report.get("report_type") == "found":
                    # Owner only: whether a private clue exists (never the clue itself)
                    report_copy["has_private_clue"] = VerificationRepository.has_clue(report["id"])
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

        clean, err = validate_report_update(update_data)
        if err:
            return None, err, 400
        fields_to_update = dict(clean)
        if "category" in fields_to_update:
            fields_to_update["category"] = Normalizer.normalize_category(fields_to_update["category"])

        if "attributes" in update_data:
            if not isinstance(update_data["attributes"], dict):
                return None, "attributes must be an object", 400
            fields_to_update["attributes"] = Normalizer.normalize_attributes(update_data["attributes"])

        if "status" in update_data:
            new_status = as_str(update_data["status"]).lower()
            allowed = ADMIN_SETTABLE_STATUSES if is_admin else OWNER_SETTABLE_STATUSES
            if new_status not in allowed:
                return None, f"Status '{new_status}' cannot be set. Allowed: {', '.join(sorted(allowed))}.", 400
            fields_to_update["status"] = new_status

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

        # Mark as closed rather than hard delete to preserve history
        ReportRepository.update_status(report_id, "closed")
        # A closed report can no longer be claimed: close out any claims still awaiting review
        ClaimRepository.reject_pending_for_report(
            report_id, reviewer_id=user_id, notes="Report closed by owner/admin"
        )
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
