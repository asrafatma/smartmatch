import io
import pytest

def test_report_submission_mandatory_photo(client, student_auth_headers):
    # Missing photograph must be rejected
    res = client.post(
        "/api/reports",
        data={
            "report_type": "lost",
            "title": "Lost Wallet",
            "description": "Lost my black wallet in library",
            "category": "personal_accessory",
            "location": "Library",
            "incident_date": "2026-11-08"
        },
        headers=student_auth_headers,
        content_type="multipart/form-data"
    )
    assert res.status_code == 400
    assert "photograph is mandatory" in res.get_json()["error"].lower()

def test_report_submission_invalid_file_type(client, student_auth_headers):
    fake_txt = io.BytesIO(b"not an image file")
    res = client.post(
        "/api/reports",
        data={
            "report_type": "lost",
            "title": "Lost Wallet",
            "description": "Lost my black wallet in library",
            "category": "personal_accessory",
            "location": "Library",
            "incident_date": "2026-11-08",
            "image": (fake_txt, "notes.txt")
        },
        headers=student_auth_headers,
        content_type="multipart/form-data"
    )
    assert res.status_code == 400
    assert "unsupported file type" in res.get_json()["error"].lower()

def test_report_submission_success_with_photo(client, student_auth_headers, sample_image_bytes):
    res = client.post(
        "/api/reports",
        data={
            "report_type": "lost",
            "title": "Lost Leather Wallet",
            "description": "Lost my black bifold wallet in library",
            "category": "personal_accessory",
            "location": "Main Library",
            "incident_date": "2026-11-08",
            "image": (sample_image_bytes, "wallet.jpg")
        },
        headers=student_auth_headers,
        content_type="multipart/form-data"
    )
    assert res.status_code == 201
    data = res.get_json()["data"]
    assert data["title"] == "Lost Leather Wallet"
    assert data["report_type"] == "lost"
    assert data["status"] == "active"
    assert data["image_path"].startswith("/uploads/")

def test_public_report_masks_private_contact_info(client, student_auth_headers, sample_image_bytes):
    # Create report as Alice
    create_res = client.post(
        "/api/reports",
        data={
            "report_type": "lost",
            "title": "Private Contact Test Item",
            "description": "Testing privacy masking of submitter email",
            "category": "stationery",
            "location": "Hall A",
            "incident_date": "2026-11-08",
            "image": (sample_image_bytes, "item.jpg")
        },
        headers=student_auth_headers,
        content_type="multipart/form-data"
    )
    report_id = create_res.get_json()["data"]["id"]

    # Public unauthenticated request
    pub_res = client.get(f"/api/reports/{report_id}")
    assert pub_res.status_code == 200
    pub_data = pub_res.get_json()["data"]
    assert "alice@test.edu" not in pub_data["submitter_email"]
    assert "PROTECTED" in pub_data["submitter_email"]

def test_unauthorized_report_update(client, student_auth_headers, finder_auth_headers, sample_image_bytes):
    # Alice creates a report
    create_res = client.post(
        "/api/reports",
        data={
            "report_type": "lost",
            "title": "Alice Notebook",
            "description": "Notebook in chemistry lab",
            "category": "stationery",
            "location": "Lab",
            "incident_date": "2026-11-08",
            "image": (sample_image_bytes, "book.jpg")
        },
        headers=student_auth_headers,
        content_type="multipart/form-data"
    )
    report_id = create_res.get_json()["data"]["id"]

    # Bob attempts to update Alice's report
    update_res = client.patch(
        f"/api/reports/{report_id}",
        json={"title": "Hacked Title"},
        headers=finder_auth_headers
    )
    assert update_res.status_code == 403
