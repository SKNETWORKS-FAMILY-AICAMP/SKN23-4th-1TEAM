"""
File: social_service.py
Author: 양창일
Created: 2026-02-15
Description: 소셜 로그인

Modification History:
- 2026-02-16: 초기 생성
- 2026-02-23(양창일): 소셜 로그인 수정, 카카오 패치 이미지 추가 get_or_create_social_user(..., profile_image_url=None) 파라미터 추가
                    , 기존 유저 로그인 시 profile_image_url 값이 오면 업데이트, 신규 유저 생성 시 profile_image_url 저장
"""


import requests  # HTTP 호출
from sqlalchemy.orm import Session  # DB 세션
from backend.core.config import settings  # 설정
from backend.models.user import User  # 유저 모델

def _require(value: str, name: str) -> str:
    if not value:
        raise ValueError(f"missing {name}")
    return value

def get_or_create_social_user(
    db: Session,
    provider: str,
    provider_user_id: str,
    email: str | None,
    name: str | None = None,
    profile_image_url: str | None = None,
) -> User:
    user = (
        db.query(User)
        .filter(User.provider == provider, User.provider_user_id == provider_user_id)
        .first()
    )
    if user:
        changed = False
        if (not user.email) and email:
            user.email = email
            changed = True
        if name and user.name != name:
            user.name = name
            changed = True
        elif (not user.name):
            user.name = email or f"{provider}_{provider_user_id}"
            changed = True
        if profile_image_url and user.profile_image_url != profile_image_url:
            user.profile_image_url = profile_image_url
            changed = True
        if changed:
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    display_name = name or email or f"{provider}_{provider_user_id}"

    user = User(
        name=display_name,
        email=email,
        password=None,
        provider=provider,
        provider_user_id=provider_user_id,
        profile_image_url=profile_image_url,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# Kakao
def kakao_exchange_code_for_token(code: str) -> str:
    _require(settings.KAKAO_CLIENT_ID, "KAKAO_CLIENT_ID")
    url = "https://kauth.kakao.com/oauth/token"
    data = {
        "grant_type": "authorization_code",
        "client_id": settings.KAKAO_CLIENT_ID,
        "redirect_uri": settings.KAKAO_REDIRECT_URI,
        "code": code,
    }
    if settings.KAKAO_CLIENT_SECRET:
        data["client_secret"] = settings.KAKAO_CLIENT_SECRET

    resp = requests.post(url, data=data, timeout=10)
    resp.raise_for_status()
    j = resp.json()
    return j["access_token"]

def kakao_fetch_profile(access_token: str) -> tuple[str, str | None, str | None, str | None]:
    url = "https://kapi.kakao.com/v2/user/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()

    j = resp.json()
    provider_user_id = str(j["id"])

    kakao_account = j.get("kakao_account") or {}
    properties = j.get("properties") or {}
    profile = kakao_account.get("profile") or {}

    email = kakao_account.get("email")
    name = properties.get("nickname") or profile.get("nickname")

    # 선택 동의 항목: 없으면 None
    image_url = profile.get("profile_image_url") or properties.get("profile_image")
    if profile.get("is_default_image") is True:
        image_url = None

    return provider_user_id, email, name, image_url

# Google
def google_exchange_code_for_token(code: str) -> str:
    _require(settings.GOOGLE_CLIENT_ID, "GOOGLE_CLIENT_ID")
    _require(settings.GOOGLE_CLIENT_SECRET, "GOOGLE_CLIENT_SECRET")
    url = "https://oauth2.googleapis.com/token"
    data = {
        "code": code,
        "client_id": settings.GOOGLE_CLIENT_ID,
        "client_secret": settings.GOOGLE_CLIENT_SECRET,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }
    resp = requests.post(url, data=data, timeout=10)
    resp.raise_for_status()
    j = resp.json()
    return j["access_token"]

def google_fetch_profile(access_token: str) -> tuple[str, str | None, str | None, str | None]:
    # 실서비스에서는 id_token 검증(서명/iss/aud)까지 하는 게 더 안전함
    url = "https://www.googleapis.com/oauth2/v2/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    j = resp.json()
    provider_user_id = str(j.get("id"))
    email = j.get("email")
    name = j.get("name")
    image_url = j.get("picture")
    return provider_user_id, email, name, image_url

# Naver
def naver_exchange_code_for_token(code: str, state: str) -> str:
    _require(settings.NAVER_CLIENT_ID, "NAVER_CLIENT_ID")
    _require(settings.NAVER_CLIENT_SECRET, "NAVER_CLIENT_SECRET")
    url = "https://nid.naver.com/oauth2.0/token"
    params = {
        "grant_type": "authorization_code",
        "client_id": settings.NAVER_CLIENT_ID,
        "client_secret": settings.NAVER_CLIENT_SECRET,
        "code": code,
        "state": state,
    }
    resp = requests.get(url, params=params, timeout=10)
    resp.raise_for_status()
    j = resp.json()
    return j["access_token"]

def naver_fetch_profile(access_token: str) -> tuple[str, str | None, str | None]:
    url = "https://openapi.naver.com/v1/nid/me"
    headers = {"Authorization": f"Bearer {access_token}"}
    resp = requests.get(url, headers=headers, timeout=10)
    resp.raise_for_status()
    j = resp.json()
    res = j.get("response") or {}
    provider_user_id = str(res.get("id"))
    email = res.get("email")
    name = res.get("name") or res.get("nickname")
    return provider_user_id, email, name
