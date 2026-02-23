"""
File: auth.py
Author: 양창일, 김지우
Created: 2026-02-15
Description: 로그인, 회원가입 처리하는 API 주소

Modification History:
- 2026-02-15 (양창일): 초기 생성 (로그인, 회원가입, CSRF 방어, Rate Limit 등)
- 2026-02-21 (김지우): 로그인 API 로직 보완
- 2026-02-22 (김지우): 토큰 검증(/verify) API 및 비밀번호 찾기(/send-reset-email, /reset-password) API 통합 추가, 권한(Role) 반환 로직 동적 수정
- 2026-02-22 (양창일): username 혼동으로 email, name으로 정리, jwt처리 수정
- 2026-02-23 (양창일): profile_image_url 포함
- 2026-02-23 (김지우): 휴면(dormant)/탈퇴(withdrawn) 계정 로그인 차단 로직 추가
- 2026-02-23 (김지우): 휴면 계정 해제 API 추가
- 2026-02-23 (김지우): 마이페이지 연동을 위해 TokenResponse에 email, tier 추가 및 회원 탈퇴(/withdraw) API 추가
- 2026-02-23 (김지우): 프로필 사진 업로드(/profile-image) API 추가
"""

import os
import shutil  # 파일 저장을 위해 추가
import uuid    # 랜덤 파일명 생성을 위해 추가
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from fastapi import APIRouter, Depends, HTTPException, Request, Response, Header, UploadFile, File # UploadFile, File 추가
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from pydantic import BaseModel

# --- 백엔드 모듈 임포트 ---
from backend.db.session import get_db
from backend.schemas.auth_schema import (
    SignupRequest, LoginRequest, TokenResponse, MeResponse,
    ResetEmailRequest, ResetPasswordRequest
)
from backend.services import auth_service
from backend.core.config import settings
from backend.core.security import new_csrf_token
from backend.models.user import User
from backend.core.rate_limit import check_block, record_failure, reset_attempts

load_dotenv(override=True)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-aiwork-key-2026")

router = APIRouter(prefix="/api/auth", tags=["auth"])


# ==========================================
# 🛠️ 쿠키 및 CSRF 보조 함수 (기존 로직 유지)
# ==========================================
def set_auth_cookies(res: Response, refresh_token: str, csrf_token: str) -> None:
    res.set_cookie(
        key=settings.REFRESH_COOKIE_NAME,
        value=refresh_token,
        httponly=True,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/api/auth",
    )
    res.set_cookie(
        key=settings.CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=settings.COOKIE_SECURE,
        samesite=settings.COOKIE_SAMESITE,
        domain=settings.COOKIE_DOMAIN,
        path="/api/auth",
    )

def clear_auth_cookies(res: Response) -> None:
    res.delete_cookie(settings.REFRESH_COOKIE_NAME, path="/api/auth", domain=settings.COOKIE_DOMAIN)
    res.delete_cookie(settings.CSRF_COOKIE_NAME, path="/api/auth", domain=settings.COOKIE_DOMAIN)

def require_csrf(req: Request) -> None:
    cookie = req.cookies.get(settings.CSRF_COOKIE_NAME)
    header = req.headers.get("X-CSRF-Token")
    if (not cookie) or (not header) or (cookie != header):
        raise HTTPException(status_code=403, detail="CSRF 에러: 올바르지 않은 접근입니다.")

def get_current_user(req: Request, db: Session) -> User:
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="unauthorized")
    token = auth.split(" ", 1)[1].strip()
    try:
        return auth_service.get_user_from_access(db, token)
    except Exception:
        raise HTTPException(status_code=401, detail="unauthorized")


# ==========================================
# 🛑 기본 계정 API: 회원가입, 로그인, 로그아웃
# ==========================================
@router.post("/signup")
def signup(req: SignupRequest, db: Session = Depends(get_db)):
    try:
        auth_service.signup(db, req.email, req.password)
        return {"ok": True}
    except ValueError:
        raise HTTPException(status_code=400, detail="유효하지 않은 요청입니다.")

