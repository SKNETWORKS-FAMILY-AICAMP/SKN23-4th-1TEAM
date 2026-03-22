import os
import secrets
import uuid
from datetime import datetime
from urllib.parse import urlencode

import PyPDF2
import requests
from django.core import signing
from django.http import HttpResponse, HttpResponseRedirect
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from openai import OpenAI
from sqlalchemy import func

from backend.ai.agent import run_agent
from backend.core.config import settings
from backend.db import base
from backend.db.database import (
    count_board_answers,
    create_board_question,
    delete_board_answer,
    delete_board_question,
    delete_user_resume,
    get_all_board_questions,
    get_all_memos,
    get_board_answer,
    get_board_answers,
    get_board_question,
    get_board_questions,
    get_connection,
    get_details_by_session,
    get_sessions_by_user,
    get_user_resumes,
    save_board_answer_feedback,
    save_memo,
    save_user_resume,
    toggle_board_answer_like,
    upsert_board_answer,
)
from backend.models.user import User
from backend.schemas.agent_schema import AgentChatRequest
from backend.schemas.attitude_schema import (
    AttitudeEvent,
    AttitudeMetrics,
    AttitudeRequest,
    AttitudeResponse,
)
from backend.schemas.jobs_schema import JobsSearchQuery
from backend.services import auth_service, social_service
from backend.services.attitude_service import analyze_attitude
from backend.services.jobs_service import ExternalJobsAPIError, _join_multi, fetch_jobs
from backend.services.llm_service import (
    analyze_resume_comprehensive,
    evaluate_and_respond,
    generate_evaluation,
    get_home_guide_response_stream,
    get_proofread_result,
    get_translated_news_summary,
)
from backend.services.personality_service import (
    generate_board_answer_feedback,
    save_and_evaluate_answer,
)
from backend.services.rag_service import get_ai_service, store_resume
from backend.services.resume_service import get_latest_resume_fields
from backend.services.tavily_service import get_web_context_first, get_web_context_second
from ..utils import (
    ApiError,
    api_view,
    clear_auth_cookies,
    db_session,
    fresh_csrf_token,
    get_bearer_token,
    get_current_user,
    issue_cookie_token_response,
    json_body,
    json_response,
    optional_current_user,
    require_csrf,
    run_async,
)


__all__ = [
    # stdlib / third-party re-exports
    "os", "secrets", "uuid", "datetime", "urlencode",
    "PyPDF2", "requests", "HttpResponse", "HttpResponseRedirect",
    "jwt", "ExpiredSignatureError", "JWTError", "OpenAI", "func",
    # backend modules
    "run_agent", "settings", "base",
    # db
    "count_board_answers", "create_board_question", "delete_board_answer",
    "delete_board_question", "delete_user_resume", "get_all_board_questions",
    "get_all_memos", "get_board_answer", "get_board_answers", "get_board_question",
    "get_board_questions", "get_connection", "get_details_by_session",
    "get_sessions_by_user", "get_user_resumes", "save_board_answer_feedback",
    "save_memo", "save_user_resume", "toggle_board_answer_like", "upsert_board_answer",
    # models / schemas
    "User", "AgentChatRequest", "AttitudeEvent", "AttitudeMetrics",
    "AttitudeRequest", "AttitudeResponse", "JobsSearchQuery",
    # services
    "auth_service", "social_service", "analyze_attitude",
    "ExternalJobsAPIError", "_join_multi", "fetch_jobs",
    "analyze_resume_comprehensive", "evaluate_and_respond", "generate_evaluation",
    "get_home_guide_response_stream", "get_proofread_result", "get_translated_news_summary",
    "generate_board_answer_feedback", "save_and_evaluate_answer",
    "get_ai_service", "store_resume", "get_latest_resume_fields",
    "get_web_context_first", "get_web_context_second",
    # utils
    "ApiError", "api_view", "clear_auth_cookies", "db_session", "fresh_csrf_token",
    "get_bearer_token", "get_current_user", "issue_cookie_token_response",
    "json_body", "json_response", "optional_current_user", "require_csrf", "run_async",
    # private helpers — must be in __all__ to be exported by `import *`
    "_get_ai", "_user_payload", "_ensure_active_user",
    "_set_oauth_state_cookie", "_pop_oauth_state",
    "_create_oauth_state", "_validate_oauth_state",
]


def _get_ai():
    return get_ai_service()


def _user_payload(user: User, access: str, refresh: str, csrf: str) -> dict:
    return {
        "access_token": access,
        "token_type": "bearer",
        "id": user.id,
        "name": user.name or user.email.split("@")[0],
        "role": getattr(user, "role", "user"),
        "profile_image_url": getattr(user, "profile_image_url", None),
        "email": user.email,
        "tier": getattr(user, "tier", "normal"),
        "refresh_token": refresh,
        "csrf_token": csrf,
    }


def _ensure_active_user(user: User) -> None:
    user_status = getattr(user, "status", "active")
    if user_status == "withdrawn":
        raise ApiError("탈퇴 처리된 계정입니다.", 403)
    if user_status == "dormant":
        raise ApiError("장기 미접속으로 휴면 전환된 계정입니다.", 403)


def _set_oauth_state_cookie(response: HttpResponse, name: str, value: str) -> None:
    response.set_cookie(
        name,
        value,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/",
        max_age=300,
    )


def _pop_oauth_state(request, name: str) -> str:
    state = request.COOKIES.get(name)
    if not state:
        raise ApiError("invalid state", 400)
    return state


def _create_oauth_state(provider: str) -> str:
    payload = {
        "provider": provider,
        "nonce": secrets.token_urlsafe(16),
    }
    return signing.dumps(payload, salt="social-oauth-state")


def _validate_oauth_state(state: str | None, provider: str) -> None:
    if not state:
        raise ApiError("invalid state", 400)
    try:
        payload = signing.loads(
            state,
            salt="social-oauth-state",
            max_age=300,
        )
    except signing.BadSignature as exc:
        raise ApiError("invalid state", 400) from exc
    except signing.SignatureExpired as exc:
        raise ApiError("invalid state", 400) from exc

    if payload.get("provider") != provider:
        raise ApiError("invalid state", 400)
