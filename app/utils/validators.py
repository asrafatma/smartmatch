import re
from datetime import datetime

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

def validate_registration_input(data: dict) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "Request payload must be a JSON object"
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "")

    if not name or len(name) < 2:
        return False, "Full name must be at least 2 characters long."
    if not email or not EMAIL_REGEX.match(email):
        return False, "A valid email address is required."
    if not password or len(password) < 6:
        return False, "Password must be at least 6 characters long."
    return True, ""

def validate_login_input(data: dict) -> tuple[bool, str]:
    if not isinstance(data, dict):
        return False, "Request payload must be a JSON object"
    email = data.get("email", "").strip()
    password = data.get("password", "")
    if not email or not password:
        return False, "Both email and password are required."
    return True, ""

def validate_report_input(form_data: dict) -> tuple[bool, str]:
    report_type = form_data.get("report_type", "").strip().lower()
    if report_type not in VALID_REPORT_TYPES:
        return False, f"Invalid report type '{report_type}'. Must be 'lost' or 'found'."

    title = form_data.get("title", "").strip()
    if not title or len(title) < 3:
        return False, "Title must be at least 3 characters long."
    if len(title) > 150:
        return False, "Title exceeds maximum length of 150 characters."

    description = form_data.get("description", "").strip()
    if not description or len(description) < 5:
        return False, "Description must be at least 5 characters long."

    category = form_data.get("category", "").strip().lower()
    if category not in VALID_CATEGORIES:
        return False, f"Invalid category '{category}'. Valid categories are: {', '.join(sorted(VALID_CATEGORIES))}."

    location = form_data.get("location", "").strip()
    if not location or len(location) < 2:
        return False, "Location is required (at least 2 characters)."

    incident_date = form_data.get("incident_date", "").strip()
    if not incident_date:
        return False, "Incident date is required."
    try:
        # Accept YYYY-MM-DD or full ISO
        if "T" in incident_date:
            datetime.fromisoformat(incident_date.replace("Z", "+00:00"))
        else:
            datetime.strptime(incident_date, "%Y-%m-%d")
    except Exception:
        return False, "Incident date must be in YYYY-MM-DD format."

    return True, ""

def validate_claim_input(data: dict) -> tuple[bool, str]:
    answers = data.get("verification_answers", "").strip()
    if not answers or len(answers) < 10:
        return False, "Verification answers must provide sufficient detail (at least 10 characters)."
    return True, ""
