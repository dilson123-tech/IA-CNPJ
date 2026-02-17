import pytest

# Garante que o banco de testes tenha as tabelas (CI usa sqlite em /tmp).
# Não fazemos drop_all para evitar risco de apagar DB de dev local.
@pytest.fixture(scope="session", autouse=True)
def _ensure_tables_exist():
    from app.db import Base
    from app.db import engine

def _import_all_models():
    """Garante que Base.metadata conhece todas as tabelas (CI depende disso)."""
    import importlib, pkgutil
    import app.models
    for m in pkgutil.iter_modules(app.models.__path__, app.models.__name__ + "."):
        importlib.import_module(m.name)

    Base.metadata.create_all(bind=engine)
    yield
