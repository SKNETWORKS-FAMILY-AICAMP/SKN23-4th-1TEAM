"""
File: schemas/agent_schema.py
Author: 김지우
Created: 2026-03-10
Description: AI 에이전트 스키마

Modification History:
- 2026-03-10 (김지우): 초기 생성
"""

from pydantic import BaseModel
from typing import Optional

class AgentChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default_session"