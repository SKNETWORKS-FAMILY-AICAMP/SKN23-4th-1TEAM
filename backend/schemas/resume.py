# 가이드 챗봇에 사용됨.

from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

# 이력서 응답용 스키마 
class ResumeResponse(BaseModel):
    id: int
    user_id: int
    title: str
    job_role: Optional[str] = None
    resume_text: Optional[str] = None 
    analysis_result: Optional[Any] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True  