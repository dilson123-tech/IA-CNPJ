import random


def get_auth_headers(client):
    resp = client.post(
        "/auth/login",
        json={"username": "userA@teste.com", "password": "dev"},
    )
    assert resp.status_code == 200
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_company(client, headers):
    random_digits = "".join(str(random.randint(0, 9)) for _ in range(8))
    cnpj = f"12345678{random_digits}"[:14]

    payload = {
        "cnpj": cnpj,
        "razao_social": f"Empresa Teste {random_digits}",
    }

    resp = client.post("/companies", json=payload, headers=headers)
    assert resp.status_code == 201
    return resp.json()


def test_get_company_ok(client):
    headers = get_auth_headers(client)
    company = create_company(client, headers)

    resp = client.get(f"/companies/{company['id']}", headers=headers)
    assert resp.status_code == 200


def test_get_company_not_found(client):
    headers = get_auth_headers(client)
    resp = client.get("/companies/999999", headers=headers)
    assert resp.status_code == 404


def test_get_company_by_cnpj_ok(client):
    headers = get_auth_headers(client)
    company = create_company(client, headers)

    resp = client.get(f"/companies/by-cnpj/{company['cnpj']}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == company["id"]
    assert data["cnpj"] == company["cnpj"]


def test_get_company_by_cnpj_invalid(client):
    headers = get_auth_headers(client)

    resp = client.get("/companies/by-cnpj/123", headers=headers)
    assert resp.status_code == 422
    assert resp.json()["detail"] == "CNPJ inválido"


def test_get_company_by_cnpj_auto_lookup_creates_company(client, monkeypatch):
    headers = get_auth_headers(client)
    suffix = "".join(str(random.randint(0, 9)) for _ in range(8))
    cnpj = f"55{suffix}0001{random.randint(10,99)}"[:14]
    calls = {"count": 0}

    def fake_lookup(raw_cnpj: str):
        calls["count"] += 1
        normalized = "".join(ch for ch in raw_cnpj if ch.isdigit())
        return {
            "cnpj": normalized,
            "razao_social": f"Empresa Auto {suffix}",
            "situacao_cadastral": "ATIVA",
            "cnae_principal_codigo": "6201501",
            "cnae_principal_descricao": "Desenvolvimento de programas de computador sob encomenda",
            "municipio": "ITAPOA",
            "uf": "SC",
        }

    from app.services import company_lookup_service as lookup_service

    monkeypatch.setattr(lookup_service, "_lookup_company_external", fake_lookup)

    first = client.get(f"/companies/by-cnpj/{cnpj}", headers=headers)
    assert first.status_code == 200
    data_first = first.json()

    second = client.get(f"/companies/by-cnpj/{cnpj}", headers=headers)
    assert second.status_code == 200
    data_second = second.json()

    assert data_first["cnpj"] == cnpj
    assert data_first["razao_social"] == f"Empresa Auto {suffix}"
    assert data_second["id"] == data_first["id"]
    assert calls["count"] == 1
