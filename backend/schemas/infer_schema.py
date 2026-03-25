"""
File: infer_schema.py
Author: 양창일
Created: 2026-02-15
Description: AI 요청과 응답 데이터 모양 정의

Modification History:
- 2026-02-15: 초기 생성
"""

from pydantic import BaseModel  # 스키마

class InferRequest(BaseModel):
    prompt: str  # 입력

class InferResponse(BaseModel):
    result: str  # 출력
