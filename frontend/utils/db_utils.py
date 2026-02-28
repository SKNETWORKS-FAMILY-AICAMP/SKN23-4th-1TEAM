"""
Frontend wrappers for admin DB actions.

This module keeps the old function signatures used by admin pages,
but routes everything through FastAPI instead of opening a DB
connection from the frontend process.
"""

from utils.api_utils import api_admin_fetch, api_admin_run_sql


def get_db_connection():
    raise RuntimeError("Frontend DB connections are disabled. Use FastAPI admin APIs.")


def fetch_remote_db(ip, query_type="users"):
    success, result = api_admin_fetch(query_type=query_type)
    if success:
        return result
    return [{"error": "DB Fetch Failed", "raw": str(result), "err": str(result)}]


def run_remote_sql(ip, sql, args=None):
    success, result = api_admin_run_sql(sql=sql, args=args)
    if not success:
        return f"ERROR: {result}"
    if isinstance(result, dict):
        return result.get("result", "SUCCESS")
    return "SUCCESS"