@router.post("/login", response_model=TokenResponse)
def login(req: LoginRequest, request: Request, res: Response, db: Session = Depends(get_db)):
    ip = request.client.host  

    # 🔒 차단 확인
    try:
        check_block(ip)
    except Exception:
        raise HTTPException(status_code=429, detail="시도 횟수가 너무 많습니다. 잠시 후 다시 시도해주세요.")

    # 1. 비밀번호 검증 (성공 시 access 토큰 반환)
    try:
        access, refresh, user_id = auth_service.login(db, req.email, req.password)
        reset_attempts(ip)
    except ValueError:
        record_failure(ip)
        raise HTTPException(status_code=401, detail="아이디 또는 비밀번호가 일치하지 않습니다.")

    # 2. 유저 정보 조회
    user_obj = db.query(User).filter(User.id == int(user_id)).first()
    
    # 🔥 3. [추가된 로직] 비밀번호는 맞았지만, 계정 상태(status)가 휴면/탈퇴인지 검사!
    if user_obj:
        user_status = getattr(user_obj, "status", "active")
        if user_status == "withdrawn":
            raise HTTPException(status_code=403, detail="탈퇴 처리된 계정입니다.")
        elif user_status == "dormant":
            raise HTTPException(status_code=403, detail="장기 미접속으로 휴면 전환된 계정입니다.")

    # 4. 상태가 정상(active)인 경우에만 쿠키 세팅 및 로그인 성공 처리
    csrf = new_csrf_token()
    set_auth_cookies(res, refresh, csrf)

    # 🔥 마이페이지용 데이터를 DB에서 안전하게 가져오기
    user_name = (user_obj.name or req.email.split("@")[0]) if user_obj else req.email.split("@")[0]
    user_role = getattr(user_obj, "role", "user") if user_obj else "user"
    user_profile_image_url = getattr(user_obj, "profile_image_url", None) if user_obj else None
    user_email = getattr(user_obj, "email", req.email) if user_obj else req.email
    user_tier = getattr(user_obj, "tier", "normal") if user_obj else "normal"

    return {
        "access_token": access,
        "token_type": "bearer",
        "name": user_name,
        "role": user_role,
        "profile_image_url": user_profile_image_url,
        "email": user_email, # 👈 프론트엔드로 전달!
        "tier": user_tier,   # 👈 프론트엔드로 전달!
    }

@router.post("/logout")
def logout(req: Request, res: Response, db: Session = Depends(get_db)):
    require_csrf(req)
    refresh_token = req.cookies.get(settings.REFRESH_COOKIE_NAME)
    if refresh_token:
        auth_service.revoke_refresh(db, refresh_token)
    clear_auth_cookies(res)
    return {"ok": True}

@router.post("/refresh", response_model=TokenResponse)
def refresh(req: Request, res: Response, db: Session = Depends(get_db)):
    require_csrf(req)
    refresh_token = req.cookies.get(settings.REFRESH_COOKIE_NAME)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")

    try:
        new_access, new_refresh = auth_service.rotate_refresh(db, refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")

    csrf = new_csrf_token()
    set_auth_cookies(res, refresh_token=new_refresh, csrf_token=csrf)
    return {"access_token": new_access, "token_type": "bearer"}

@router.get("/me", response_model=MeResponse)
def me(req: Request, db: Session = Depends(get_db)):
    user = get_current_user(req, db)
    return {"id": user.id, "email": user.email, "name": user.name}


# ==========================================
# 🛑 프론트엔드용 API: 토큰 검증, 비밀번호 찾기
# ==========================================

@router.get("/verify")
def verify_token(authorization: str = Header(None), db: Session = Depends(get_db)):
    """프론트엔드(home.py)가 화면 이동 시 토큰의 만료 여부를 묻는 API"""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="토큰이 없습니다.")

    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id = payload.get("sub")

        # DB에서 실제 이름과 권한 조회
        user_obj = db.query(User).filter(User.id == int(user_id)).first() if user_id else None
        if not user_obj:
            raise HTTPException(status_code=401, detail="유효하지 않은 인증 정보입니다.")

        user_name = user_obj.name or user_obj.email.split("@")[0]
        user_role = getattr(user_obj, "role", "user")

        return {
            "name": user_name,
            "role": user_role,
            "profile_image_url": getattr(user_obj, "profile_image_url", None),
            "email": getattr(user_obj, "email", payload.get("email", "")),
            "tier": getattr(user_obj, "tier", "normal")
        }

    except ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="30분 동안 활동이 없어 자동 로그아웃 되었습니다.")
    except JWTError:
        raise HTTPException(status_code=401, detail="유효하지 않은 인증 정보입니다.")


