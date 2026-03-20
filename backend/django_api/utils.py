import asyncio
import json
from contextlib import contextmanager
from functools import wraps
from typing import Any

from django.http import HttpRequest, HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from backend.core.config import settings
from backend.core.security import new_csrf_token
from backend.db.session import SessionLocal
from backend.services import auth_service


class ApiError(Exception):
    def __init__(self, detail: Any, status_code: int = 400):
        super().__init__(str(detail))
        self.detail = detail
        self.status_code = status_code


@contextmanager
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def json_body(request: HttpRequest) -> dict[str, Any]:
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ApiError({"detail": "invalid json"}, 422) from exc


def json_response(payload: Any, status: int = 200) -> JsonResponse:
    safe = not isinstance(payload, list)
    return JsonResponse(payload, status=status, safe=safe, json_dumps_params={"ensure_ascii": False})


def api_view(allowed_methods: list[str]):
    def decorator(func):
        @csrf_exempt
        @wraps(func)
        def wrapper(request: HttpRequest, *args, **kwargs):
            if request.method not in allowed_methods:
                return json_response({"detail": "method not allowed"}, 405)
            try:
                result = func(request, *args, **kwargs)
                if isinstance(result, HttpResponse):
                    return result
                if isinstance(result, tuple) and len(result) == 2:
                    payload, status = result
                    return json_response(payload, status=status)
                return json_response(result)
            except ApiError as exc:
                return json_response({"detail": exc.detail}, status=exc.status_code)
            except Exception as exc:
                status_code = getattr(exc, "status_code", 500)
                detail = getattr(exc, "detail", str(exc))
                if isinstance(detail, dict) and "detail" in detail:
                    payload = detail
                else:
                    payload = {"detail": detail}
                return json_response(payload, status=status_code)

        return wrapper

    return decorator


def set_auth_cookies(response: HttpResponse, refresh_token: str, csrf_token: str) -> None:
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/api/auth",
    )
    response.set_cookie(
        settings.CSRF_COOKIE_NAME,
        csrf_token,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/api/auth",
    )


def clear_auth_cookies(response: HttpResponse) -> None:
    response.delete_cookie(settings.REFRESH_COOKIE_NAME, path="/api/auth", domain=settings.COOKIE_DOMAIN)
    response.delete_cookie(settings.CSRF_COOKIE_NAME, path="/api/auth", domain=settings.COOKIE_DOMAIN)


def require_csrf(request: HttpRequest) -> None:
    cookie = request.COOKIES.get(settings.CSRF_COOKIE_NAME)
    header = request.headers.get("X-CSRF-Token")
    if (not cookie) or (not header) or (cookie != header):
        raise ApiError("CSRF 토큰이 유효하지 않습니다.", 403)


def get_bearer_token(request: HttpRequest) -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth.split(" ", 1)[1].strip()
    return None


def get_current_user(request: HttpRequest, db):
    token = get_bearer_token(request)
    if not token:
        raise ApiError("unauthorized", 401)
    try:
        return auth_service.get_user_from_access(db, token)
    except Exception as exc:
        raise ApiError("unauthorized", 401) from exc


def optional_current_user(request: HttpRequest, db):
    token = get_bearer_token(request)
    if not token:
        return None
    try:
        return auth_service.get_user_from_access(db, token)
    except Exception:
        return None


def fresh_csrf_token() -> str:
    return new_csrf_token()


def issue_cookie_token_response(response: HttpResponse, refresh_token: str, csrf_token: str) -> None:
    set_auth_cookies(response, refresh_token=refresh_token, csrf_token=csrf_token)


def run_async(coro):
    return asyncio.run(coro)
