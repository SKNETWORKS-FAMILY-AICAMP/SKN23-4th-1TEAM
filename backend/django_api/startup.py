import threading

_startup_lock = threading.Lock()
_initialized = False


def initialize_backend() -> None:
    global _initialized
    if _initialized:
        return

    with _startup_lock:
        if _initialized:
            return

        from backend.db.base import Base
        from backend.db.database import init_db
        from backend.db.schema_patch import patch_user_table_columns
        from backend.db.session import engine

        Base.metadata.create_all(bind=engine)
        init_db()
        patch_user_table_columns()
        _initialized = True