@router.post("/send-reset-email")
def api_send_reset_email(req: ResetEmailRequest, db: Session = Depends(get_db)):
    """이메일 발송 API"""
    if not auth_service.check_user_exists(db, req.email):
        raise HTTPException(status_code=404, detail="가입되지 않은 이메일입니다. 아이디를 다시 확인해주세요.")
    
    is_sent, error_msg = auth_service.send_auth_email(req.email, req.auth_code)
    
    if not is_sent:
        raise HTTPException(status_code=500, detail=error_msg)
        
    return {"message": "인증번호 발송 성공"}


@router.post("/reset-password")
def api_reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """비밀번호 재설정 API"""
    success, error_msg = auth_service.update_password(db, req.email, req.new_password)
    
    if not success:
        raise HTTPException(status_code=500, detail=error_msg)
        
    return {"message": "비밀번호가 성공적으로 변경되었습니다."}


class UnlockRequest(BaseModel):
    email: str

@router.post("/unlock")
def unlock_dormant(req: UnlockRequest, db: Session = Depends(get_db)):
    """휴면 계정을 다시 활성화(active) 시키는 API"""
    user = db.query(User).filter(User.email == req.email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    if getattr(user, "status", "active") != "dormant":
        raise HTTPException(status_code=400, detail="휴면 상태인 계정이 아닙니다.")
    
    # 상태를 다시 활성화로 변경!
    user.status = "active"
    db.commit()
    
    return {"detail": "휴면 해제 완료"}

class WithdrawRequest(BaseModel):
    email: str

@router.post("/withdraw")
def api_withdraw(req: WithdrawRequest, db: Session = Depends(get_db)):
    """회원 탈퇴 API"""
    user = db.query(User).filter(User.email == req.email).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")
    
    user.status = "withdrawn"
    db.commit()
    
    return {"detail": "회원 탈퇴가 완료되었습니다."}


# ==========================================
# 📷 프로필 사진 업로드 API (김지우 추가)
# ==========================================
@router.post("/profile-image")
def upload_profile_image(
    req: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    # 1. 토큰으로 현재 요청한 유저 확인
    user = get_current_user(req, db)
    if not user:
        raise HTTPException(status_code=401, detail="로그인이 필요합니다.")

    # 2. 백엔드 프로젝트 최상단에 폴더 생성 (없으면 자동 생성)
    UPLOAD_DIR = "static/profiles"
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 3. 기존 파일명에서 확장자를 추출하고 고유한 새 이름 만들기
    ext = file.filename.split(".")[-1]
    new_filename = f"user_{user.id}_{uuid.uuid4().hex[:8]}.{ext}"
    file_path = os.path.join(UPLOAD_DIR, new_filename)

    # 4. 서버 폴더에 파일 저장
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # 5. DB 업데이트 및 프론트로 경로 반환
    # 프론트가 브라우저에서 읽을 수 있는 도메인 주소로 저장
    image_url = f"http://127.0.0.1:8000/static/profiles/{new_filename}"
    
    user.profile_image_url = image_url
    db.commit()

    return {"profile_image_url": image_url}