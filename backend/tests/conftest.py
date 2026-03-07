import os

import pytest


def _truthy(v) -> bool:
    return str(v or "").strip().lower() in {"1", "true", "yes", "y", "on"}


def _redact_url(url: str) -> str:
    # Redação simples de credenciais: postgres://user:pass@host/db -> postgres://user:***@host/db
    try:
        if "://" not in url or "@" not in url:
            return url
        scheme, rest = url.split("://", 1)
        creds, host = rest.split("@", 1)
        if ":" in creds:
            user, _ = creds.split(":", 1)
            creds = f"{user}:***"
        return f"{scheme}://{creds}@{host}"
    except Exception:
        return "<unable to redact url>"


def _detect_db_url() -> str:
    return (os.getenv("IA_CNPJ_DATABASE_URL") or os.getenv("DATABASE_URL") or "").strip()


def _looks_like_postgres(url: str) -> bool:
    u = url.lower()
    return u.startswith("postgres://") or u.startswith("postgresql://") or u.startswith("postgresql+")


def _block_postgres(url_hint: str) -> None:
    redacted = _redact_url(url_hint) if url_hint else "<not set>"
    raise pytest.UsageError(
        "\n"
        "🛑 Tests blocked: detected Postgres configuration.\n"
        f"    DATABASE_URL/IA_CNPJ_DATABASE_URL = {redacted}\n\n"
        "Default policy (IA-CNPJ): tests rodam CI-like em SQLite (/tmp) por segurança e determinismo.\n"
        "Use:\n"
        "    cd backend && ./test_ci.sh\n\n"
        "Se você REALMENTE quer rodar testes em Postgres local (RLS), habilite explicitamente:\n"
        "    export IA_CNPJ_ALLOW_PG_TESTS=true\n\n"
        "Dica: se foi sem querer, limpe o ambiente:\n"
        "    unset DATABASE_URL IA_CNPJ_DATABASE_URL\n"
    )


# Guard EARLY (antes de importar app.db / engine)
_url = _detect_db_url()
if _looks_like_postgres(_url) and not _truthy(os.getenv("IA_CNPJ_ALLOW_PG_TESTS")):
    _block_postgres(_url)


from fastapi.testclient import TestClient  # noqa: E402
from app.db import Base, engine  # noqa: E402
from app.main import app  # noqa: E402


# Guard fallback (caso engine já esteja em Postgres por outro caminho)
dialect = getattr(getattr(engine, "dialect", None), "name", None)
if dialect in {"postgresql", "postgres"} and not _truthy(os.getenv("IA_CNPJ_ALLOW_PG_TESTS")):
    try:
        url2 = engine.url.render_as_string(hide_password=True)
    except Exception:
        url2 = "<unable to render engine url>"
    _block_postgres(url2)


@pytest.fixture
def client():
    Base.metadata.create_all(bind=engine)
    return TestClient(app)


@pytest.fixture
def auth_header(client):
    r = client.post(
        "/auth/login",
        json={"username": "userA@teste.com", "password": "dev"},
    )
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}
