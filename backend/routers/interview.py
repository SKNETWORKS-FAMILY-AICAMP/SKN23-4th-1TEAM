"""
File: routers/interview.py
Author: 김지우
Created: 2026-03-01
Description: 면접 세션 CRUD 및 AI/RAG 처리 라우터 통합본
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from backend.db.session import get_db
from backend.routers.auth import get_current_user
from backend.db.database import get_connection

# 프론트엔드에서 분리해낸 AI/RAG 서비스 함수 임포트
from backend.services.llm_service import analyze_resume_comprehensive, generate_evaluation, evaluate_and_respond
from backend.services.rag_service import store_resume

router = APIRouter(prefix="/api/interview", tags=["Interview"])


@router.delete("/sessions/{session_id}")
async def delete_interview_session(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    current_user = get_current_user(request, db)
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM interview_sessions WHERE id=%s AND user_id=%s",
                (session_id, current_user.id)
            )
            session = cur.fetchone()
            
            if not session:
                raise HTTPException(status_code=404, detail="세션을 찾을 수 없거나 삭제 권한이 없습니다.")
            
            cur.execute("DELETE FROM interview_details WHERE session_id=%s", (session_id,))
            cur.execute("DELETE FROM interview_sessions WHERE id=%s", (session_id,))

    return {"message": "삭제 완료", "session_id": session_id}

@router.post("/details")
async def save_interview_detail(
    body: dict,
    db: Session = Depends(get_db)
):
    from backend.db.base import InterviewDetail
    session_id = body.get("session_id")
    if not session_id:
        raise HTTPException(status_code=400, detail="session_id is required")

    new_detail = InterviewDetail(
        session_id=session_id,
        turn_index=body.get("turn_index", 0),
        question=body.get("question", ""),
        answer=body.get("answer", ""),
        response_time=body.get("response_time", 0),
        score=body.get("score", 0.0),
        sentiment_score=body.get("sentiment_score", 0.0),
        feedback=body.get("feedback", ""),
        is_followup=body.get("is_followup", False)
    )
    db.add(new_detail)
    db.commit()
    return {"message": "상세 기록 저장 완료"}

@router.put("/sessions/{session_id}")
async def update_interview_session(
    session_id: int,
    body: dict,
    db: Session = Depends(get_db)
):
    from backend.db.base import InterviewDetail, InterviewSession
    session_record = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session_record:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    if "total_score" in body:
        session_record.total_score = body["total_score"]
    if "status" in body:
        session_record.status = body["status"]
        if body["status"] == "COMPLETED":
            if "total_score" not in body:
                from sqlalchemy import func

                avg_score = (
                    db.query(func.avg(InterviewDetail.score))
                    .filter(
                        InterviewDetail.session_id == session_id,
                        InterviewDetail.score.isnot(None),
                    )
                    .scalar()
                )
                if avg_score is not None:
                    session_record.total_score = round(float(avg_score), 2)
            from sqlalchemy.sql import func
            session_record.ended_at = func.now()
    
    db.commit()
    return {"message": "세션 업데이트 완료"}


class AnalyzeResumeRequest(BaseModel):
    resume_text: str
    job_role: str

class StoreResumeRequest(BaseModel):
    resume_text: str
    user_id: str

class EvaluateInterviewRequest(BaseModel):
    messages: List[Dict[str, Any]]
    job_role: str
    difficulty: str
    resume_text: Optional[str] = None

@router.post("/analyze-resume")
async def api_analyze_resume(req: AnalyzeResumeRequest):
    try:
        result = analyze_resume_comprehensive(req.resume_text, req.job_role)
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/store-resume")
async def api_store_resume(req: StoreResumeRequest):
    try:
        chunk_count = store_resume(req.resume_text, req.user_id)
        return {"status": "success", "chunk_count": chunk_count}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/evaluate")
async def api_evaluate_interview(req: EvaluateInterviewRequest):
    try:
        result = generate_evaluation(req.messages, req.job_role, req.difficulty, req.resume_text)
        return {"status": "success", "evaluation": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class InterviewChatRequest(BaseModel):
    user_id: Optional[str] = "anonymous"
    job_role: Optional[str] = "개발자"
    difficulty: Optional[str] = "중"
    persona: Optional[str] = "깐깐한 기술팀장"
    resume_text: Optional[str] = None
    current_question: Optional[str] = "시작"
    user_answer: Optional[str] = ""
    next_main_question: Optional[str] = None
    followup_count: int = 0

@router.post("/chat")
async def api_interview_chat(req: InterviewChatRequest):
    print(f"[DEBUG] Received interview chat request: {req.dict()}")
    """
    프론트엔드에서 유저의 답변을 받아,
    RAG(이력서) 검색과 LLM 평가를 거쳐 피드백 및 다음 질문(또는 꼬리질문)을 반환합니다.
    """
    try:
        result = evaluate_and_respond(
            question=req.current_question,
            answer=req.user_answer,
            job_role=req.job_role or "개발자",
            difficulty=req.difficulty or "중",
            persona_style=req.persona or "깐깐한 기술팀장",  # None-safe 기본값
            user_id=str(req.user_id),                        # str 강제 변환
            resume_text=req.resume_text,
            next_main_question=req.next_main_question,
            followup_count=req.followup_count,
        )
        return {"status": "success", "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
