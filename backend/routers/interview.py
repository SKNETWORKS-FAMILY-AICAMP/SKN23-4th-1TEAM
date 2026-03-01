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
