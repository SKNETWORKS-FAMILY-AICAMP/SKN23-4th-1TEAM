"""
File: session.py
Author: 양창일
Created: 2026-02-15
Description: 데이터베이스 연결 및 세션 관리 (Base 정의 포함 통합본)

Modification History:
- 2026-02-15 (양창일): 초기 생성
- 2026-02-22 (김지우): Base 정의 추가 및 SQLAlchemy 임포트 에러 수정
"""
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.core.config import settings  # 기존 설정 파일 유지

# 엔진 설정
if not settings.DATABASE_URL:
    raise ValueError("DATABASE_URL is required")

connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(settings.DATABASE_URL, connect_args=connect_args, future=True)

# 세션 팩토리 설정
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

# 선언적 베이스 클래스 정의
Base = declarative_base()

# Dependency Injection용 DB 세션 함수
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
