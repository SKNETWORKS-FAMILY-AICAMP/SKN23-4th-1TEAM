from .shared import *  # noqa: F401,F403


@api_view(["GET"])
def admin_query(request):
    query_type = request.GET.get("query_type", "users")
    if query_type == "users":
        sql = "SELECT * FROM users"
    elif query_type == "interviews":
        sql = "SELECT id, user_id, total_score AS score, started_at AS created_at FROM interview_sessions ORDER BY id DESC LIMIT 10"
    else:
        return []
    try:
        with get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                return cursor.fetchall()
    except Exception as exc:
        return [{"error": "DB Fetch Failed", "raw": str(exc), "err": str(exc)}]


@api_view(["POST"])
def admin_sql(request):
    body = json_body(request)
    sql = body["sql"]
    args = body.get("args")
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
