"""
File: routers/agent.py
Author: 김지우
Created: 2026-03-10
Description: AI 에이전트 라우터

Modification History:
- 2026-03-10 (김지우): 초기 생성
"""

from fastapi import APIRouter, HTTPException
from backend.schemas.agent_schema import AgentChatRequest
from backend.ai.agent import run_agent

router = APIRouter()

@router.post("/chat")
async def chat_with_agent(request: AgentChatRequest):
    """
    프론트엔드에서 사용자의 채팅 메시지를 받아 자비스 에이전트에게 전달하고,
    에이전트가 결정한 프론트엔드 제어 명령(JSON)을 반환합니다.
    """
    try:
        # 1. 에이전트 호출
        result = run_agent(request.message)
        
        # 2. 결과 반환 (action, target_page, session_params, message 포함)
        return result
        
    except Exception as e:
        print(f"[Agent Router Error] {e}")
        raise HTTPException(status_code=500, detail="에이전트 처리 중 서버 오류가 발생했습니다.")