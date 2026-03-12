from app.main import app


def test_auth_api_v1_aliases_are_exposed_in_openapi():
    paths = app.openapi()["paths"]

    assert "/auth/login" in paths
    assert "/auth/me" in paths
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/me" in paths
