from sqlalchemy import text

from backend.db.session import engine


USER_COLUMN_PATCHES = {
    "name": "ALTER TABLE users ADD COLUMN name VARCHAR(100) NULL",
    "profile_image_url": "ALTER TABLE users ADD COLUMN profile_image_url VARCHAR(512) NULL",
    "provider": "ALTER TABLE users ADD COLUMN provider VARCHAR(20) NULL",
    "provider_user_id": "ALTER TABLE users ADD COLUMN provider_user_id VARCHAR(128) NULL",
    "role": "ALTER TABLE users ADD COLUMN role VARCHAR(20) NOT NULL DEFAULT 'user'",
    "tier": "ALTER TABLE users ADD COLUMN tier VARCHAR(20) NOT NULL DEFAULT 'normal'",
    "status": "ALTER TABLE users ADD COLUMN status VARCHAR(20) NOT NULL DEFAULT 'active'",
}


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    query = text(
        """
        SELECT COUNT(*)
        FROM information_schema.columns
        WHERE table_schema = DATABASE()
          AND table_name = :table_name
          AND column_name = :column_name
        """
    )
    return bool(
        conn.execute(
            query,
            {"table_name": table_name, "column_name": column_name},
        ).scalar()
    )


def patch_user_table_columns() -> None:
    with engine.begin() as conn:
        for column_name, alter_sql in USER_COLUMN_PATCHES.items():
            if _column_exists(conn, "users", column_name):
                continue
            conn.execute(text(alter_sql))
