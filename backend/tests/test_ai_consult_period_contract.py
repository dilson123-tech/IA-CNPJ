
def test_ai_consult_respects_period(client, auth_header):
    payload = {
        "company_id": 1,
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
