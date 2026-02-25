"""
File: base.py
Author: 양창일
Created: 2026-02-15
Description: DB 모델들의 기본 뼈대

Modification History:
- 2026-02-15: 초기 생성
- 2026-02-22 (김지우) : 벡엔드 DB 모델 정의 - 기존 User 모델 외에 직무 분류, 질문 풀, 면접 기록 테이블 추가
"""

from sqlalchemy.orm import DeclarativeBase  # 베이스 클래스

class Base(DeclarativeBase):  # ORM 베이스
    pass  # 확장용


from sqlalchemy import Column, Integer, String, Text, ForeignKey, Float, DateTime
from sqlalchemy.orm import relationship
from backend.db.session import Base
from datetime import datetime