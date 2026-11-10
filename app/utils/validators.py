import re
from datetime import datetime, timedelta, timezone

EMAIL_REGEX = re.compile(r"^[\w\.\+\-]+@[a-zA-Z0-9\-]+\.[a-zA-Z0-9\-\.]+$")
VALID_CATEGORIES = {
    "electronics",
    "personal_accessory",
    "stationery",
    "bag_backpack",
    "clothing",
    "key_id",
    "bottle_container",
    "other"
}
VALID_REPORT_TYPES = {"lost", "found"}

MAX_TITLE_LENGTH = 150
MAX_DESCRIPTION_LENGTH = 2000
MAX_LOCATION_LENGTH = 200
MAX_NAME_LENGTH = 100
MAX_PASSWORD_LENGTH = 128  # bcrypt only uses the first 72 bytes; cap to avoid abuse
MAX_CLAIM_ANSWER_LENGTH = 2000


def as_str(value) -> str:
    """Coerce an untrusted input value to a stripped string. Non-scalar values become ''."""
    if value is None or isinstance(value, (dict, list, tuple, set, bool)):
        return ""
    return str(value).strip()


def parse_int(value, default: int, minimum: int = None, maximum: int = None) -> int:
    """Parse an untrusted integer query parameter, falling back to default and clamping."""
    try:
        result = int(value)
    except (TypeError, ValueError):
        result = default
    if minimum is not None:
        result = max(minimum, result)
    if maximum is not None:
        result = min(maximum, result)
    return result


def _parse_date(value: str):
    if "T" in value:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    return datetime.strptime(value, "%Y-%m-%d").date()


def _min_incident_date():
    try:
        from flask import current_app
        raw = current_app.config.get("MIN_INCIDENT_DATE", "2020-01-01")
    except RuntimeError:
        raw = "2020-01-01"
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        return datetime(2020, 1, 1).date()


def incident_date_error(value: str) -> str:
    """Returns '' when the date is valid, otherwise a user-facing error message.
    Accepted range: MIN_INCIDENT_DATE .. tomorrow (UTC, to tolerate time zones)."""
    if not value:
        return "Incident date is required."
    try:
        d = _parse_date(value)
    except (ValueError, TypeError):
        return "Incident date must be in YYYY-MM-DD format."
    latest = (datetime.now(timezone.utc) + timedelta(days=1)).date()
    earliest = _min_incident_date()
    if d > latest:
        return "Incident date cannot be in the future."
    if d < earliest:
        return f"Incident date must be on or after {earliest.isoformat()}."
    return ""


def is_valid_date(value: str) -> bool:
    return incident_date_error(value) == ""


def validate_registration_input(data: dict) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "Request payload must be a JSON object"
    name = as_str(data.get("name"))
    email = as_str(data.get("email"))
    password = data.get("password")

    if not name or len(name) < 2:
        return False, "Full name must be at least 2 characters long."
    if len(name) > MAX_NAME_LENGTH:
        return False, f"Full name must be at most {MAX_NAME_LENGTH} characters."
    if not email or not EMAIL_REGEX.match(email):
        return False, "A valid email address is required."
    if not isinstance(password, str) or len(password) < 6:
        return False, "Password must be at least 6 characters long."
    if len(password) > MAX_PASSWORD_LENGTH:
        return False, f"Password must be at most {MAX_PASSWORD_LENGTH} characters."
    return True, ""


def validate_login_input(data: dict) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "Request payload must be a JSON object"
    email = as_str(data.get("email"))
    password = data.get("password")
    if not email or not isinstance(password, str) or not password:
        return False, "Both email and password are required."
    return True, ""


def validate_report_input(form_data: dict) -> tuple[bool, str]:
    if not isinstance(form_data, dict):
        return False, "Invalid form payload."

    report_type = as_str(form_data.get("report_type")).lower()
    if report_type not in VALID_REPORT_TYPES:
        return False, f"Invalid report type '{report_type}'. Must be 'lost' or 'found'."

    title = as_str(form_data.get("title"))
    if not title or len(title) < 3:
        return False, "Title must be at least 3 characters long."
    if len(title) > MAX_TITLE_LENGTH:
        return False, f"Title exceeds maximum length of {MAX_TITLE_LENGTH} characters."

    description = as_str(form_data.get("description"))
    if not description or len(description) < 5:
        return False, "Description must be at least 5 characters long."
    if len(description) > MAX_DESCRIPTION_LENGTH:
        return False, f"Description exceeds maximum length of {MAX_DESCRIPTION_LENGTH} characters."

    category = as_str(form_data.get("category")).lower()
    if category not in VALID_CATEGORIES:
        return False, f"Invalid category '{category}'. Valid categories are: {', '.join(sorted(VALID_CATEGORIES))}."

    location = as_str(form_data.get("location"))
    if not location or len(location) < 2:
        return False, "Location is required (at least 2 characters)."
    if len(location) > MAX_LOCATION_LENGTH:
        return False, f"Location exceeds maximum length of {MAX_LOCATION_LENGTH} characters."

    date_err = incident_date_error(as_str(form_data.get("incident_date")))
    if date_err:
        return False, date_err

    return True, ""


def validate_report_update(update_data: dict) -> tuple[dict | None, str]:
    """
    Validates and cleans a partial report update. Returns (clean_fields, error).
    'attributes' and 'status' are handled by the caller (they need normalisation / authorisation).
    """
    if not isinstance(update_data, dict):
        return None, "Request payload must be a JSON object"

    clean = {}
    for field in ("title", "description", "location", "incident_date", "category"):
        if field in update_data and not isinstance(update_data[field], str):
            return None, f"{field} must be a string."
    if "title" in update_data:
        title = as_str(update_data["title"])
        if len(title) < 3 or len(title) > MAX_TITLE_LENGTH:
            return None, f"Title must be between 3 and {MAX_TITLE_LENGTH} characters."
        clean["title"] = title
    if "description" in update_data:
        description = as_str(update_data["description"])
        if len(description) < 5 or len(description) > MAX_DESCRIPTION_LENGTH:
            return None, f"Description must be between 5 and {MAX_DESCRIPTION_LENGTH} characters."
        clean["description"] = description
    if "location" in update_data:
        location = as_str(update_data["location"])
        if len(location) < 2 or len(location) > MAX_LOCATION_LENGTH:
            return None, f"Location must be between 2 and {MAX_LOCATION_LENGTH} characters."
        clean["location"] = location
    if "incident_date" in update_data:
        incident_date = as_str(update_data["incident_date"])
        date_err = incident_date_error(incident_date)
        if date_err:
            return None, date_err
        clean["incident_date"] = incident_date
    if "category" in update_data:
        category = as_str(update_data["category"]).lower()
        if category not in VALID_CATEGORIES:
            return None, f"Invalid category '{category}'."
        clean["category"] = category
    return clean, ""


def validate_claim_input(data: dict) -> tuple[bool, str]:
    answers = as_str(data.get("verification_answers")) if isinstance(data, dict) else ""
    if not answers or len(answers) < 10:
        return False, "Verification answers must provide sufficient detail (at least 10 characters)."
    if len(answers) > MAX_CLAIM_ANSWER_LENGTH:
        return False, f"Verification answers must be at most {MAX_CLAIM_ANSWER_LENGTH} characters."
    return True, ""
