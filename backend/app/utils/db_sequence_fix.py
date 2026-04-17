from sqlalchemy import text
from sqlalchemy.orm import Session


def fix_sequences(db: Session, database_url: str) -> None:
    """
    Sincroniza sequences apenas em Postgres.
    Em SQLite/lab/dev, não faz nada.
    """

    if not database_url.startswith("postgresql"):
        return

    query = text("""
    SELECT
        s.sequence_name,
        c.table_name,
        c.column_name
    FROM information_schema.sequences s
    JOIN information_schema.columns c
        ON c.column_default LIKE '%' || s.sequence_name || '%'
    WHERE c.table_schema = 'public'
    """)

    results = db.execute(query).fetchall()

    for seq_name, table_name, column_name in results:
        max_query = text(
            f"SELECT COALESCE(MAX({column_name}), 1) FROM {table_name}"
        )
        max_id = db.execute(max_query).scalar()

        setval_query = text(
            f"SELECT setval('{seq_name}', {max_id}, true)"
        )
        db.execute(setval_query)

    db.commit()
