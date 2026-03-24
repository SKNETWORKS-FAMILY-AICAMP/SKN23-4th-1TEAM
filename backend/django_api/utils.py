import asyncio
import json
import traceback
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
                traceback.print_exc()
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


JOB_ROLE_TO_OCCUPATIONS = {
    "Python 백엔드 개발자": [
        "133100",  # 시스템 소프트웨어 개발자
        "133101",  # 시스템 소프트웨어 개발자(프로그래머)
        "133200",  # 응용 소프트웨어 개발자
        "133203",  # 범용 응용 소프트웨어 프로그래머
        "133204",  # 산업특화 응용 소프트웨어 프로그래머
        "133202",  # C언어 및 그 외 프로그래밍 언어 전문가
        "133300",  # 웹 개발자
        "133900",  # 기타 컴퓨터 시스템 및 소프트웨어 전문가
    ],
    "Java 백엔드 개발자": [
        "133201",  # JAVA 프로그래밍 언어 전문가
        "133200",  # 응용 소프트웨어 개발자
        "133203",  # 범용 응용 소프트웨어 프로그래머
        "133204",  # 산업특화 응용 소프트웨어 프로그래머
        "133100",  # 시스템 소프트웨어 개발자
        "133101",  # 시스템 소프트웨어 개발자(프로그래머)
        "133202",  # C언어 및 그 외 프로그래밍 언어 전문가
        "133900",  # 기타 컴퓨터 시스템 및 소프트웨어 전문가
        "135102",  # 데이터베이스 운영·관리자
    ],
    "프론트엔드 개발자": [
        "133100",  # 시스템 소프트웨어 개발자
        "133300",  # 웹 개발자
        "133301",  # 웹 개발자(웹 엔지니어·웹 프로그래머)
        "133302",  # 웹 기획자
        "133200",  # 응용 소프트웨어 개발자
        "133207",  # 모바일 애플리케이션 프로그래머
        "133205",  # 네트워크 프로그래머
        "133900",  # 기타 컴퓨터 시스템 및 소프트웨어 전문가
    ],
    "AI/ML 엔지니어": [
        "133200",  # 응용 소프트웨어 개발자
        "133202",  # C언어 및 그 외 프로그래밍 언어 전문가
        "133203",  # 범용 응용 소프트웨어 프로그래머
        "133204",  # 산업특화 응용 소프트웨어 프로그래머
        "133100",  # 시스템 소프트웨어 개발자
        "133102",  # 펌웨어 및 임베디드 소프트웨어 프로그래머
        "133900",  # 기타 컴퓨터 시스템 및 소프트웨어 전문가
    ],
    "데이터 엔지니어": [
        "133203",  # 범용 응용 소프트웨어 프로그래머
        "133204",  # 산업특화 응용 소프트웨어 프로그래머
        "133200",  # 응용 소프트웨어 개발자
        "133202",  # C언어 및 그 외 프로그래밍 언어 전문가
        "133100",  # 시스템 소프트웨어 개발자
        "133205",  # 네트워크 프로그래머
        "133206",  # 게임 프로그래머
        "133900",  # 기타 컴퓨터 시스템 및 소프트웨어 전문가
        "135200",  # 데이터 분석가(빅데이터 분석가)
        
    ],
    "데이터 사이언티스트": [
        "133202",  # C언어 및 그 외 프로그래밍 언어 전문가
        "135200",  # 데이터 분석가(빅데이터 분석가)
        "136101",  # 정보시스템 운영자
        "136103",  # IT 기술지원 전문가
        "135101",  # 데이터 설계 및 프로그래머
        "133200",  # 응용 소프트웨어 개발자
    ],
    "데이터 분석가": [
        "133202",  # C언어 및 그 외 프로그래밍 언어 전문가
        "135200",  # 데이터 분석가(빅데이터 분석가)
        "135100",  # 데이터 시스템 전문가
        "135101",  # 데이터 설계 및 프로그래머
        "133200",  # 응용 소프트웨어 개발자
    ]
}

# 채용 공고용
def normalize_job_role(value: str | None) -> str:
    return (value or "").strip()


def infer_occupation_codes(job_role: str | None) -> list[str]:
    normalized = normalize_job_role(job_role)
    if not normalized:
        return []
    return JOB_ROLE_TO_OCCUPATIONS.get(normalized, [])


def infer_jobs_cd_value(job_role: str | None) -> str | None:
    codes = infer_occupation_codes(job_role)
    if not codes:
        return None
    return "|".join(codes)


def resolve_emp_wanted_title(
    emp_wanted_title: str | None,
    keywords: str | None,
    job_role: str | None,
) -> str | None:
    if keywords and keywords.strip():
        return keywords.strip()
    if emp_wanted_title and emp_wanted_title.strip():
        return emp_wanted_title.strip()
    if job_role and job_role.strip():
        return job_role.strip()
    return None
