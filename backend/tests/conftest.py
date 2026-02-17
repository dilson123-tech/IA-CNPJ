import pytest

def _import_all_models():
    # Import explícito dos models para registrar no SQLAlchemy metadata
    # (sem isso, create_all() cria 0 tabelas e os testes quebram)
    import app.models.company  # noqa: F401
    import app.models.category  # noqa: F401
    import app.models.transaction  # noqa: F401


# Garante que o banco de testes tenha as tabelas (CI usa sqlite em /tmp).
# Não fazemos drop_all para evitar risco de apagar DB de dev local.
@pytest.fixture(scope="session", autouse=True)
def _ensure_tables_exist():
    from app.db import Base, engine

    _import_all_models()
    Base.metadata.create_all(bind=engine)
    yield
