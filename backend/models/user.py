"""
File: user.py
Author: 양창일
Created: 2026-02-15
Description: 사용자 정보를 저장하는 구조

Modification History:
- 2026-02-15: 초기 생성
- 2026-02-23: profile_image_url 컬럼 추가
- 2026-03-23: github_url 컬럼 추가 및 프로필 디폴트 지정
"""
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from backend.db.base import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    
    profile_image_url: Mapped[str | None] = mapped_column(String(512), default="/images/default-profile.png", nullable=True)
    
    password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    provider_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    role: Mapped[str] = mapped_column(String(20), default="user")
    tier: Mapped[str] = mapped_column(String(20), default="normal")
    status: Mapped[str] = mapped_column(String(20), default="active")
    github_url: Mapped[str | None] = mapped_column(String(512), nullable=True)