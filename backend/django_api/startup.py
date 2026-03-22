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

        # SQLAlchemy metadata에 참조 테이블들이 모두 등록되도록
        # create_all 전에 모델 모듈을 먼저 import한다.
        from backend.models.user import User  # noqa: F401
        from backend.models.refresh_token import RefreshToken  # noqa: F401
        from backend.db.base import Base
        from backend.db.database import init_db
        from backend.db.schema_patch import patch_board_answer_columns, patch_user_table_columns
        from backend.db.session import engine

        Base.metadata.create_all(bind=engine)
        init_db()
        patch_user_table_columns()
        patch_board_answer_columns()
        _initialized = True
