"""
File: security.py
Author: 양창일
Created: 2026-02-15
Description: 암호 만들고 토큰 만들고 검사하는 보안 도구 모음

Modification History:
- 2026-02-15: 초기 생성
- 2026-02-22 (양창일) : 비밀번호 hash 72자리로 끊기
- 2026-03-12 (김지우) : Bcrypt 72바이트(Null 포함) 버그 해결을 위해 50자리로 제한
"""

import hashlib  
import secrets  
from datetime import datetime, timedelta, timezone  
from jose import jwt  
from passlib.context import CryptContext  
from backend.core.config import settings  

pwd_context = CryptContext(schemes=["bcrypt", "argon2"], deprecated="auto")

def hash_password(password: str) -> str:
    import bcrypt as _bcrypt
    safe_password = password[:50].encode('utf-8')
    salt = _bcrypt.gensalt()
    return _bcrypt.hashpw(safe_password, salt).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    safe_password = password[:50]
    if password_hash and password_hash.startswith(("$2b$", "$2a$", "$2y$")):
        import bcrypt as _bcrypt
        return _bcrypt.checkpw(safe_password.encode("utf-8"), password_hash.encode("utf-8"))
    return pwd_context.verify(safe_password, password_hash)

def new_jti() -> str:
    return secrets.token_hex(16)  

def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)  

def sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()  

def create_access_token(sub: str) -> str:
    now = datetime.now(timezone.utc)  
    exp = now + timedelta(minutes=settings.ACCESS_TOKEN_MINUTES)  
    payload = {"sub": sub, "iat": int(now.timestamp()), "exp": exp}  
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)  

def create_refresh_token(sub: str, jti: str) -> str:
    now = datetime.now(timezone.utc)  
    exp = now + timedelta(days=settings.REFRESH_TOKEN_DAYS)  
    payload = {"sub": sub, "jti": jti, "iat": int(now.timestamp()), "exp": exp}  
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)  

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])