from sqlalchemy import JSON, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from backend.db.session import Base


class JobCategory(Base):
    __tablename__ = "job_categories"

    id = Column(Integer, primary_key=True, index=True)
    main_category = Column(String(50), nullable=True)
    sub_category = Column(String(50), nullable=True)
    target_role = Column(String(50), unique=True, nullable=True)

    questions = relationship("QuestionPool", back_populates="category")


class QuestionPool(Base):
    __tablename__ = "question_pool"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("job_categories.id", ondelete="SET NULL"), nullable=True)
    question_type = Column(String(30), nullable=True)
    skill_tag = Column(String(100), nullable=True)
    difficulty = Column(String(20), nullable=True)
    content = Column(Text, nullable=False)
    reference_answer = Column(Text, nullable=True)
    keywords = Column(String(255), nullable=True)

    category = relationship("JobCategory", back_populates="questions")


class UserResume(Base):
    __tablename__ = "user_resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title = Column(String(255), nullable=False)
    job_role = Column(String(100), nullable=True)
    resume_text = Column(Text, nullable=True)
    analysis_result = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    job_role = Column(String(100), nullable=True)
    difficulty = Column(String(20), nullable=True)
    persona = Column(String(50), nullable=True)
    total_score = Column(Float, nullable=True)
    status = Column(String(20), default="START")
    started_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)
    resume_used = Column(Boolean, default=False)
    resume_id = Column(Integer, ForeignKey("user_resumes.id", ondelete="SET NULL"), nullable=True)
    manual_tech_stack = Column(Text, nullable=True)

    details = relationship("InterviewDetail", back_populates="session", cascade="all, delete-orphan")


class InterviewDetail(Base):
    __tablename__ = "interview_details"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("interview_sessions.id", ondelete="CASCADE"), nullable=False)
    turn_index = Column(Integer, nullable=False, default=0)
    question = Column(Text, nullable=True)
    answer = Column(Text, nullable=True)
    is_followup = Column(Boolean, default=False)
    response_time = Column(Integer, nullable=True)
    score = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)
    sentiment_score = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    session = relationship("InterviewSession", back_populates="details")
