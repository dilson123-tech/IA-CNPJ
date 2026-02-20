import random

def test_ai_consult_respects_period(client, auth_header):
    # gera CNPJ único
    random_digits = "".join(str(random.randint(0, 9)) for _ in range(8))
    cnpj = f"12345678{random_digits}"[:14]

    r_company = client.post(
        "/companies",
        json={
            "cnpj": cnpj,
            "razao_social": f"Empresa Teste {random_digits}"
        },
        headers=auth_header,
    )
    assert r_company.status_code == 201
    company_id = r_company.json()["id"]

    payload = {
        "company_id": company_id,
        "period": {
            "start": "1999-12-31",
            "end": "2000-01-01"
        }
    }

    r = client.post("/ai/consult", json=payload, headers=auth_header)
    assert r.status_code == 200

    data = r.json()

    assert data["period"]["start"] == "1999-12-31"
    assert data["period"]["end"] == "2000-01-01"
