from typing import Any

from fastapi import APIRouter, Body, Query

from backend.db.database import get_connection


router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/query")
def query_admin_data(query_type: str = Query("users")):
    if query_type == "users":
        sql = "SELECT * FROM users"
    elif query_type == "interviews":
        sql = (
            "SELECT id, user_id, total_score AS score, started_at AS created_at "
            "FROM interview_sessions ORDER BY id DESC LIMIT 10"
        )
    else:
        return []

    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                return cursor.fetchall()
    except Exception as exc:
        return [{"error": "DB Fetch Failed", "raw": str(exc), "err": str(exc)}]


@router.post("/sql")
def run_admin_sql(
    sql: str = Body(..., embed=True),
    args: list[Any] | None = Body(None, embed=True),
):
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                if args:
                    cursor.execute(sql, args)
                else:
                    cursor.execute(sql)
        return {"result": "SUCCESS"}
    except Exception as exc:
        return {"result": f"ERROR: {str(exc)}"}
