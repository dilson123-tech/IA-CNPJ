import random


def _create_company(client, auth_header):
    random_digits = "".join(str(random.randint(0, 9)) for _ in range(8))
    cnpj = f"12345678{random_digits}"[:14]

    resp = client.post(
        "/companies",
        json={
            "cnpj": cnpj,
            "razao_social": f"Empresa Tx Kind {random_digits}",
        },
        headers=auth_header,
    )
    assert resp.status_code == 201, resp.text
    return resp.json()["id"]


def _create_category(client, auth_header):
    random_digits = "".join(str(random.randint(0, 9)) for _ in range(6))

    resp = client.post(
        "/categories",
        json={"name": f"Categoria Tx {random_digits}"},
        headers=auth_header,
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def test_create_transaction_accepts_in(client, auth_header):
    company_id = _create_company(client, auth_header)
    category_id = _create_category(client, auth_header)

    resp = client.post(
        "/transactions",
        json={
            "company_id": company_id,
            "category_id": category_id,
            "kind": "in",
            "amount_cents": 150000,
            "description": "receita teste contrato kind",
        },
        headers=auth_header,
    )

    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["company_id"] == company_id
    assert data["category_id"] == category_id
    assert data["kind"] == "in"
    assert data["amount_cents"] == 150000


def test_create_transaction_rejects_income(client, auth_header):
    company_id = _create_company(client, auth_header)
    category_id = _create_category(client, auth_header)

    resp = client.post(
        "/transactions",
        json={
            "company_id": company_id,
            "category_id": category_id,
            "kind": "income",
            "amount_cents": 150000,
            "description": "receita invalida",
        },
        headers=auth_header,
    )

    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert "detail" in body
    assert any(
        err.get("loc") == ["body", "kind"] and "in' or 'out" in err.get("msg", "")
        for err in body["detail"]
    )
