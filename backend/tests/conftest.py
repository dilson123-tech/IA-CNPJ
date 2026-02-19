from app.db import engine, Base


import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    return TestClient(app)

@pytest.fixture
def auth_header(client):
    r = client.post(
        "/auth/login",
        json={"username": "dev", "password": "dev"},
    )
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
