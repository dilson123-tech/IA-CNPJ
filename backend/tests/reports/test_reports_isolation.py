def test_reports_summary_returns_404_for_invalid_company(client, auth_header):
    # tenta acessar empresa inexistente
    r = client.get(
        "/reports/summary?company_id=999999",
        headers=auth_header,
    )

    assert r.status_code == 404


def test_api_v1_reports_summary_returns_404_for_invalid_company(client, auth_header):
    # alias versionado deve manter o mesmo contrato da rota raiz
    r = client.get(
        "/api/v1/reports/summary?company_id=999999",
        headers=auth_header,
    )

    assert r.status_code == 404
