import os
import secrets
import uuid
from datetime import datetime
from urllib.parse import urlencode

import PyPDF2
import requests
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
    save_memo,
    save_user_resume,
    toggle_board_answer_like,
    upsert_board_answer,
)
from backend.models.user import User
from backend.schemas.agent_schema import AgentChatRequest
from backend.schemas.attitude_schema import AttitudeEvent, AttitudeMetrics, AttitudeRequest, AttitudeResponse
from backend.schemas.jobs_schema import JobsSearchQuery
from backend.services import auth_service, social_service
from backend.services.attitude_service import analyze_attitude
from backend.services.fit_service import save_and_evaluate_answer
from backend.services.jobs_service import ExternalJobsAPIError, _join_multi, fetch_jobs
from backend.services.llm_service import (
    analyze_resume_comprehensive,
    evaluate_and_respond,
    generate_evaluation,
    get_home_guide_response_stream,
    get_proofread_result,
    get_translated_news_summary,
)
from backend.services.personality_feedback_service import generate_board_answer_feedback
from backend.services.personality_vector_service import save_board_answer_to_vector_db
from backend.services.rag_service import get_ai_service, store_resume
from backend.services.resume_service import get_latest_resume_fields
from backend.services.tavily_service import get_web_context_first, get_web_context_second
from .utils import (
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


@api_view(["POST"])
def auth_signup(request):
    body = json_body(request)
    with db_session() as db:
        try:
            auth_service.signup(db, body["email"], body["password"], body.get("name"))
        except KeyError as exc:
            raise ApiError(f"missing field: {exc.args[0]}", 422) from exc
        except ValueError as exc:
            raise ApiError(str(exc), 400) from exc
    return {"ok": True}


@api_view(["GET"])
def auth_check_email(request):
    email = request.GET.get("email", "")
    with db_session() as db:
        return {"exists": auth_service.check_user_exists(db, email)}


@api_view(["POST"])
def auth_send_signup_email(request):
    body = json_body(request)
    with db_session() as db:
        if auth_service.check_user_exists(db, body["email"]):
            raise ApiError("이미 가입한 이메일입니다.", 400)
    ok, error_msg = auth_service.send_auth_email(body["email"], body["auth_code"])
    if not ok:
        raise ApiError(error_msg, 500)
    return {"message": "인증번호 발송 성공"}


@api_view(["POST"])
def auth_login(request):
    body = json_body(request)
    with db_session() as db:
        try:
            access, refresh, user_id = auth_service.login(db, body["email"], body["password"])
        except ValueError as exc:
            raise ApiError("이메일 또는 비밀번호가 일치하지 않습니다.", 401) from exc
        user = db.query(User).filter(User.id == int(user_id)).first()
        if not user:
            raise ApiError("사용자를 찾을 수 없습니다.", 404)
        _ensure_active_user(user)
        csrf = fresh_csrf_token()
        response = json_response(_user_payload(user, access, refresh, csrf))
        issue_cookie_token_response(response, refresh_token=refresh, csrf_token=csrf)
        return response


@api_view(["POST"])
def auth_logout(request):
    require_csrf(request)
    refresh_token = request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
    with db_session() as db:
        if refresh_token:
            auth_service.revoke_refresh(db, refresh_token)
    response = json_response({"ok": True})
    clear_auth_cookies(response)
    return response


@api_view(["POST"])
def auth_refresh(request):
    body = json_body(request) if request.body else {}
    refresh_token = body.get("refresh_token") or request.COOKIES.get(settings.REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise ApiError("유효하지 않은 토큰입니다.", 401)
    if not body.get("refresh_token"):
        require_csrf(request)
    with db_session() as db:
        try:
            new_access, new_refresh = auth_service.rotate_refresh(db, refresh_token)
            user = auth_service.get_user_from_access(db, new_access)
        except Exception as exc:
            raise ApiError("유효하지 않은 토큰입니다.", 401) from exc
        csrf = fresh_csrf_token()
        response = json_response(_user_payload(user, new_access, new_refresh, csrf))
        issue_cookie_token_response(response, refresh_token=new_refresh, csrf_token=csrf)
        return response


@api_view(["GET"])
def auth_me(request):
    with db_session() as db:
        user = get_current_user(request, db)
        return {"id": user.id, "email": user.email, "name": user.name}


@api_view(["GET"])
def auth_verify(request):
    token = get_bearer_token(request)
    if not token:
        raise ApiError("토큰이 없습니다.", 401)
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")
        with db_session() as db:
            user = db.query(User).filter(User.id == int(user_id)).first() if user_id else None
            if not user:
                raise ApiError("유효하지 않은 인증 정보입니다.", 401)
            return {
                "id": user.id,
                "name": user.name or user.email.split("@")[0],
                "role": getattr(user, "role", "user"),
                "profile_image_url": getattr(user, "profile_image_url", None),
                "email": user.email,
                "tier": getattr(user, "tier", "normal"),
            }
    except ExpiredSignatureError as exc:
        raise ApiError(f"{settings.ACCESS_TOKEN_MINUTES}분 동안 활동이 없어 자동 로그아웃 되었습니다.", 401) from exc
    except JWTError as exc:
        raise ApiError("유효하지 않은 인증 정보입니다.", 401) from exc


@api_view(["POST"])
def auth_send_reset_email(request):
    body = json_body(request)
    with db_session() as db:
        if not auth_service.check_user_exists(db, body["email"]):
            raise ApiError("가입되지 않은 이메일입니다.", 404)
    ok, error_msg = auth_service.send_auth_email(body["email"], body["auth_code"])
    if not ok:
        raise ApiError(error_msg, 500)
    return {"message": "인증번호 발송 성공"}


@api_view(["POST"])
def auth_reset_password(request):
    body = json_body(request)
    with db_session() as db:
        success, error_msg = auth_service.update_password(db, body["email"], body["new_password"])
        if not success:
            raise ApiError(error_msg, 500)
    return {"message": "비밀번호가 성공적으로 변경되었습니다."}


@api_view(["POST"])
def auth_unlock(request):
    body = json_body(request)
    with db_session() as db:
        user = db.query(User).filter(User.email == body["email"]).first()
        if not user:
            raise ApiError("사용자를 찾을 수 없습니다.", 404)
        if getattr(user, "status", "active") != "dormant":
            raise ApiError("휴면 상태의 계정이 아닙니다.", 400)
        user.status = "active"
        db.commit()
    return {"detail": "휴면 해제 완료"}


@api_view(["POST"])
def auth_withdraw(request):
    body = json_body(request)
    with db_session() as db:
        user = db.query(User).filter(User.email == body["email"]).first()
        if not user:
            raise ApiError("사용자를 찾을 수 없습니다.", 404)
        user.status = "withdrawn"
        db.commit()
    return {"detail": "회원 탈퇴가 완료되었습니다."}


@api_view(["POST"])
def auth_profile_image(request):
    file = request.FILES.get("file")
    if not file:
        raise ApiError("file is required", 422)
    with db_session() as db:
        user = get_current_user(request, db)
        upload_dir = os.path.join("static", "profiles")
        os.makedirs(upload_dir, exist_ok=True)
        ext = file.name.split(".")[-1]
        new_filename = f"user_{user.id}_{uuid.uuid4().hex[:8]}.{ext}"
        file_path = os.path.join(upload_dir, new_filename)
        with open(file_path, "wb") as buffer:
            for chunk in file.chunks():
                buffer.write(chunk)
        image_url = f"{settings.BACKEND_BASE_URL}/static/profiles/{new_filename}"
        user.profile_image_url = image_url
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"profile_image_url": user.profile_image_url}


@api_view(["POST"])
def auth_upgrade(request):
    with db_session() as db:
        user = get_current_user(request, db)
        if getattr(user, "tier", "normal") == "premium":
            return {"detail": "이미 프리미엄 등급입니다.", "tier": "premium"}
        user.tier = "premium"
        db.add(user)
        db.commit()
        db.refresh(user)
        return {"detail": "등급 업그레이드가 완료되었습니다.", "tier": user.tier}


@api_view(["GET"])
def social_kakao_start(request):
    state = secrets.token_urlsafe(24)
    params = {
        "response_type": "code",
        "client_id": settings.KAKAO_CLIENT_ID,
        "redirect_uri": settings.KAKAO_REDIRECT_URI,
        "state": state,
        "scope": "account_email profile_nickname profile_image",
    }
    response = HttpResponseRedirect("https://kauth.kakao.com/oauth/authorize?" + urlencode(params))
    _set_oauth_state_cookie(response, "kakao_oauth_state", state)
    return response


@api_view(["GET"])
def social_kakao_callback(request):
    code = request.GET.get("code")
    state = request.GET.get("state")
    if state != _pop_oauth_state(request, "kakao_oauth_state"):
        raise ApiError("invalid state", 400)
    access_token = social_service.kakao_exchange_code_for_token(code)
    provider_user_id, email, name, image_url = social_service.kakao_fetch_profile(access_token)
    with db_session() as db:
        user = social_service.get_or_create_social_user(
            db,
            provider="kakao",
            provider_user_id=provider_user_id,
            email=email,
            name=name,
            profile_image_url=image_url,
        )
        _ensure_active_user(user)
        our_access, our_refresh = auth_service.issue_tokens_for_user_id(db, user.id)
    csrf = fresh_csrf_token()
    frontend_url = f"{settings.FRONTEND_BASE_URL}/?{urlencode({'access_token': our_access, 'social': 'kakao'})}"
    response = HttpResponseRedirect(frontend_url)
    issue_cookie_token_response(response, refresh_token=our_refresh, csrf_token=csrf)
    return response


@api_view(["GET"])
def social_google_start(request):
    state = secrets.token_urlsafe(24)
    params = {
        "response_type": "code",
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }
    response = HttpResponseRedirect("https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params))
    _set_oauth_state_cookie(response, "google_oauth_state", state)
    return response


@api_view(["GET"])
def social_google_callback(request):
    code = request.GET.get("code")
    state = request.GET.get("state")
    if state != _pop_oauth_state(request, "google_oauth_state"):
        raise ApiError("invalid state", 400)
    access_token = social_service.google_exchange_code_for_token(code)
    provider_user_id, email, name, image_url = social_service.google_fetch_profile(access_token)
    with db_session() as db:
        user = social_service.get_or_create_social_user(
            db,
            provider="google",
            provider_user_id=provider_user_id,
            email=email,
            name=name,
            profile_image_url=image_url,
        )
        _ensure_active_user(user)
        our_access, our_refresh = auth_service.issue_tokens_for_user_id(db, user.id)
    csrf = fresh_csrf_token()
    frontend_url = f"{settings.FRONTEND_BASE_URL}/?{urlencode({'access_token': our_access, 'social': 'google'})}"
    response = HttpResponseRedirect(frontend_url)
    issue_cookie_token_response(response, refresh_token=our_refresh, csrf_token=csrf)
    return response


@api_view(["GET"])
def social_naver_start(request):
    state = secrets.token_urlsafe(24)
    params = {
        "response_type": "code",
        "client_id": settings.NAVER_CLIENT_ID,
        "redirect_uri": settings.NAVER_REDIRECT_URI,
        "state": state,
    }
    response = HttpResponseRedirect("https://nid.naver.com/oauth2.0/authorize?" + urlencode(params))
    _set_oauth_state_cookie(response, "naver_oauth_state", state)
    return response


@api_view(["GET"])
def social_naver_callback(request):
    code = request.GET.get("code")
    state = request.GET.get("state")
    if state != _pop_oauth_state(request, "naver_oauth_state"):
        raise ApiError("invalid state", 400)
    access_token = social_service.naver_exchange_code_for_token(code, state=state)
    provider_user_id, email, name = social_service.naver_fetch_profile(access_token)
    with db_session() as db:
        user = social_service.get_or_create_social_user(
            db,
            provider="naver",
            provider_user_id=provider_user_id,
            email=email,
            name=name,
        )
        _ensure_active_user(user)
        our_access, our_refresh = auth_service.issue_tokens_for_user_id(db, user.id)
    csrf = fresh_csrf_token()
    frontend_url = f"{settings.FRONTEND_BASE_URL}/?{urlencode({'access_token': our_access, 'social': 'naver'})}"
    response = HttpResponseRedirect(frontend_url)
    issue_cookie_token_response(response, refresh_token=our_refresh, csrf_token=csrf)
    return response


@api_view(["GET", "POST"])
def home_memos(request):
    if request.method == "GET":
        limit = int(request.GET.get("limit", 30))
        return {"items": get_all_memos(limit=limit)}

    body = json_body(request)
    with db_session() as db:
        user = get_current_user(request, db)
        author = user.name or user.email.split("@")[0]
        save_memo(
            user_id=user.id,
            author=author,
            content=body.get("content", ""),
            color=body.get("color", "#FFF9C4"),
            border=body.get("border", "#FFF59D"),
            text_color=body.get("text_color", "#5D4037"),
        )
    return {"ok": True}


@api_view(["POST"])
def home_news(request):
    body = json_body(request)
    query = body.get("query", "")
    raw_news = get_web_context_second(query) if query else ""
    summary = get_translated_news_summary(raw_news) if raw_news else ""
    return {"content": summary}


@api_view(["POST"])
def home_guide(request):
    body = json_body(request)
    user_message = body.get("message", "")
    use_web_search = bool(body.get("use_web_search", False))
    web_context = get_web_context_first(user_message) if use_web_search and user_message else ""
    reply = "".join(get_home_guide_response_stream(user_message, web_context))
    return {"content": reply, "web_context": web_context}


@api_view(["POST"])
def home_proofread_file(request):
    file = request.FILES.get("file")
    document_type = request.POST.get("document_type")
    if not file or not document_type:
        raise ApiError("file and document_type are required", 422)
    content_text = ""
    if file.name.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            content_text += (page.extract_text() or "") + "\n"
    else:
        content_text = file.read().decode("utf-8", errors="ignore")
    if not content_text.strip():
        raise ApiError("문서에서 텍스트를 추출할 수 없습니다.", 400)
    return {"feedback": get_proofread_result(content_text, document_type)}


@api_view(["POST"])
def infer_proofread(request):
    body = json_body(request)
    return {"feedback": get_proofread_result(body.get("content", ""), body.get("document_type", "resume"))}


@api_view(["GET", "POST"])
def board_questions_collection(request):
    if request.method == "GET":
        return {"items": get_board_questions()}

    body = json_body(request)
    raw_content = (body.get("raw_content") or "").strip()
    if len(raw_content) < 5:
        raise ApiError("내용이 너무 짧습니다.", 400)
    with db_session() as db:
        get_current_user(request, db)
    existing_questions = get_all_board_questions()
    existing_text = "\n".join(f"- {q}" for q in existing_questions)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ApiError("서버에 OPENAI_API_KEY가 설정되지 않았습니다.", 500)
    client = OpenAI(api_key=api_key)
    prompt = (
        f"아래는 기존 인성 면접 질문 목록입니다.\n{existing_text}\n\n"
        f"사용자가 입력한 새로운 상황/질문:\n\"{raw_content}\"\n\n"
        "유효하지 않으면 INVALID, 기술 질문이면 TECHNICAL, 중복이면 DUPLICATE, "
        "정제 가능한 유효 질문이면 'REFINED: ...' 형식으로만 답해주세요."
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        ai_result = response.choices[0].message.content.strip()
    except Exception as exc:
        raise ApiError("AI 질문 교정 중 오류가 발생했습니다.", 500) from exc
    if ai_result == "INVALID":
        raise ApiError("INVALID_CONTENT", 422)
    if ai_result == "TECHNICAL":
        raise ApiError("TECHNICAL_CONTENT", 422)
    if ai_result == "DUPLICATE":
        raise ApiError("DUPLICATE_CONTENT", 409)
    refined_content = ai_result.replace("REFINED:", "").strip()
    new_question_id = create_board_question(refined_content)
    return {"ok": True, "question_id": new_question_id, "refined_content": refined_content}


@api_view(["GET", "DELETE"])
def board_question_resource(request, question_id: int):
    if request.method == "GET":
        limit = int(request.GET.get("limit", 10))
        offset = int(request.GET.get("offset", 0))
        question = get_board_question(question_id)
        if not question:
            raise ApiError("질문을 찾을 수 없습니다.", 404)
        with db_session() as db:
            viewer = optional_current_user(request, db)
            viewer_id = viewer.id if viewer else None
        answers = get_board_answers(question_id, limit=limit, offset=offset, viewer_id=viewer_id)
        total_count = count_board_answers(question_id)
        return {
            "question": question,
            "answers": answers,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(answers) < total_count,
        }

    with db_session() as db:
        user = get_current_user(request, db)
        if getattr(user, "role", "user") != "admin":
            raise ApiError("관리자만 질문을 삭제할 수 있습니다.", 403)
    question = get_board_question(question_id)
    if not question:
        raise ApiError("질문을 찾을 수 없습니다.", 404)
    delete_board_question(question_id)
    return {"ok": True, "message": "질문을 삭제했습니다."}


@api_view(["POST"])
def board_create_answer(request, question_id: int):
    body = json_body(request)
    question = get_board_question(question_id)
    if not question:
        raise ApiError("질문을 찾을 수 없습니다.", 404)
    content = (body.get("content") or "").strip()
    if len(content) < 5:
        raise ApiError("답변은 5자 이상 입력해주세요.", 400)
    with db_session() as db:
        user = get_current_user(request, db)
        author_name = user.name or user.email.split("@")[0]
        answer_id = upsert_board_answer(question_id, user.id, author_name, content)
        feedback = None
        try:
            feedback = save_and_evaluate_answer(answer_id, user.id, question_id, question["content"], content)
        except Exception:
            feedback = None
        try:
            save_board_answer_to_vector_db(
                answer_id=answer_id,
                user_id=user.id,
                question_id=question_id,
                question_text=question["content"],
                answer_text=content,
            )
        except Exception:
            pass
    return {"ok": True, "answer_id": answer_id, "author_name": author_name, "feedback": feedback}


@api_view(["POST"])
def board_toggle_like(request, answer_id: int):
    with db_session() as db:
        user = get_current_user(request, db)
        answer = get_board_answer(answer_id)
        if not answer:
            raise ApiError("답변을 찾을 수 없습니다.", 404)
        liked = toggle_board_answer_like(answer_id, user.id)
    updated = get_board_answer(answer_id) or answer
    return {"ok": True, "liked": liked, "like_count": int(updated.get("like_count", 0)), "question_id": answer.get("question_id")}


@api_view(["POST"])
def board_feedback(request, answer_id: int):
    with db_session() as db:
        user = get_current_user(request, db)
        answer = get_board_answer(answer_id)
        if not answer:
            raise ApiError("답변을 찾을 수 없습니다.", 404)
        if answer["user_id"] != user.id:
            raise ApiError("본인 답변만 피드백 받을 수 있습니다.", 403)
    question = get_board_question(answer["question_id"])
    feedback = generate_board_answer_feedback(
        question_id=answer["question_id"],
        question_text=question["content"],
        answer_text=answer["content"],
        user_id=user.id,
    )
    return {"ok": True, "answer_id": answer_id, "feedback": feedback}


@api_view(["DELETE"])
def board_delete_answer(request, answer_id: int):
    with db_session() as db:
        user = get_current_user(request, db)
        answer = get_board_answer(answer_id)
        if not answer:
            raise ApiError("답변을 찾을 수 없습니다.", 404)
        if answer["user_id"] != user.id:
            raise ApiError("본인 답변만 삭제할 수 있습니다.", 403)
    delete_board_answer(answer_id)
    return {"ok": True, "message": "삭제했습니다."}


@api_view(["POST"])
def infer_ingest(request):
    file = request.FILES.get("file")
    session_id = request.GET.get("session_id", "default")
    if not file:
        raise ApiError("file is required", 422)
    contents = file.read()
    file_path = f"temp_{file.name}"
    with open(file_path, "wb") as buffer:
        buffer.write(contents)
    content_text = ""
    try:
        if file.name.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(file_path)
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    content_text += extracted + "\n"
        else:
            content_text = contents.decode("utf-8", errors="ignore")
        store_resume(content_text, session_id)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
    return {"message": "이력서 분석 완료", "resume_text": content_text.strip()}


@api_view(["POST"])
def infer_start(request):
    body = json_body(request)
    user_id = None
    with db_session() as db:
        user = optional_current_user(request, db)
        if user:
            user_id = user.id
        new_session = base.InterviewSession(
            user_id=user_id,
            job_role=body.get("job_role", "개발자"),
            difficulty=body.get("difficulty", "미들"),
            persona=body.get("persona", "꼼꼼한 기술 면접관"),
            resume_used=body.get("resume_used", False),
            resume_id=body.get("resume_id"),
            manual_tech_stack=body.get("manual_tech_stack"),
            status="START",
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return {"session_id": new_session.id}


@api_view(["GET"])
def infer_questions(request):
    job_role = request.GET.get("job_role")
    difficulty = request.GET.get("difficulty")
    limit = int(request.GET.get("limit", 5))
    with db_session() as db:
        rows = (
            db.query(base.QuestionPool)
            .join(base.JobCategory)
            .filter(base.JobCategory.target_role == job_role, base.QuestionPool.difficulty == difficulty)
            .order_by(func.rand())
            .limit(limit)
            .all()
        )
    return {"items": [{"id": row.id, "question": row.content, "difficulty": row.difficulty} for row in rows]}


@api_view(["POST"])
def infer_stt(request):
    file = request.FILES.get("file")
    if not file:
        raise ApiError("file is required", 422)
    temp_filename = f"temp_{file.name}.wav"
    with open(temp_filename, "wb") as f:
        for chunk in file.chunks():
            f.write(chunk)
    try:
        with open(temp_filename, "rb") as audio_data:
            text = _get_ai().stt_whisper(audio_data)
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
    return {"text": text}


@api_view(["POST"])
def infer_tts(request):
    body = json_body(request)
    text = body.get("text", "")
    if not text:
        raise ApiError("텍스트가 제공되지 않았습니다.", 400)
    try:
        audio_content = _get_ai().tts_voice(text)
    except Exception as local_exc:
        try:
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")
            client = OpenAI(api_key=api_key)
            tts_response = client.audio.speech.create(model="tts-1", voice="alloy", input=text)
            audio_content = tts_response.content
        except Exception as openai_exc:
            raise ApiError(f"TTS 생성 실패: local={str(local_exc)} | openai={str(openai_exc)}", 500) from openai_exc
    return HttpResponse(audio_content, content_type="audio/mpeg")


@api_view(["POST"])
def infer_evaluate_turn(request):
    body = json_body(request)
    answer = body.get("answer", "")
    if not str(answer).strip():
        raise ApiError("answer가 비어 있습니다.", 400)
    result = evaluate_and_respond(
        question=body.get("question", "면접 질문"),
        answer=answer,
        job_role=body.get("job_role", "Python 백엔드 개발자"),
        difficulty=body.get("difficulty", "미들"),
        persona_style=body.get("persona_style", "꼼꼼한 기술 면접관"),
        user_id=str(body.get("user_id", "guest")),
        resume_text=body.get("resume_text"),
        next_main_question=body.get("next_main_question"),
        followup_count=int(body.get("followup_count", 0)),
    )
    attitude = body.get("attitude")
    summary_text = (attitude.get("summary_text") or "").strip() if isinstance(attitude, dict) else ""
    if summary_text:
        base_feedback = (result.get("feedback") or "").strip()
        base_reply = (result.get("reply_text") or "").strip()
        result["feedback"] = f"{base_feedback} 태도 측면에서는 {summary_text}" if base_feedback else f"태도 측면에서는 {summary_text}"
        result["reply_text"] = f"{base_reply}\n\n[태도 피드백] {summary_text}" if base_reply else f"[태도 피드백] {summary_text}"
    return result


@api_view(["GET"])
def infer_realtime_token(request):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ApiError("서버에 OPENAI_API_KEY가 설정되지 않았습니다.", 500)
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {"model": os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview-2024-12-17"), "voice": "echo"}
    try:
        response = requests.post("https://api.openai.com/v1/realtime/sessions", headers=headers, json=data, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        raise ApiError("AI 면접용 토큰 발급에 실패했습니다.", 500) from exc


@api_view(["POST"])
def interview_analyze_resume(request):
    body = json_body(request)
    try:
        result = analyze_resume_comprehensive(body["resume_text"], body["job_role"])
    except Exception as exc:
        raise ApiError(str(exc), 500) from exc
    return {"status": "success", "data": result}


@api_view(["POST"])
def interview_store_resume(request):
    body = json_body(request)
    try:
        chunk_count = store_resume(body["resume_text"], body["user_id"])
    except Exception as exc:
        raise ApiError(str(exc), 500) from exc
    return {"status": "success", "chunk_count": chunk_count}


@api_view(["POST"])
def interview_evaluate(request):
    body = json_body(request)
    try:
        result = generate_evaluation(body["messages"], body["job_role"], body["difficulty"], body.get("resume_text"))
    except Exception as exc:
        raise ApiError(str(exc), 500) from exc
    return {"status": "success", "evaluation": result}


@api_view(["POST"])
def interview_chat(request):
    body = json_body(request)
    try:
        result = evaluate_and_respond(
            question=body.get("current_question", "시작"),
            answer=body.get("user_answer", ""),
            job_role=body.get("job_role") or "개발자",
            difficulty=body.get("difficulty") or "중급",
            persona_style=body.get("persona") or "꼼꼼한 기술 면접관",
            user_id=str(body.get("user_id", "anonymous")),
            resume_text=body.get("resume_text"),
            next_main_question=body.get("next_main_question"),
            followup_count=body.get("followup_count", 0),
        )
    except Exception as exc:
        raise ApiError(str(exc), 500) from exc
    return {"status": "success", "data": result}


@api_view(["POST"])
def interview_save_details(request):
    body = json_body(request)
    session_id = body.get("session_id")
    if not session_id:
        raise ApiError("session_id is required", 400)
    with db_session() as db:
        new_detail = base.InterviewDetail(
            session_id=session_id,
            turn_index=body.get("turn_index", 0),
            question=body.get("question", ""),
            answer=body.get("answer", ""),
            response_time=body.get("response_time", 0),
            score=body.get("score", 0.0),
            sentiment_score=body.get("sentiment_score", 0.0),
            feedback=body.get("feedback", ""),
            is_followup=body.get("is_followup", False),
        )
        db.add(new_detail)
        db.commit()
    return {"message": "상세 기록 저장 완료"}


@api_view(["GET", "PUT", "DELETE"])
def interview_session_resource(request, session_id: int):
    if request.method == "GET":
        return {"items": get_details_by_session(session_id)}

    if request.method == "DELETE":
        with db_session() as db:
            current_user = get_current_user(request, db)
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT id FROM interview_sessions WHERE id=%s AND user_id=%s", (session_id, current_user.id))
                    session = cur.fetchone()
                    if not session:
                        raise ApiError("세션을 찾을 수 없거나 삭제 권한이 없습니다.", 404)
                    cur.execute("DELETE FROM interview_details WHERE session_id=%s", (session_id,))
                    cur.execute("DELETE FROM interview_sessions WHERE id=%s", (session_id,))
        return {"message": "삭제 완료", "session_id": session_id}

    body = json_body(request)
    with db_session() as db:
        session_record = db.query(base.InterviewSession).filter(base.InterviewSession.id == session_id).first()
        if not session_record:
            raise ApiError("세션을 찾을 수 없습니다.", 404)
        if "total_score" in body:
            session_record.total_score = body["total_score"]
        if "status" in body:
            session_record.status = body["status"]
            if body["status"] == "COMPLETED":
                session_record.ended_at = datetime.now()
        db.commit()
    return {"message": "세션 업데이트 완료"}


@api_view(["GET"])
def interview_sessions(request):
    user_id = int(request.GET.get("user_id", 0))
    return {"items": get_sessions_by_user(user_id)}


@api_view(["POST"])
def jobs_search(request):
    body = json_body(request)
    query = JobsSearchQuery(**body)
    params = {"startPage": query.startPage, "display": query.display}
    if query.empCoNo:
        params["empCoNo"] = query.empCoNo
    if query.jobsCd:
        params["jobsCd"] = query.jobsCd
    if query.empWantedTitle:
        params["empWantedTitle"] = query.empWantedTitle
    if query.sortField:
        params["sortField"] = query.sortField
    if query.sortOrderBy:
        params["sortOrderBy"] = query.sortOrderBy
    for field in ("coClcd", "empWantedTypeCd", "empWantedCareerCd", "empWantedEduCd"):
        value = _join_multi(getattr(query, field))
        if value:
            params[field] = value
    try:
        return run_async(fetch_jobs(params))
    except ExternalJobsAPIError as exc:
        raise ApiError(str(exc), 502) from exc


@api_view(["GET", "POST"])
def resumes_collection(request):
    if request.method == "GET":
        user_id = int(request.GET.get("user_id", 0))
        return {"items": get_user_resumes(user_id)}
    body = json_body(request)
    analysis_result = body.get("analysis_result")
    if analysis_result is None:
        analysis_result = analyze_resume_comprehensive(body["resume_text"], body["job_role"])
    resume_id = save_user_resume(
        user_id=body["user_id"],
        title=body["title"],
        job_role=body["job_role"],
        resume_text=body["resume_text"],
        analysis_result=analysis_result,
    )
    return {"id": resume_id, "analysis_result": analysis_result}


@api_view(["GET"])
def resumes_latest(request):
    user_id = int(request.GET.get("user_id", 0))
    if not user_id or user_id <= 0:
        return {"user_id": user_id, "job_role": None, "analysis_result": None}
    with db_session() as db:
        job_role, analysis_result = get_latest_resume_fields(db, str(user_id))
    return {"user_id": user_id, "job_role": job_role, "analysis_result": analysis_result}


@api_view(["DELETE"])
def resumes_delete(request, resume_id: int):
    delete_user_resume(resume_id)
    return {"ok": True}


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


@api_view(["POST"])
def agent_chat(request):
    body = AgentChatRequest(**json_body(request))
    try:
        return run_agent(body.message)
    except Exception as exc:
        raise ApiError("에이전트 처리 중 서버 오류가 발생했습니다.", 500) from exc


@api_view(["POST"])
def attitude_infer(request):
    parsed = AttitudeRequest(**json_body(request))
    if not parsed.frames:
        raise ApiError("frames is empty", 400)
    result = analyze_attitude([frame.model_dump() for frame in parsed.frames], fps=2.0)
    response = AttitudeResponse(
        metrics=AttitudeMetrics(**result["metrics"]),
        events=[AttitudeEvent(**event) for event in result["events"]],
        summary_text=result["summary_text"],
    )
    return response.model_dump()
