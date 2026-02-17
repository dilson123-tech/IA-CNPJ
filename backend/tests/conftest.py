import pytest

# Garante que o banco de testes tenha as tabelas (CI usa sqlite em /tmp).
# Não fazemos drop_all para evitar risco de apagar DB de dev local.
@pytest.fixture(scope="session", autouse=True)
def _ensure_tables_exist():
    from app.db import Base
    from app.db import engine
    Base.metadata.create_all(bind=engine)
    yield
