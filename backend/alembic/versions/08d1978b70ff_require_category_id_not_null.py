"""require category_id not null"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "08d1978b70ff"
down_revision: Union[str, Sequence[str], None] = "144db2fbc5f9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.alter_column(
            "category_id",
            existing_type=sa.Integer(),
            nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.alter_column(
            "category_id",
            existing_type=sa.Integer(),
            nullable=True,
        )
