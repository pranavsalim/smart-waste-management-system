import os
import tempfile
import pytest

os.environ["ADMIN_EMAIL"] = "admin@test.local"
os.environ["ADMIN_PASSWORD"] = "TestAdmin@123"

import app as app_module


@pytest.fixture()
def client(monkeypatch):
    fd, path = tempfile.mkstemp()
    os.close(fd)
    monkeypatch.setattr(app_module, "DATABASE", path)
    app_module.init_db()
    app_module.app.config.update(TESTING=True, SECRET_KEY="test-secret")
    with app_module.app.test_client() as client:
        yield client
    os.unlink(path)


def test_home_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"Cleaner streets" in response.data


def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_register_and_login(client):
    response = client.post("/register", data={
        "name": "Test Citizen",
        "email": "citizen@example.com",
        "password": "Password123"
    }, follow_redirects=True)
    assert response.status_code == 200
    response = client.post("/login", data={
        "email": "citizen@example.com",
        "password": "Password123"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"My complaints" in response.data


def test_admin_login(client):
    response = client.post("/login", data={
        "email": "admin@test.local",
        "password": "TestAdmin@123"
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Waste reports overview" in response.data
