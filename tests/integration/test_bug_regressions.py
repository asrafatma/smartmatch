"""Regression tests for bugs found in the project audit."""
import os
from app.ai.gemini_client import GeminiClient
from app.repositories.ai_log_repository import AILogRepository
from app.services.matching_service import MatchingEngine


def _create_report(client, headers, image_factory, report_type="found", **overrides):
    data = {
        "report_type": report_type,
        "title": "Black Leather Wallet",
        "description": "Black leather wallet with stitched edges",
        "category": "personal_accessory",
        "location": "Main Library",
        "incident_date": "2026-11-08",
        "image": (image_factory(), "wallet.jpg"),
    }
    data.update(overrides)
    res = client.post("/api/reports", data=data, headers=headers, content_type="multipart/form-data")
    assert res.status_code == 201, res.get_json()
    return res.get_json()["data"]


# ---------------- Auth ----------------

def test_register_cannot_self_assign_admin_role(client):
    res = client.post("/api/auth/register", json={
        "name": "Eve", "email": "eve@x.edu", "password": "secret12", "role": "admin"
    })
    assert res.status_code == 400
    assert "invite code" in res.get_json()["error"]


def test_register_admin_with_valid_invite_code(client):
    res = client.post("/api/auth/register", json={
        "name": "Staff", "email": "staff@x.edu", "password": "secret12",
        "admin_code": "test-admin-invite-code"
    })
    assert res.status_code == 201
    assert res.get_json()["data"]["user"]["role"] == "admin"


def test_register_admin_with_wrong_invite_code(client):
    res = client.post("/api/auth/register", json={
        "name": "Staff", "email": "staff2@x.edu", "password": "secret12", "admin_code": "nope"
    })
    assert res.status_code == 400


def test_register_without_role_defaults_to_student(client):
    res = client.post("/api/auth/register", json={
        "name": "Sam", "email": "sam@x.edu", "password": "secret12"
    })
    assert res.status_code == 201
    assert res.get_json()["data"]["user"]["role"] == "student"


def test_null_and_non_string_fields_return_400_not_500(client):
    assert client.post("/api/auth/register", json={
        "name": None, "email": "a@b.co", "password": "xxxxxxxx"
    }).status_code == 400
    assert client.post("/api/auth/register", json={
        "name": "Ok Name", "email": 12345, "password": "xxxxxxxx"
    }).status_code == 400
    assert client.post("/api/auth/login", json={"email": None, "password": None}).status_code == 401
    assert client.post("/api/auth/register", json=["not", "an", "object"]).status_code == 400


# ---------------- Query parsing / search ----------------

def test_invalid_pagination_params_do_not_crash(client):
    assert client.get("/api/reports?page=abc&limit=xyz").status_code == 200
    assert client.get("/api/reports?page=-5&limit=100000").status_code == 200


def test_search_is_literal_not_regex(client, student_auth_headers, image_factory):
    _create_report(client, student_auth_headers, image_factory, title="Wallet (black)")
    res = client.get("/api/reports?search=(black)&status=active")
    assert res.status_code == 200
    data = res.get_json()["data"]
    assert data["total"] == 1  # count uses the same filter as the list
    assert len(data["items"]) == 1
    # A regex metacharacter pattern must not match everything
    assert client.get("/api/reports?search=.*").get_json()["data"]["total"] == 0


# ---------------- Uploads ----------------

def test_uploaded_image_is_served(client, student_auth_headers, image_factory):
    report = _create_report(client, student_auth_headers, image_factory)
    assert client.get(report["image_path"]).status_code == 200


def test_upload_folder_is_absolute(app):
    assert os.path.isabs(app.config["UPLOAD_FOLDER"])


# ---------------- Matches authorization ----------------

def test_matches_require_authentication(client, student_auth_headers, image_factory):
    report = _create_report(client, student_auth_headers, image_factory, report_type="lost")
    assert client.get(f"/api/matches/{report['id']}").status_code == 401


