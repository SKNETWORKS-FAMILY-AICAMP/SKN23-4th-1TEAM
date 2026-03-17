"""
File: refresh_token.py
Author: 양창일
Created: 2026-02-15
Description: 로그인 유지용 토큰을 저장하는 구조

Modification History:
- 2026-02-15: 초기 생성
"""

from sqlalchemy import String, Integer, DateTime, ForeignKey  # 타입
from sqlalchemy.orm import Mapped, mapped_column  # 매핑
from datetime import datetime  # 시간
from backend.db.base import Base  # 베이스

class RefreshToken(Base):
    __tablename__ = "refresh_tokens"  # 테이블명

    id: Mapped[int] = mapped_column(Integer, primary_key=True)  # PK
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), index=True, nullable=False)  # 소유자
    jti: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)  # 토큰 ID
    token_hash: Mapped[str] = mapped_column(String(256), nullable=False)  # 리프레시 토큰 해시
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)  # 만료
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)  # 폐기시각
