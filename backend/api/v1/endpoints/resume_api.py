from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.db.session import get_db  # 프로젝트에 맞게 경로 수정
from backend.services.resume_service import get_latest_resume_fields

router = APIRouter(prefix="/resumes", tags=["resumes"])

@router.get("/latest")
def read_latest_resume(
    user_id: str = Query(..., description="user_resumes.user_id"),
    db: Session = Depends(get_db),
):
    job_role, analysis_result = get_latest_resume_fields(db, user_id)

    if job_role is None and analysis_result is None:
        raise HTTPException(status_code=404, detail="해당 유저의 이력서가 없습니다.")

    return {
        "user_id": user_id,
        "job_role": job_role,
        "analysis_result": analysis_result,
    }