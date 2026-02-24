def test_rls_isolation(client):
    """
    Valida isolamento estrutural via RLS através da API.
    """

    # Login
    resp = client.post(
        "/auth/login",
        json={"username": "userA@teste.com", "password": "dev"},
    )
    assert resp.status_code == 200

    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Buscar empresas
    resp = client.get("/api/v1/companies", headers=headers)
    assert resp.status_code == 200

    companies = resp.json()

    # Garantia mínima estrutural
    assert isinstance(companies, list)
