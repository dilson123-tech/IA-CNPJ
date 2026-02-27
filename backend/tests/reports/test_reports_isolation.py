def test_reports_summary_returns_404_for_invalid_company(client, auth_header):
    # tenta acessar empresa inexistente
    r = client.get(
        "/reports/summary?company_id=999999",
        headers=auth_header,
    )

    assert r.status_code == 404
