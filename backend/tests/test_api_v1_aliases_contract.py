from app.main import app


def test_api_v1_aliases_are_exposed_in_openapi():
    paths = app.openapi()["paths"]

    assert "/api/v1/categories" in paths
    assert "/api/v1/reports/summary" in paths
    assert "/api/v1/reports/daily" in paths
    assert "/api/v1/reports/context" in paths
    assert "/api/v1/reports/top-categories" in paths
    assert "/api/v1/reports/ai-consult/pdf" in paths
