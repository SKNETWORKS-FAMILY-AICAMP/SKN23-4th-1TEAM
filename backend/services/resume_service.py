# backend/services/resume_service.py
import json
from typing import Optional, Tuple, Any, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text

def get_latest_resume_fields(
    db: Session,
    user_id: str,
) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
    """
    user_resumes에서 user_id 기준 최신 이력서 1건의 job_role, analysis_result만 가져온다.
    """
    q = text("""
        SELECT job_role, analysis_result
        FROM user_resumes
        WHERE user_id = :uid
        ORDER BY created_at DESC, id DESC
        LIMIT 1
    """)
    row = db.execute(q, {"uid": user_id}).fetchone()
    if not row:
        return None, None

    job_role = row[0]
    analysis_result = row[1]

    # analysis_result가 문자열로 오는 환경이면 dict로 변환
    if isinstance(analysis_result, str):
        try:
            analysis_result = json.loads(analysis_result)
        except Exception:
            analysis_result = None

    if not isinstance(analysis_result, dict):
        analysis_result = None

    return job_role, analysis_result