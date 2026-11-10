import pytest

@pytest.fixture
def found_report_by_bob(client, finder_auth_headers, sample_image_bytes):
    res = client.post(
        "/api/reports",
        data={
            "report_type": "found",
            "title": "Found Silver Watch",
            "description": "Silver analog wristwatch found on lawn",
            "category": "personal_accessory",
            "location": "Central Quad",
            "incident_date": "2026-11-09",
            "image": (sample_image_bytes, "watch.jpg")
        },
        headers=finder_auth_headers,
        content_type="multipart/form-data"
    )
    return res.get_json()["data"]

def test_claim_submission_against_found_item(client, student_auth_headers, found_report_by_bob):
    rep_id = found_report_by_bob["id"]
    res = client.post(
        "/api/claims",
        json={
            "report_id": rep_id,
            "verification_answers": "The watch has my initials 'A.C.' engraved on the rear clasp."
        },
        headers=student_auth_headers
    )
    assert res.status_code == 201
    claim = res.get_json()["data"]
    assert claim["status"] == "pending"
    assert claim["attempt_count"] == 1

def test_finder_cannot_claim_own_item(client, finder_auth_headers, found_report_by_bob):
    rep_id = found_report_by_bob["id"]
    res = client.post(
        "/api/claims",
        json={
            "report_id": rep_id,
            "verification_answers": "I claim this item that I reported having found"
        },
        headers=finder_auth_headers
    )
    assert res.status_code == 400
    assert "cannot submit an ownership claim" in res.get_json()["error"]

def test_claim_attempt_limits_and_lock(client, student_auth_headers, found_report_by_bob):
    rep_id = found_report_by_bob["id"]
    
    # Attempt 1
    res1 = client.post("/api/claims", json={"report_id": rep_id, "verification_answers": "Attempt 1 details here"}, headers=student_auth_headers)
    assert res1.status_code == 201
    
    # Attempt 2
    res2 = client.post("/api/claims", json={"report_id": rep_id, "verification_answers": "Attempt 2 details here"}, headers=student_auth_headers)
    assert res2.status_code == 200
    assert res2.get_json()["data"]["attempt_count"] == 2
    
    # Attempt 3 -> locks
    res3 = client.post("/api/claims", json={"report_id": rep_id, "verification_answers": "Attempt 3 details here"}, headers=student_auth_headers)
    assert res3.status_code == 403
    assert "limit reached" in res3.get_json()["error"].lower()

def test_claim_review_and_contact_privacy_authorization(
    client,
    student_auth_headers,
    finder_auth_headers,
    admin_auth_headers,
    found_report_by_bob
):
    rep_id = found_report_by_bob["id"]

    # 1. Contact info before approval is forbidden
    pre_contact = client.get(f"/api/reports/{rep_id}/contact", headers=student_auth_headers)
    assert pre_contact.status_code == 403

    # 2. Alice submits claim
    claim_res = client.post(
        "/api/claims",
        json={"report_id": rep_id, "verification_answers": "Silver watch with blue leather strap back"},
        headers=student_auth_headers
    )
    claim_id = claim_res.get_json()["data"]["id"]

    # 3. Random unauthenticated / unauthorized user cannot review claim
    unauth_rev = client.patch(f"/api/claims/{claim_id}", json={"action": "approved"})
    assert unauth_rev.status_code == 401

    # Alice herself cannot approve her own claim
    self_rev = client.patch(f"/api/claims/{claim_id}", json={"action": "approved"}, headers=student_auth_headers)
    assert self_rev.status_code == 403

    # 4. Bob (the finder) approves the claim
    approve_res = client.patch(
        f"/api/claims/{claim_id}",
        json={"action": "approved", "notes": "Initials verified in person"},
        headers=finder_auth_headers
    )
    assert approve_res.status_code == 200
    assert approve_res.get_json()["data"]["status"] == "approved"

    # 5. Check report status changed to resolved
    rep_check = client.get(f"/api/reports/{rep_id}")
    assert rep_check.get_json()["data"]["status"] == "resolved"

    # 6. Contact info is now unlocked for Alice (claimant) and Bob (finder)
    alice_contact = client.get(f"/api/reports/{rep_id}/contact", headers=student_auth_headers)
    assert alice_contact.status_code == 200
    contact_data = alice_contact.get_json()["data"]
    assert contact_data["finder"]["email"] == "bob@test.edu"
    assert contact_data["claimant"]["email"] == "alice@test.edu"

    # 7. Contact info is also accessible by Admin
    admin_contact = client.get(f"/api/reports/{rep_id}/contact", headers=admin_auth_headers)
    assert admin_contact.status_code == 200
