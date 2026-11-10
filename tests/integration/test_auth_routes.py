import pytest

def test_register_success(client):
    res = client.post("/api/auth/register", json={
        "name": "Dana Student",
        "email": "dana@campus.edu",
        "password": "danapassword123",
        "role": "student"
    })
    assert res.status_code == 201
    data = res.get_json()
    assert data["success"] is True
    assert "token" in data["data"]
    assert data["data"]["user"]["email"] == "dana@campus.edu"

def test_register_duplicate_email_rejected(client, student_user):
    res = client.post("/api/auth/register", json={
        "name": "Duplicate Alice",
        "email": "alice@test.edu",
        "password": "password123"
    })
    assert res.status_code == 400
    assert "already exists" in res.get_json()["error"]

def test_register_short_password_rejected(client):
    res = client.post("/api/auth/register", json={
        "name": "Short Pass User",
        "email": "short@campus.edu",
        "password": "123"
    })
    assert res.status_code == 400

def test_login_success(client, student_user):
    res = client.post("/api/auth/login", json={
        "email": "alice@test.edu",
        "password": "password123"
    })
    assert res.status_code == 200
    data = res.get_json()
    assert data["success"] is True
    assert "token" in data["data"]

def test_login_invalid_credentials(client, student_user):
    res = client.post("/api/auth/login", json={
        "email": "alice@test.edu",
        "password": "wrongpassword"
    })
    assert res.status_code == 401

def test_protected_me_endpoint(client, student_auth_headers):
    # With valid token
    res = client.get("/api/auth/me", headers=student_auth_headers)
    assert res.status_code == 200
    assert res.get_json()["data"]["email"] == "alice@test.edu"

    # Without token
    res_no_auth = client.get("/api/auth/me")
    assert res_no_auth.status_code == 401
