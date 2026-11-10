"""
Organizer-mandated acceptance tests (Design Report v2.0, section 12.1) plus the additional
functional tests from section 12.2. Gemini is always mocked; CI never calls the real API.
"""
import io
import json
from datetime import date, timedelta

from PIL import Image

from app.ai.gemini_client import GeminiClient
from app.repositories.db import get_db
from app.services.matching_service import MatchingEngine
from app.utils.rate_limit import reset_rate_limits


def _img(fmt="JPEG"):
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), color=(20, 20, 20)).save(buf, format=fmt)
    buf.seek(0)
    return buf


def _form(report_type="found", **over):
    data = {
        "report_type": report_type,
        "title": "Dark leather card holder",
        "description": "Dark leather card holder with a metallic logo, found near the library",
        "category": "personal_accessory",
        "location": "Main Library",
        "incident_date": "2026-11-08",
        "image": (_img(), "item.jpg"),
    }
    data.update(over)
    return data


def _post_report(client, headers, **over):
    return client.post("/api/reports", data=_form(**over), headers=headers, content_type="multipart/form-data")


def _make(client, headers, **over):
    res = _post_report(client, headers, **over)
    assert res.status_code == 201, res.get_json()
    return res.get_json()["data"]


# ---------------------------------------------------------------- AI review / fallback

