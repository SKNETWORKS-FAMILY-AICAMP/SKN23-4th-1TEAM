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

from pydantic import BaseModel, Field  
from typing import Optional


class SignupRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)  
    password: str = Field(min_length=8, max_length=128)  

class LoginRequest(BaseModel):
    email: str  
    password: str  

class TokenResponse(BaseModel):
    access_token: str          
    token_type: str = "bearer"  
    id: int                     
    name: str | None = None    
    role: str | None = None     
    profile_image_url: str | None = None
    email: str | None = None    
    tier: str | None = None     

class MeResponse(BaseModel):
    id: int  
    email: str 
    name: str | None = None 

# 추가 부분 (김지우)
class ResetEmailRequest(BaseModel):
    email: str
    auth_code: str

class ResetPasswordRequest(BaseModel):
    email: str
    new_password: str