def test_matches_only_visible_to_owner_or_admin(
    client, student_auth_headers, finder_auth_headers, admin_auth_headers, image_factory
):
    report = _create_report(client, student_auth_headers, image_factory, report_type="lost")
    assert client.get(f"/api/matches/{report['id']}", headers=finder_auth_headers).status_code == 403
    assert client.get(f"/api/matches/{report['id']}", headers=student_auth_headers).status_code == 200
    assert client.get(f"/api/matches/{report['id']}", headers=admin_auth_headers).status_code == 200


def test_match_records_do_not_persist_candidate_snapshot(
    app, client, student_auth_headers, finder_auth_headers, image_factory
):
    lost = _create_report(client, student_auth_headers, image_factory, report_type="lost")
    _create_report(client, finder_auth_headers, image_factory, report_type="found")
    res = client.get(f"/api/matches/{lost['id']}", headers=student_auth_headers)
    assert res.get_json()["count"] == 1
    from app.repositories.db import get_db
    with app.app_context():
        stored = get_db().matches.find_one({"lost_report_id": lost["id"]})
        assert stored is not None
        assert "candidate_report" not in stored


# ---------------- Report updates ----------------

def test_patch_rejects_invalid_field_types(client, student_auth_headers, image_factory):
    report = _create_report(client, student_auth_headers, image_factory)
    rid = report["id"]
    assert client.patch(f"/api/reports/{rid}", json={"location": 123}, headers=student_auth_headers).status_code == 400
    assert client.patch(f"/api/reports/{rid}", json={"incident_date": "yesterday"}, headers=student_auth_headers).status_code == 400
    assert client.patch(f"/api/reports/{rid}", json={"category": "spaceship"}, headers=student_auth_headers).status_code == 400
    assert client.patch(f"/api/reports/{rid}", json={"location": "Science Hall"}, headers=student_auth_headers).status_code == 200


def test_owner_cannot_set_workflow_statuses(client, student_auth_headers, admin_auth_headers, image_factory):
    report = _create_report(client, student_auth_headers, image_factory)
    rid = report["id"]
    assert client.patch(f"/api/reports/{rid}", json={"status": "claim_pending"}, headers=student_auth_headers).status_code == 400
    assert client.patch(f"/api/reports/{rid}", json={"status": "claim_pending"}, headers=admin_auth_headers).status_code == 200


# ---------------- Claims ----------------

def test_claim_on_resolved_report_rejected_and_status_kept(
    client, student_auth_headers, finder_auth_headers, admin_auth_headers, image_factory
):
    found = _create_report(client, finder_auth_headers, image_factory)
    client.patch(f"/api/reports/{found['id']}", json={"status": "resolved"}, headers=finder_auth_headers)
    res = client.post("/api/claims", json={
        "report_id": found["id"], "verification_answers": "It has my initials inside it"
    }, headers=student_auth_headers)
    assert res.status_code == 409
    status = client.get(f"/api/reports/{found['id']}").get_json()["data"]["status"]
    assert status == "resolved"


def test_claim_cannot_be_reviewed_twice(client, student_auth_headers, finder_auth_headers, image_factory):
    found = _create_report(client, finder_auth_headers, image_factory)
    claim = client.post("/api/claims", json={
        "report_id": found["id"], "verification_answers": "It has my initials inside it"
    }, headers=student_auth_headers).get_json()["data"]
    first = client.patch(f"/api/claims/{claim['id']}", json={"action": "rejected"}, headers=finder_auth_headers)
    assert first.status_code == 200
    second = client.patch(f"/api/claims/{claim['id']}", json={"action": "approved"}, headers=finder_auth_headers)
    assert second.status_code == 409
    # Rejection with no other pending claims returns the report to active
    assert client.get(f"/api/reports/{found['id']}").get_json()["data"]["status"] == "active"