def test_analyze_returns_editable_suggestions_without_saving(app, client, student_auth_headers, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    res = client.post("/api/reports/analyze", data={
        "title": "Black leather wallet", "description": "Black leather wallet with silver logo",
        "category": "personal_accessory", "image": (_img(), "w.jpg"),
    }, headers=student_auth_headers, content_type="multipart/form-data")
    assert res.status_code == 200
    payload = res.get_json()["data"]
    assert payload["ai_status"] == "manual"
    assert "black" in payload["suggestion"]["attributes"]["color"]
    assert payload["analysis_id"]
    with app.app_context():
        assert get_db().reports.count_documents({}) == 0  # nothing saved


def test_confirmed_attributes_are_saved_and_analysis_linked(app, client, student_auth_headers, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    analysis = client.post("/api/reports/analyze", data={
        "title": "Black leather wallet", "description": "Black leather wallet",
        "category": "personal_accessory", "image": (_img(), "w.jpg"),
    }, headers=student_auth_headers, content_type="multipart/form-data").get_json()["data"]

    confirmed = {"object_type": "wallet", "color": ["navy"], "material": ["leather"],
                 "shape": [], "brand_or_logo": [], "distinctive_features": ["red stitching"]}
    report = _make(client, student_auth_headers, report_type="lost",
                   confirmed_attributes=json.dumps(confirmed), analysis_id=analysis["analysis_id"])
    assert report["attribute_source"] == "user_confirmed"
    assert report["attributes"]["color"] == ["dark_blue"]  # normalized user edit
    assert report["ai_status"] == "manual"
    with app.app_context():
        log = get_db().ai_logs.find_one({"report_id": report["id"]})
        assert log is not None

    # The same analysis cannot be reused to label a second report
    again = _make(client, student_auth_headers, report_type="lost",
                  confirmed_attributes=json.dumps(confirmed), analysis_id=analysis["analysis_id"])
    assert again["ai_status"] == "manual"


def test_ai_failure_fallback_report_still_posts_and_matches(client, student_auth_headers, finder_auth_headers, monkeypatch):
    """Spec: force Gemini failure -> report posts, ai_status failed, matching still runs."""
    monkeypatch.setenv("GEMINI_API_KEY", "fake-key-for-test")

    def boom(self, description, image_path):
        raise TimeoutError("simulated Gemini timeout")
    monkeypatch.setattr(GeminiClient, "extract_item_attributes", boom)

    lost = _make(client, student_auth_headers, report_type="lost", title="Black leather wallet",
                 description="Black leather wallet lost in library")
    assert lost["ai_status"] == "failed"
    assert lost["attribute_source"] == "rule_based_fallback"
    _make(client, finder_auth_headers, title="Black leather wallet found",
          description="Black leather wallet found in library")
    m = client.get(f"/api/matches/{lost['id']}", headers=student_auth_headers)
    assert m.status_code == 200 and m.get_json()["count"] == 1


# ---------------------------------------------------------------- bad inputs

def test_no_photo_returns_photo_required_and_creates_nothing(app, client, student_auth_headers):
    data = _form(); data.pop("image")
    res = client.post("/api/reports", data=data, headers=student_auth_headers, content_type="multipart/form-data")
    assert res.status_code == 400 and res.get_json()["code"] == "PHOTO_REQUIRED"
    with app.app_context():
        assert get_db().reports.count_documents({}) == 0


def test_huge_image_returns_413(client, student_auth_headers):
    big = io.BytesIO(b"\xff\xd8\xff" + b"0" * (7 * 1024 * 1024))
    res = _post_report(client, student_auth_headers, image=(big, "big.jpg"))
    assert res.status_code == 413


def test_renamed_text_file_returns_415(client, student_auth_headers):
    res = _post_report(client, student_auth_headers, image=(io.BytesIO(b"MZ fake exe"), "photo.jpg"))
    assert res.status_code == 415


def test_wrong_real_format_returns_415(client, student_auth_headers):
    res = _post_report(client, student_auth_headers, image=(_img("GIF"), "photo.png"))
    assert res.status_code == 415
    assert res.get_json()["code"] == "UNSUPPORTED_MEDIA_TYPE"


def test_empty_fields_return_400(client, student_auth_headers):
    for field in ("title", "description", "category", "location", "incident_date"):
        res = _post_report(client, student_auth_headers, **{field: ""})
        assert res.status_code == 400, field


def test_future_and_implausible_dates_rejected(client, student_auth_headers):
    future = (date.today() + timedelta(days=10)).isoformat()
    assert _post_report(client, student_auth_headers, incident_date=future).status_code == 400
    assert _post_report(client, student_auth_headers, incident_date="1999-01-01").status_code == 400
    assert _post_report(client, student_auth_headers, incident_date="08/11/2026").status_code == 400


# ---------------------------------------------------------------- matching

def test_known_match_ranks_first_and_is_deterministic(app):
    from scripts.seed_database import seed
    with app.app_context():
        assert seed(app=app, force=True)
        lost_wallet = get_db().reports.find_one({"title": "Black Leather Bifold Wallet"})
        rid = str(lost_wallet["_id"])
        run1 = MatchingEngine.find_matches_for_report(rid)
        run2 = MatchingEngine.find_matches_for_report(rid)
    assert run1[0]["candidate_report"]["title"] == "Found Black Leather Wallet"
    assert run1[0]["score"] > run1[1]["score"]
    strip = lambda rs: [(r["found_report_id"], r["score"], r["matched_attributes"], r["conflicts"], r["unknowns"]) for r in rs]
    assert strip(run1) == strip(run2)
    assert run1[0]["algorithm_version"] and run1[0]["config_version"]


def test_wallet_card_holder_and_colour_family_compatibility():
    lost = {"category": "personal_accessory", "object_type": "wallet", "location": "Library",
            "incident_date": "2026-11-08", "attributes": {"color": ["navy"], "material": ["leather"]}}
    found = {"category": "personal_accessory", "object_type": "card holder", "location": "Library",
             "incident_date": "2026-11-08", "attributes": {"color": ["blue"], "material": ["leather"]}}
    bottle = {"category": "bottle_container", "object_type": "water bottle", "location": "Gym",
              "incident_date": "2026-11-08", "attributes": {"color": ["red"], "material": ["plastic"]}}
    good = MatchingEngine.compare_reports(lost, found)
    bad = MatchingEngine.compare_reports(lost, bottle)
    assert any("Compatible object types" in m for m in good["matched_attributes"])
    assert any("colour family" in m for m in good["matched_attributes"])
    assert good["score"] > bad["score"]


def test_no_self_match_or_same_type_or_own_reports(client, student_auth_headers, finder_auth_headers):
    lost = _make(client, student_auth_headers, report_type="lost")
    _make(client, student_auth_headers, report_type="lost")       # same type: never compared
    _make(client, student_auth_headers, report_type="found")      # same owner: never compared
    _make(client, finder_auth_headers, report_type="found")       # valid candidate
    data = client.get(f"/api/matches/{lost['id']}", headers=student_auth_headers).get_json()["data"]
    assert len(data) == 1
    assert data[0]["candidate_report"]["report_type"] == "found"


def test_resolved_item_absent_from_search_and_matching(client, student_auth_headers, finder_auth_headers):
    lost = _make(client, student_auth_headers, report_type="lost")
    found = _make(client, finder_auth_headers)
    client.patch(f"/api/reports/{found['id']}", json={"status": "resolved"}, headers=finder_auth_headers)
    listing = client.get("/api/reports?report_type=found").get_json()["data"]["items"]
    assert all(r["id"] != found["id"] for r in listing)
    matches = client.get(f"/api/matches/{lost['id']}", headers=student_auth_headers).get_json()["data"]
    assert all(m["candidate_report"]["id"] != found["id"] for m in matches)


# ---------------------------------------------------------------- claim verification

def test_private_clue_never_leaks(client, student_auth_headers, finder_auth_headers):
    clue = "blue metro pass behind card"
    found = _make(client, finder_auth_headers, verification_clue=clue)
    lost = _make(client, student_auth_headers, report_type="lost")
    bodies = [
        client.get(f"/api/reports/{found['id']}").get_data(as_text=True),
        client.get(f"/api/reports/{found['id']}", headers=finder_auth_headers).get_data(as_text=True),
        client.get("/api/reports?report_type=found").get_data(as_text=True),
        client.get(f"/api/matches/{lost['id']}", headers=student_auth_headers).get_data(as_text=True),
    ]
    assert all("metro pass" not in b for b in bodies)
    owner_view = client.get(f"/api/reports/{found['id']}", headers=finder_auth_headers).get_json()["data"]
    assert owner_view["has_private_clue"] is True


def test_wrong_answers_increment_and_lock(client, student_auth_headers, finder_auth_headers):
    found = _make(client, finder_auth_headers, verification_clue="blue metro pass behind card")
    wrong = {"report_id": found["id"], "verification_answers": "It is just a normal black wallet"}
    r1 = client.post("/api/claims", json=wrong, headers=student_auth_headers)
    assert r1.status_code == 400 and "2 attempt(s) remaining" in r1.get_json()["error"]
    assert "metro" not in r1.get_json()["error"]  # generic failure message
    r2 = client.post("/api/claims", json=wrong, headers=student_auth_headers)
    assert r2.status_code == 400 and "1 attempt(s) remaining" in r2.get_json()["error"]
    r3 = client.post("/api/claims", json=wrong, headers=student_auth_headers)
    assert r3.status_code == 429
    # Even the correct answer is refused once locked (no bypass by replay)
    right = {"report_id": found["id"], "verification_answers": "There is a blue metro pass behind my card"}
    assert client.post("/api/claims", json=right, headers=student_auth_headers).status_code == 429


def test_failed_claims_hidden_from_finder_and_not_approvable(client, student_auth_headers, finder_auth_headers):
    found = _make(client, finder_auth_headers, verification_clue="blue metro pass behind card")
    client.post("/api/claims", json={"report_id": found["id"], "verification_answers": "Totally wrong answer here"},
                headers=student_auth_headers)
    review = client.get("/api/claims?scope=review", headers=finder_auth_headers).get_json()["data"]
    assert review == []
    mine = client.get("/api/claims?scope=mine", headers=student_auth_headers).get_json()["data"]
    assert mine[0]["verification_status"] == "failed"
    res = client.patch(f"/api/claims/{mine[0]['id']}", json={"action": "approved"}, headers=finder_auth_headers)
    assert res.status_code == 409


def test_correct_answer_verified_then_finder_approves(client, student_auth_headers, finder_auth_headers):
    found = _make(client, finder_auth_headers, verification_clue="blue metro pass behind card")
    res = client.post("/api/claims", json={
        "report_id": found["id"], "verification_answers": "My blue metro pass is tucked behind the student card"
    }, headers=student_auth_headers)
    assert res.status_code == 201
    claim = res.get_json()["data"]
    assert claim["verification_status"] == "verified"
    review = client.get("/api/claims?scope=review", headers=finder_auth_headers).get_json()["data"]
    assert [c["id"] for c in review] == [claim["id"]]
    assert client.patch(f"/api/claims/{claim['id']}", json={"action": "approved"},
                        headers=finder_auth_headers).status_code == 200


def test_pending_claim_does_not_resolve_item(client, student_auth_headers, finder_auth_headers):
    found = _make(client, finder_auth_headers)
    client.post("/api/claims", json={"report_id": found["id"], "verification_answers": "Details about my item"},
                headers=student_auth_headers)
    status = client.get(f"/api/reports/{found['id']}").get_json()["data"]["status"]
    assert status == "claim_pending"


# ---------------------------------------------------------------- contact access

def test_contact_access_matrix(client, student_auth_headers, finder_auth_headers, admin_auth_headers):
    found = _make(client, finder_auth_headers)
    url = f"/api/reports/{found['id']}/contact"
    # Outsider (admin is used here as an unrelated user; there is no admin bypass)
    assert client.get(url, headers=admin_auth_headers).status_code == 403
    # Finder: allowed for own found report
    assert client.get(url, headers=finder_auth_headers).status_code == 200
    # Unapproved claimant
    claim = client.post("/api/claims", json={"report_id": found["id"], "verification_answers": "Details about my item"},
                        headers=student_auth_headers).get_json()["data"]
    assert client.get(url, headers=student_auth_headers).status_code == 403
    # Approved claimant
    client.patch(f"/api/claims/{claim['id']}", json={"action": "approved"}, headers=finder_auth_headers)
    res = client.get(url, headers=student_auth_headers)
    assert res.status_code == 200
    assert res.get_json()["data"]["finder"]["email"] == "bob@test.edu"
    # Contact data never appears in public endpoints
    assert "bob@test.edu" not in client.get(f"/api/reports/{found['id']}").get_data(as_text=True)
    assert "bob@test.edu" not in client.get("/api/reports").get_data(as_text=True)


def test_only_finder_or_admin_decides(client, student_auth_headers, finder_auth_headers, app):
    found = _make(client, finder_auth_headers)
    claim = client.post("/api/claims", json={"report_id": found["id"], "verification_answers": "Details about my item"},
                        headers=student_auth_headers).get_json()["data"]
    # A third, unrelated student cannot decide
    client.post("/api/auth/register", json={"name": "Mallory", "email": "mal@x.edu", "password": "secret12"})
    tok = client.post("/api/auth/login", json={"email": "mal@x.edu", "password": "secret12"}).get_json()["data"]["token"]
    res = client.patch(f"/api/claims/{claim['id']}", json={"action": "approved"},
                       headers={"Authorization": f"Bearer {tok}"})
    assert res.status_code == 403


# ---------------------------------------------------------------- auth extras

def test_duplicate_email_rejected_and_password_hashed(app, client):
    body = {"name": "Dup User", "email": "dup@x.edu", "password": "secret12"}
    assert client.post("/api/auth/register", json=body).status_code == 201
    assert client.post("/api/auth/register", json={**body, "email": "DUP@x.edu"}).status_code == 400
    with app.app_context():
        user = get_db().users.find_one({"email": "dup@x.edu"})
        assert user["password_hash"] != "secret12" and user["password_hash"].startswith("$2")


def test_login_rate_limited(app, client):
    app.config["RATE_LIMIT_ENABLED"] = True
    reset_rate_limits()
    try:
        codes = [client.post("/api/auth/login", json={"email": "x@y.edu", "password": "bad"}).status_code
                 for _ in range(12)]
        assert codes[0] == 401 and codes[-1] == 429
    finally:
        app.config["RATE_LIMIT_ENABLED"] = False
        reset_rate_limits()


def test_api_404_is_json(client):
    res = client.get("/api/does-not-exist")
    assert res.status_code == 404
    assert res.get_json()["success"] is False
