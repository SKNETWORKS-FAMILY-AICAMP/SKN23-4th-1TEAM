"""
File: routers/interview.py
Author: 김지우
Created: 2026-03-01
Description: 면접 기록 삭제 (PyMySQL 원시 SQL 적용 + 인증 호환성 패치)
"""
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from backend.db.session import get_db
from backend.routers.auth import get_current_user
from backend.db.database import get_connection

router = APIRouter(prefix="/api/interview", tags=["Interview"])

@router.delete("/sessions/{session_id}")
async def delete_interview_session(
    session_id: int,
    request: Request,
    db: Session = Depends(get_db)
):
    # 1. FastAPI 의존성 해결을 위해 함수 내부에서 토큰 검증 추출
    current_user = get_current_user(request, db)
    
    # 2. PyMySQL 컨텍스트 매니저를 통한 삭제 로직 실행
    with get_connection() as conn:
        with conn.cursor() as cur:
            # 본인 세션인지 확인
            cur.execute(
                "SELECT id FROM interview_sessions WHERE id=%s AND user_id=%s",
                (session_id, current_user.id)
            )
            session = cur.fetchone()
            
            if not session:
                raise HTTPException(status_code=404, detail="세션을 찾을 수 없거나 삭제 권한이 없습니다.")
            
            # 연관 상세 기록 삭제
            cur.execute(
                "DELETE FROM interview_details WHERE session_id=%s",
                (session_id,)
            )
            
            # 메인 세션 삭제
            cur.execute(
                "DELETE FROM interview_sessions WHERE id=%s",
                (session_id,)
            )

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
    from backend.db.base import InterviewSession
    session_record = db.query(InterviewSession).filter(InterviewSession.id == session_id).first()
    if not session_record:
        raise HTTPException(status_code=404, detail="세션을 찾을 수 없습니다.")

    if "total_score" in body:
        session_record.total_score = body["total_score"]
    if "status" in body:
        session_record.status = body["status"]
        if body["status"] == "COMPLETED":
            from sqlalchemy.sql import func
            session_record.ended_at = func.now()
    
    db.commit()
    return {"message": "세션 업데이트 완료"}