def test_approving_one_claim_rejects_competing_claims(
    client, student_auth_headers, finder_auth_headers, admin_auth_headers, image_factory
):
    found = _create_report(client, finder_auth_headers, image_factory)
    c1 = client.post("/api/claims", json={
        "report_id": found["id"], "verification_answers": "Student claim with details"
    }, headers=student_auth_headers).get_json()["data"]
    c2 = client.post("/api/claims", json={
        "report_id": found["id"], "verification_answers": "Admin claim with details"
    }, headers=admin_auth_headers).get_json()["data"]

    assert client.patch(f"/api/claims/{c1['id']}", json={"action": "approved"},
                        headers=finder_auth_headers).status_code == 200
    other = client.get(f"/api/claims/{c2['id']}", headers=admin_auth_headers).get_json()["data"]
    assert other["status"] == "rejected"
    assert client.patch(f"/api/claims/{c2['id']}", json={"action": "approved"},
                        headers=finder_auth_headers).status_code == 409


def test_closing_report_rejects_pending_claims(client, student_auth_headers, finder_auth_headers, image_factory):
    found = _create_report(client, finder_auth_headers, image_factory)
    claim = client.post("/api/claims", json={
        "report_id": found["id"], "verification_answers": "It has my initials inside it"
    }, headers=student_auth_headers).get_json()["data"]
    assert client.delete(f"/api/reports/{found['id']}", headers=finder_auth_headers).status_code == 200
    got = client.get(f"/api/claims/{claim['id']}", headers=student_auth_headers).get_json()["data"]
    assert got["status"] == "rejected"


def test_my_claims_include_report_title(client, student_auth_headers, finder_auth_headers, image_factory):
    found = _create_report(client, finder_auth_headers, image_factory)
    client.post("/api/claims", json={
        "report_id": found["id"], "verification_answers": "It has my initials inside it"
    }, headers=student_auth_headers)
    mine = client.get("/api/claims?scope=mine", headers=student_auth_headers).get_json()["data"]
    assert mine[0]["report_title"] == "Black Leather Wallet"


# ---------------- AI integration ----------------

def test_gemini_model_env_var_is_honoured(monkeypatch):
    monkeypatch.setenv("GEMINI_MODEL", "gemini-custom-model")
    assert GeminiClient(api_key="").model_name == "gemini-custom-model"
    assert GeminiClient(api_key="", model_name="explicit").model_name == "explicit"
    monkeypatch.delenv("GEMINI_MODEL")
    assert GeminiClient(api_key="").model_name == "gemini-2.5-flash"


def test_ai_log_is_linked_to_report(app, client, student_auth_headers, image_factory, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    report = _create_report(client, student_auth_headers, image_factory)
    with app.app_context():
        logs = AILogRepository.list_logs()
    assert logs[0]["report_id"] == report["id"]


def test_gemini_mime_detected_from_content(tmp_path):
    from PIL import Image
    path = tmp_path / "actually_png.jpg"
    Image.new("RGB", (10, 10)).save(path, format="PNG")
    assert GeminiClient.detect_mime_type(str(path)) == "image/png"


# ---------------- Matching engine ----------------

def _rep(**kw):
    base = {
        "category": "bag_backpack", "object_type": "backpack", "location": "Library",
        "incident_date": "2026-11-01", "description": "", "attributes": {}
    }
    base.update(kw)
    return base


def test_distinctive_terms_use_whole_words():
    a = _rep(description="vintage briefcase with discover logo")
    b = _rep(description="tag on the case cover")
    result = MatchingEngine.compare_reports(a, b)
    assert not any("Shared distinctive" in m for m in result["matched_attributes"])


def test_matching_tolerates_non_string_fields():
    a = _rep(location=123, description=None)
    b = _rep(location=None, description=["x"])
    result = MatchingEngine.compare_reports(a, b)
    assert 0 <= result["score"] <= 100


def test_health_reports_database_status(client):
    body = client.get("/api/health").get_json()
    assert body["database"]["status"] in ("healthy", "degraded")
