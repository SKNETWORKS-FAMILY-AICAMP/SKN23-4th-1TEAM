"""
File: social_auth.py
Author: 양창일
Created: 2026-02-15
Description: 소셜 로그인

Modification History:
- 2026-02-16: 초기 생성
- 2026-02-22(양창일): 스코프 카카오 닉네임 , 이미지 추가 
- 2026-02-23(양창일): 프로필에서 image_url 받도록 연결, get_or_create_social_user(..., profile_image_url=image_url) 전달, scope에 profile_image 포함
"""

import secrets  # state 생성
from urllib.parse import urlencode  # 쿼리 생성
from fastapi import APIRouter, Depends, Request, Response, HTTPException  # FastAPI
from fastapi.responses import RedirectResponse  # 응답
from sqlalchemy.orm import Session  # DB 세션
from backend.db.session import get_db  # DI
from backend.core.config import settings  # 설정
from backend.core.security import new_csrf_token  # csrf
from backend.routers.auth import set_auth_cookies  # 기존 쿠키 셋팅 함수 재사용
from backend.services import social_service  # 소셜 서비스
from backend.services.auth_service import issue_tokens_for_user_id  # 우리 JWT 발급

router = APIRouter(prefix="/api/auth", tags=["social-auth"])  # 라우터

def _set_oauth_state_cookie(res: Response, name: str, value: str) -> None:
    res.set_cookie(  # state 쿠키(짧게 쓰고 버림)
        key=name,
        value=value,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/",
        max_age=300,
    )

def _pop_oauth_state(req: Request, name: str) -> str:
    state = req.cookies.get(name)
    if not state:
        raise HTTPException(status_code=400, detail="invalid state")
    return state

def _oauth_popup_html(frontend_redirect_url: str, access_token: str) -> str:
    # 팝업 방식: opener로 access_token 전달 후 닫기 (URL에 토큰 안 남김)
    return f"""
<!doctype html>
<html>
  <body>
    <script>
      (function () {{
        try {{
          if (window.opener) {{
            window.opener.postMessage({{ type: "SOCIAL_LOGIN", accessToken: "{access_token}" }}, "{frontend_redirect_url.split('/social/callback')[0]}");
            window.close();
            return;
          }}
        }} catch (e) {{}}
        window.location.href = "{frontend_redirect_url}";
      }})();
    </script>
  </body>
</html>
"""

# Kakao
@router.get("/kakao/start")
def kakao_start():
    state = secrets.token_urlsafe(24)

    params = {
        "response_type": "code",
        "client_id": settings.KAKAO_CLIENT_ID,
        "redirect_uri": settings.KAKAO_REDIRECT_URI,
        "state": state,
        "scope": "account_email profile_nickname profile_image",
    }
    url = "https://kauth.kakao.com/oauth/authorize?" + urlencode(params)
    response = RedirectResponse(url)
    _set_oauth_state_cookie(response, "kakao_oauth_state", state)
    return response

@router.get("/kakao/callback")
def kakao_callback(code: str, state: str, req: Request, res: Response, db: Session = Depends(get_db)):
    saved_state = _pop_oauth_state(req, "kakao_oauth_state")
    if state != saved_state:
        raise HTTPException(status_code=400, detail="invalid state")

    access_token = social_service.kakao_exchange_code_for_token(code)
    provider_user_id, email, name, image_url = social_service.kakao_fetch_profile(access_token)

    user = social_service.get_or_create_social_user(
        db,
        provider="kakao",
        provider_user_id=provider_user_id,
        email=email,
        name=name,
        profile_image_url=image_url,
    )
    our_access, our_refresh = issue_tokens_for_user_id(db, user.id)

    csrf = new_csrf_token()
    frontend_url = f"{settings.FRONTEND_BASE_URL}/?{urlencode({'access_token': our_access, 'social': 'kakao'})}"
    response = RedirectResponse(url=frontend_url)
    set_auth_cookies(response, refresh_token=our_refresh, csrf_token=csrf)
    return response

# Google
@router.get("/google/start")
def google_start():
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
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)
    response = RedirectResponse(url)
    _set_oauth_state_cookie(response, "google_oauth_state", state)
    return response

@router.get("/google/callback")
def google_callback(code: str, state: str, req: Request, res: Response, db: Session = Depends(get_db)):
    saved_state = _pop_oauth_state(req, "google_oauth_state")
    if state != saved_state:
        raise HTTPException(status_code=400, detail="invalid state")

    access_token = social_service.google_exchange_code_for_token(code)
    provider_user_id, email, name, image_url = social_service.google_fetch_profile(access_token)

    user = social_service.get_or_create_social_user(
        db,
        provider="google",
        provider_user_id=provider_user_id,
        email=email,
        name=name,
        profile_image_url=image_url,
    )
    our_access, our_refresh = issue_tokens_for_user_id(db, user.id)

    csrf = new_csrf_token()
    frontend_url = f"{settings.FRONTEND_BASE_URL}/?{urlencode({'access_token': our_access, 'social': 'google'})}"
    response = RedirectResponse(url=frontend_url)
    set_auth_cookies(response, refresh_token=our_refresh, csrf_token=csrf)
    return response

# Naver
@router.get("/naver/start")
def naver_start():
    state = secrets.token_urlsafe(24)

    params = {
        "response_type": "code",
        "client_id": settings.NAVER_CLIENT_ID,
        "redirect_uri": settings.NAVER_REDIRECT_URI,
        "state": state,
    }
    url = "https://nid.naver.com/oauth2.0/authorize?" + urlencode(params)
    response = RedirectResponse(url)
    _set_oauth_state_cookie(response, "naver_oauth_state", state)
    return response

@router.get("/naver/callback")
def naver_callback(code: str, state: str, req: Request, res: Response, db: Session = Depends(get_db)):
    saved_state = _pop_oauth_state(req, "naver_oauth_state")
    if state != saved_state:
        raise HTTPException(status_code=400, detail="invalid state")

    access_token = social_service.naver_exchange_code_for_token(code, state=state)
    provider_user_id, email, name = social_service.naver_fetch_profile(access_token)

    user = social_service.get_or_create_social_user(
        db,
        provider="naver",
        provider_user_id=provider_user_id,
        email=email,
        name=name,
    )
    our_access, our_refresh = issue_tokens_for_user_id(db, user.id)

    csrf = new_csrf_token()
    frontend_url = f"{settings.FRONTEND_BASE_URL}/?{urlencode({'access_token': our_access, 'social': 'naver'})}"
    response = RedirectResponse(url=frontend_url)
    set_auth_cookies(response, refresh_token=our_refresh, csrf_token=csrf)
    return response
