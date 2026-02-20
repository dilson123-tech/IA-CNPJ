import random
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def get_auth_headers():
    resp = client.post(
        "/auth/login",
        json={"username": "dev", "password": "dev"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_company(headers):
    random_digits = "".join(str(random.randint(0, 9)) for _ in range(8))
    cnpj = f"12345678{random_digits}"[:14]

    payload = {
        "cnpj": cnpj,
        "razao_social": f"Empresa Teste {random_digits}",
    }

    resp = client.post("/companies", json=payload, headers=headers)
    assert resp.status_code == 201
    return resp.json()["id"]


def test_get_company_ok():
    headers = get_auth_headers()
    company_id = create_company(headers)

    resp = client.get(f"/companies/{company_id}", headers=headers)
    assert resp.status_code == 200


def test_get_company_not_found():
    headers = get_auth_headers()
    resp = client.get("/companies/999999", headers=headers)
    assert resp.status_code == 404
