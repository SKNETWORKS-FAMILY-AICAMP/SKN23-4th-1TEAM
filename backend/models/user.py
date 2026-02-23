"""
File: user.py
Author: 양창일
Created: 2026-02-15
Description: 사용자 정보를 저장하는 구조

Modification History:
- 2026-02-15: 초기 생성
- 2026-02-23: profile_image_url 컬럼 추가
"""

from sqlalchemy import String, Integer, DateTime  # 컬럼 타입
from sqlalchemy.orm import Mapped, mapped_column  # 매핑
from backend.db.base import Base  # 베이스

class User(Base):
    __tablename__ = "users"  # 테이블명

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    profile_image_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)  # 비번 해시(소셜은 None)
    provider: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)  # kakao/google/naver
    provider_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)  # 제공자 고유 ID
    role: Mapped[str] = mapped_column(String(20), default="user")  # user/admin 관리자용 
