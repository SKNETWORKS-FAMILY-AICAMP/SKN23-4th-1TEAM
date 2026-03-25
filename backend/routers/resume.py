# 가이드 챗봇에 사용됨.
from fastapi import APIRouter, Depends
from typing import List
from schemas.resume import ResumeResponse # 방금 만든 스키마 불러오기

router = APIRouter()

# response_model에 방금 만든 스키마를 지정해 줍니다.
@router.get("/resumes", response_model=List[ResumeResponse])
def get_resume_list(user_id: int):
    # (database.py의 get_user_resumes 함수를 호출하는 로직)
    resumes = get_user_resumes(user_id)
    return resumes