import random


def _create_category(client, auth_header, name: str):
    resp = client.post(
        "/categories",
        json={"name": name},
        headers=auth_header,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _create_transaction(
    client,
    auth_header,
    company_id: int,
    category_id: int,
    occurred_at: str,
):
    resp = client.post(
        "/transactions",
        json={
            "company_id": company_id,
            "category_id": category_id,
            "kind": "in",
            "amount_cents": 150000,
            "description": "receita teste ai consult",
            "occurred_at": occurred_at,
        },
        headers=auth_header,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()


def test_ai_consult_respects_period(client, auth_header):
    random_digits = "".join(str(random.randint(0, 9)) for _ in range(8))
    cnpj = f"12345678{random_digits}"[:14]

    r_company = client.post(
        "/companies",
        json={
            "cnpj": cnpj,
            "razao_social": f"Empresa Teste {random_digits}",
        },
        headers=auth_header,
    )
    assert r_company.status_code == 201, r_company.text
    company_id = r_company.json()["id"]

    category_name = f"Receita Teste AI {random_digits}"
    category_id = _create_category(client, auth_header, category_name)

    _create_transaction(
        client,
        auth_header,
        company_id=company_id,
        category_id=category_id,
        occurred_at="2000-01-01T12:00:00",
    )

    payload = {
        "company_id": company_id,
        "period": {
            "start": "1999-12-31",
            "end": "2000-01-01",
        },
    }

    r = client.post("/ai/consult", json=payload, headers=auth_header)
    assert r.status_code == 200, r.text

    data = r.json()

    assert data["period"]["start"] == "1999-12-31"
    assert data["period"]["end"] == "2000-01-01"

    recent_transactions = data["recent_transactions"]
    assert isinstance(recent_transactions, list)
    assert len(recent_transactions) >= 1

    assert any(
        tx["category_id"] == category_id and tx["category_name"] == category_name
        for tx in recent_transactions
    ), data["recent_transactions"]
