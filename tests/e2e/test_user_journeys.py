import pytest

def test_complete_lost_to_handover_journey(client, image_factory):
    # Step 1: Alice registers as student
    reg_alice = client.post("/api/auth/register", json={
        "name": "Alice Wang",
        "email": "alice.wang@campus.edu",
        "password": "securepass123",
        "role": "student"
    })
    assert reg_alice.status_code == 201
    alice_token = reg_alice.get_json()["data"]["token"]
    alice_headers = {"Authorization": f"Bearer {alice_token}"}

    # Step 2: Bob registers as finder
    reg_bob = client.post("/api/auth/register", json={
        "name": "Bob Miller",
        "email": "bob.miller@campus.edu",
        "password": "securepass123",
        "role": "student"
    })
    assert reg_bob.status_code == 201
    bob_token = reg_bob.get_json()["data"]["token"]
    bob_headers = {"Authorization": f"Bearer {bob_token}"}

    # Step 3: Alice submits Lost Wallet report
    lost_res = client.post(
        "/api/reports",
        data={
            "report_type": "lost",
            "title": "Black Leather Wallet",
            "description": "Lost folded black leather wallet near Library study carrel with silver badge",
            "category": "personal_accessory",
            "location": "Main Library",
            "incident_date": "2026-11-09",
            "image": (image_factory(), "lost_wallet.jpg")
        },
        headers=alice_headers,
        content_type="multipart/form-data"
    )
    assert lost_res.status_code == 201
    lost_id = lost_res.get_json()["data"]["id"]

    # Step 4: Bob submits Found Wallet report
    found_res = client.post(
        "/api/reports",
        data={
            "report_type": "found",
            "title": "Found Black Bifold Wallet",
            "description": "Found a black leather wallet near Main Library study area with silver badge",
            "category": "personal_accessory",
            "location": "Main Library",
            "incident_date": "2026-11-09",
            "image": (image_factory(), "found_wallet.jpg")
        },
        headers=bob_headers,
        content_type="multipart/form-data"
    )
    assert found_res.status_code == 201
    found_id = found_res.get_json()["data"]["id"]

    # Step 5: Deterministic Matching Engine runs
    match_res = client.get(f"/api/matches/{lost_id}")
    assert match_res.status_code == 200
    matches = match_res.get_json()["data"]
    assert len(matches) > 0
    top_match = matches[0]
    assert top_match["candidate_report"]["id"] == found_id
    assert top_match["score"] >= 70
    assert top_match["label"] == "Strong candidate"

    # Step 6: Alice submits an ownership claim against Bob's found report
    claim_res = client.post(
        "/api/claims",
        json={
            "report_id": found_id,
            "verification_answers": "Inside there is a student ID for Alice Wang and a gym locker card #402."
        },
        headers=alice_headers
    )
    assert claim_res.status_code == 201
    claim_id = claim_res.get_json()["data"]["id"]

    # Step 7: Bob checks pending claims
    pending_res = client.get("/api/claims?scope=review", headers=bob_headers)
    assert pending_res.status_code == 200
    claims_to_review = pending_res.get_json()["data"]
    assert any(c["id"] == claim_id for c in claims_to_review)

    # Step 8: Bob verifies and approves claim
    review_res = client.patch(
        f"/api/claims/{claim_id}",
        json={"action": "approved", "notes": "Alice Wang name verified on internal ID"},
        headers=bob_headers
    )
    assert review_res.status_code == 200
    assert review_res.get_json()["data"]["status"] == "approved"

    # Step 9: Handover contact information is unlocked
    contact_res = client.get(f"/api/reports/{found_id}/contact", headers=alice_headers)
    assert contact_res.status_code == 200
    contact_info = contact_res.get_json()["data"]
    assert contact_info["claim_status"] == "approved"
    assert contact_info["finder"]["email"] == "bob.miller@campus.edu"
    assert contact_info["claimant"]["email"] == "alice.wang@campus.edu"

def test_resolved_reports_excluded_from_matching(client, image_factory, student_auth_headers, finder_auth_headers):
    # Create Lost Item
    lost_res = client.post(
        "/api/reports",
        data={
            "report_type": "lost",
            "title": "Lost Silver Keys",
            "description": "Lost set of silver keys",
            "category": "key_id",
            "location": "Quad",
            "incident_date": "2026-11-09",
            "image": (image_factory(), "keys.jpg")
        },
        headers=student_auth_headers,
        content_type="multipart/form-data"
    )
    lost_id = lost_res.get_json()["data"]["id"]

    # Create Found Item
    found_res = client.post(
        "/api/reports",
        data={
            "report_type": "found",
            "title": "Found Silver Keys",
            "description": "Found set of silver keys on Quad",
            "category": "key_id",
            "location": "Quad",
            "incident_date": "2026-11-09",
            "image": (image_factory(), "found_keys.jpg")
        },
        headers=finder_auth_headers,
        content_type="multipart/form-data"
    )
    found_id = found_res.get_json()["data"]["id"]

    # Before resolving: found item appears in matches
    m1 = client.get(f"/api/matches/{lost_id}").get_json()["data"]
    assert any(m["candidate_report"]["id"] == found_id for m in m1)

    # Now mark found item as resolved
    client.patch(f"/api/reports/{found_id}", json={"status": "resolved"}, headers=finder_auth_headers)

    # After resolving: resolved found item must NOT appear in active matches
    m2 = client.get(f"/api/matches/{lost_id}").get_json()["data"]
    assert not any(m["candidate_report"]["id"] == found_id for m in m2)
