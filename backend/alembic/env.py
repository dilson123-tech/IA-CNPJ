from pathlib import Path
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context
from app.core.settings import settings
from app.db import Base
from app.models.company import Company  # noqa: F401
from app.models.transaction import Transaction  # noqa: F401
from app.models.category import Category  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# --- IA-CNPJ: garante Alembic usando o MESMO DATABASE_URL do app (CI-safe) ---
def _normalize_sqlite_url(url: str) -> str:
    if not url.startswith("sqlite"):
        return url
    # sqlite:///./foo.db -> absoluto baseado em backend/
    if url.startswith("sqlite:///./"):
        rel = url[len("sqlite:///./"):]
        base = Path(__file__).resolve().parents[1]  # backend/
        abs_path = (base / rel).resolve()
        return "sqlite:////" + abs_path.as_posix().lstrip("/")
    # sqlite:///abs/path.db -> garante 4 slashes
    if url.startswith("sqlite:///") and not url.startswith("sqlite:////"):
        path = url[len("sqlite:///"):]
        if path.startswith("/"):
            return "sqlite:////" + path.lstrip("/")
    return url

config.set_main_option("sqlalchemy.url", _normalize_sqlite_url(settings.DATABASE_URL))
# --- end ---


# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
