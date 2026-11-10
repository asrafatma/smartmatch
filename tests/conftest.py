import os
import io
import pytest
from PIL import Image
from app import create_app
from app.config import TestingConfig
from app.repositories.db import get_db
from app.repositories.user_repository import UserRepository
from app.utils.security import hash_password

@pytest.fixture(scope="session")
def app():
    os.environ["FLASK_ENV"] = "testing"
    os.environ["TESTING"] = "true"
    os.environ["MONGODB_URI"] = "mock"
    os.environ["UPLOAD_FOLDER"] = "uploads"
    
    app = create_app(TestingConfig)
    return app

@pytest.fixture(autouse=True)
def clean_db(app):
    with app.app_context():
        db = get_db()
        db.users.delete_many({})
        db.reports.delete_many({})
        db.matches.delete_many({})
        db.claims.delete_many({})
        db.ai_logs.delete_many({})
        yield

@pytest.fixture
def client(app):
    return app.test_client()

def make_test_image():
    buf = io.BytesIO()
    img = Image.new("RGB", (100, 100), color=(50, 100, 150))
    img.save(buf, format="JPEG")
    buf.seek(0)
    return buf

@pytest.fixture
def image_factory():
    return make_test_image

@pytest.fixture
def sample_image_bytes():
    return make_test_image()

@pytest.fixture
def student_user(app):
    with app.app_context():
        return UserRepository.create(
            name="Alice Student",
            email="alice@test.edu",
            password_hash=hash_password("password123"),
            role="student"
        )

@pytest.fixture
def finder_user(app):
    with app.app_context():
        return UserRepository.create(
            name="Bob Finder",
            email="bob@test.edu",
            password_hash=hash_password("password123"),
            role="student"
        )

@pytest.fixture
def admin_user(app):
    with app.app_context():
        return UserRepository.create(
            name="Charlie Admin",
            email="admin@test.edu",
            password_hash=hash_password("adminpass123"),
            role="admin"
        )

@pytest.fixture
def student_auth_headers(client, student_user):
    res = client.post("/api/auth/login", json={
        "email": "alice@test.edu",
        "password": "password123"
    })
    token = res.get_json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def finder_auth_headers(client, finder_user):
    res = client.post("/api/auth/login", json={
        "email": "bob@test.edu",
        "password": "password123"
    })
    token = res.get_json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def admin_auth_headers(client, admin_user):
    res = client.post("/api/auth/login", json={
        "email": "admin@test.edu",
        "password": "adminpass123"
    })
    token = res.get_json()["data"]["token"]
    return {"Authorization": f"Bearer {token}"}
