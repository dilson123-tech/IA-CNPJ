"""seed categories (inclui Testes)

Revision ID: 144db2fbc5f9
Revises: 260112194132
Create Date: 2026-02-07 02:20:21.150895

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "144db2fbc5f9"
down_revision: Union[str, Sequence[str], None] = "260112194132"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_CATEGORIES = [
    (1, "Aluguel"),
    (2, "Combustível"),
    (3, "Compras"),
    (4, "Energia"),
    (5, "Fretes"),
    (6, "Impostos"),
    (7, "Internet"),
    (8, "Salários"),
    (9, "Vendas"),
    (10, "Água"),
    (11, "Testes"),
]


def upgrade() -> None:
    """Seed default categories with stable IDs (idempotent)."""
    conn = op.get_bind()

    categories = sa.table(
        "categories",
        sa.column("id", sa.Integer),
        sa.column("name", sa.String),
    )

    rows = [{"id": cid, "name": name} for cid, name in _CATEGORIES]
    dialect = conn.dialect.name

    if dialect == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as pg_insert
        stmt = pg_insert(categories).values(rows).on_conflict_do_nothing(index_elements=["name"])
        conn.execute(stmt)
    elif dialect in ("mysql", "mariadb"):
        stmt = sa.insert(categories).values(rows).prefix_with("IGNORE")
        conn.execute(stmt)
    else:
        # sqlite + default
        stmt = sa.insert(categories).values(rows).prefix_with("OR IGNORE")
        conn.execute(stmt)


def downgrade() -> None:
    """Best-effort rollback: remove seeded categories by ID."""
    conn = op.get_bind()
    ids = [cid for cid, _ in _CATEGORIES]
    stmt = sa.text("DELETE FROM categories WHERE id IN :ids").bindparams(sa.bindparam("ids", expanding=True))
    conn.execute(stmt, {"ids": ids})
