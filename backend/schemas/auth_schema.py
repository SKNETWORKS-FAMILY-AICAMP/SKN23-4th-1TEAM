"""
File: auth_schema.py
Author: 양창일
Created: 2026-02-15
Description: 로그인 관련 데이터 모양 정의

Modification History:
- 2026-02-15: 초기 생성
- 2026-02-21 (김지우): email 추가, 비밀번호 찾기 관련 스키마 추가
- 2026-02-22 (양창일): username 혼동으로 email, name으로 정리, 소셜 로그인 수정
- 2026-02-23 (양창일): profile_image_url 추가
- 2026-02-23 (김지우): 마이페이지 연동을 위해 TokenResponse에 email, tier 속성 추가
"""

from pydantic import BaseModel, Field  # 스키마

class SignupRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)  # 유저 Email
    password: str = Field(min_length=8, max_length=128)  # 비번

class LoginRequest(BaseModel):
    email: str  # 이메일(아이디)
    password: str  # 비번

class TokenResponse(BaseModel):
    access_token: str           # 액세스 토큰
    token_type: str = "bearer"  # 타입
    name: str | None = None     # 유저 이름 (프론트 표시용)
    role: str | None = None     # 권한 (user / admin)
    profile_image_url: str | None = None
    
    # 🔥 마이페이지(profile.py) 데이터 바인딩을 위해 추가된 부분!
    email: str | None = None    # 유저 이메일
    tier: str | None = None     # 유저 등급 (normal / plus)

class MeResponse(BaseModel):
    id: int  # 유저 ID
    email: str # 유저 Email
    name: str | None = None # 유저명

# 추가 부분 (김지우)
class ResetEmailRequest(BaseModel):
    email: str
    auth_code: str

class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str