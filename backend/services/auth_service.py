"""
File: auth_service.py
Author: 양창일, 김지우
Created: 2026-02-15
Description: 로그인, 토큰 처리 및 비밀번호 재설정 로직

Modification History:
- 2026-02-15 (양창일): 초기 생성 (로그인, JWT 토큰 관리 로직)
- 2026-02-21 (김지우): 비밀번호 찾기 (이메일 인증, 비밀번호 업데이트) SQLAlchemy 통합
- 2026-02-22 (양창일): username 혼동으로 email, name으로 정리, 소셜 로그인 수정
"""

import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from dotenv import load_dotenv

# --- 기존 백엔드 모델 및 보안 유틸 임포트 ---
from backend.models.user import User
from backend.models.refresh_token import RefreshToken
from backend.core.security import (
    hash_password, verify_password, new_jti, sha256_hex,
    create_access_token, create_refresh_token, decode_token
)
from backend.core.config import settings

load_dotenv(override=True)

# 이메일 발송 환경변수
SENDER_EMAIL = os.getenv("SENDER_EMAIL")
APP_PASSWORD = os.getenv("APP_PASSWORD")



def signup(db: Session, email: str, password: str, name: str | None = None) -> None:
    exists = db.query(User).filter(User.email == email).first()
    if exists:
        raise ValueError("invalid credentials")
    user = User(email=email, name=name, password=hash_password(password))
    db.add(user)
    db.commit()

def login(db: Session, email: str, password: str) -> tuple[str, str, str]:
    user = db.query(User).filter(User.email == email).first()

    if (not user) or (not user.password) or (not verify_password(password, user.password)):
        raise ValueError("invalid credentials")  

    access = create_access_token(sub=str(user.id))  
    jti = new_jti()  
    refresh = create_refresh_token(sub=str(user.id), jti=jti)  

    exp = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_DAYS)  
    row = RefreshToken(user_id=user.id, jti=jti, token_hash=sha256_hex(refresh), expires_at=exp)  
    db.add(row)  
    db.commit()  

    return access, refresh, str(user.id)  


def rotate_refresh(db: Session, refresh_token: str) -> tuple[str, str]:
    payload = decode_token(refresh_token)  
    user_id = int(payload.get("sub"))  
    jti = payload.get("jti")  
    if not jti:
        raise ValueError("invalid token")  

    row = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()  
    if (not row) or (row.revoked_at is not None):  
        raise ValueError("invalid token")  
    if row.token_hash != sha256_hex(refresh_token):  
        raise ValueError("invalid token")  
    if row.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):  
        raise ValueError("invalid token")  

    row.revoked_at = datetime.now(timezone.utc)  
    db.add(row)  

    new_access = create_access_token(sub=str(user_id))  
    new_jti = new_jti()  
    new_refresh = create_refresh_token(sub=str(user_id), jti=new_jti)  

    exp = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_DAYS)  
    db.add(RefreshToken(user_id=user_id, jti=new_jti, token_hash=sha256_hex(new_refresh), expires_at=exp))  
    db.commit()  

    return new_access, new_refresh  

def revoke_refresh(db: Session, refresh_token: str) -> None:
    try:
        payload = decode_token(refresh_token)  
        jti = payload.get("jti")  
    except Exception:
        return  

    if not jti:
        return  

    row = db.query(RefreshToken).filter(RefreshToken.jti == jti).first()  
    if row and row.revoked_at is None:
        row.revoked_at = datetime.now(timezone.utc)  
        db.add(row)  
        db.commit()  

def get_user_from_access(db: Session, access_token: str) -> User:
    payload = decode_token(access_token)  
    sub = payload.get("sub")  
    if not sub:
        raise ValueError("invalid token")  
    user = db.query(User).filter(User.id == int(sub)).first()  
    if not user:
        raise ValueError("invalid token")  
    return user  

def issue_tokens_for_user_id(db: Session, user_id: int) -> tuple[str, str]:
    access = create_access_token(sub=str(user_id))  
    jti = new_jti()  
    refresh = create_refresh_token(sub=str(user_id), jti=jti)  

    exp = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_DAYS)  
    row = RefreshToken(user_id=user_id, jti=jti, token_hash=sha256_hex(refresh), expires_at=exp)  
    db.add(row)  
    db.commit()  

    return access, refresh  



def check_user_exists(db: Session, email: str) -> bool:
    """이메일 기반 유저 존재 여부 확인"""
    user = db.query(User).filter(User.email == email).first()
    return user is not None

def send_auth_email(receiver_email: str, auth_code: str) -> tuple[bool, str]:
    """SMTP 기반 인증 이메일 발송"""
    if not SENDER_EMAIL or not APP_PASSWORD:
        return False, "서버의 이메일 설정이 누락되었습니다."
        
    subject = "[보안] 비밀번호 재설정 인증 코드 안내"
    body = f"""
    <html>
    <body style="font-family: 'Malgun Gothic', sans-serif; line-height: 1.6; color: #333; max-width: 500px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #222;">코드를 입력하고 비밀번호를 재설정하세요</h2>
        <div style="background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 8px; padding: 20px; text-align: center; margin: 24px 0;">
            <h1 style="color: #bb38d0; letter-spacing: 8px; margin: 0; font-size: 32px;">{auth_code}</h1>
        </div>
        <p style="font-size: 14px; color: #555;">화면에 위 코드를 입력하세요. 코드는 15분 뒤 만료됩니다.</p>
    </body>
    </html>
    """
    
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'html'))
    
    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SENDER_EMAIL, APP_PASSWORD)
        server.sendmail(SENDER_EMAIL, receiver_email, msg.as_string())
        server.quit()
        return True, "성공"
    except Exception as e:
        return False, f"이메일 발송 실패: {str(e)}"

def update_password(db: Session, email: str, new_raw_password: str) -> tuple[bool, str]:
    """새로운 비밀번호를 암호화하여 DB 업데이트 (ORM 활용)"""
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            return False, "가입되지 않은 이메일입니다."

        user.password = hash_password(new_raw_password)
        db.commit()
        return True, "성공"
    except Exception as e:
        db.rollback()
        return False, f"비밀번호 업데이트 오류: {str(e)}"
