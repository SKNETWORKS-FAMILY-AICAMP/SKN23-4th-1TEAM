from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from backend.db.session import get_db
from backend.services.resume_service import get_latest_resume_fields
from backend.services.llm_service import analyze_resume_comprehensive
from backend.db.database import save_user_resume, get_user_resumes, delete_user_resume

router = APIRouter(prefix="/resumes", tags=["resumes"])


class ResumeCreateRequest(BaseModel):
    user_id: int
    title: str
    job_role: str
    resume_text: str


@router.get("/latest")
def read_latest_resume(
    user_id: int = Query(..., description="user_resumes.user_id"),
    db: Session = Depends(get_db),
):
    # user_id가 0이거나 유효하지 않은 경우 early return
    if not user_id or user_id <= 0:
        return {"user_id": user_id, "job_role": None, "analysis_result": None}

    job_role, analysis_result = get_latest_resume_fields(db, str(user_id))

    if job_role is None and analysis_result is None:
        # 404를 내보내면 프론트엔드에서 에러로 잡히므로, 데이터가 없는 상태로 반환
        return {
            "user_id": user_id,
            "job_role": None,
            "analysis_result": None,
        }

    return {
        "user_id": user_id,
        "job_role": job_role,
        "analysis_result": analysis_result,
    }


@router.get("")
def read_resumes(user_id: int = Query(..., description="users.id")):
    return {"items": get_user_resumes(user_id)}


@router.post("")
def create_resume(req: ResumeCreateRequest):
    analysis_result = analyze_resume_comprehensive(req.resume_text, req.job_role)
    resume_id = save_user_resume(
        user_id=req.user_id,
        title=req.title,
        job_role=req.job_role,
        resume_text=req.resume_text,
        analysis_result=analysis_result,
    )
    return {"id": resume_id, "analysis_result": analysis_result}


@router.delete("/{resume_id}")
def remove_resume(resume_id: int):
    delete_user_resume(resume_id)
    return {"ok": True}

