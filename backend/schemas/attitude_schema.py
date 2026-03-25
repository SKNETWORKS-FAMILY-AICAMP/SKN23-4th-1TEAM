"""
File: attitude_schema.py
Author: 양창일
Created: 2026-02-28
Description: AI 요청과 응답 데이터 모양 정의

Modification History:
- 2026-02-28 (양창일): 초기 생성
"""

from pydantic import BaseModel      # FastAPI에서 request/response 데이터 구조를 정의하기 위한 기본 클래스
from typing import List, Optional, Dict, Any  # 타입 힌트를 위한 모듈

class FrameIn(BaseModel):           # 프론트(JS)에서 보내는 "프레임 1개" 데이터 구조
    t_ms: int                       # 해당 프레임의 시간 (ms) → start 버튼 기준 경과 시간
    image_b64: str                  # 프레임 이미지(base64 문자열)

class AttitudeRequest(BaseModel):   # 프론트가 보내는 전체 요청 구조
    frames: List[FrameIn]           # 프레임 리스트 (start~stop 사이 수집된 것들)

class AttitudeMetrics(BaseModel):   # 계산된 태도 지표 결과
    head_center_ratio: float        # 정면 유지 비율
    downward_ratio: float           # 고개 숙임 비율
    expression_variability: float   # 표정 변화량
    eye_open_variability: float     # 눈 깜빡임/긴장 변화량

class AttitudeEvent(BaseModel):     # "문제 행동 구간" 이벤트
    t_start_ms: int                 # 문제 시작 시점
    t_end_ms: int                   # 문제 종료 시점
    type: str                       # 이벤트 종류 (예: 정면 이탈, 고개 하방 등)
    severity: str = "info"          # 심각도 (info / warn)
    detail: Optional[str] = None    # 추가 설명 (선택)

class AttitudeResponse(BaseModel):  # 백엔드 → 프론트로 보내는 최종 결과
    metrics: AttitudeMetrics        # 계산된 태도 지표
    events: List[AttitudeEvent]     # 감지된 문제 구간 리스트
    summary_text: str               # LLM에 넘길 요약 문장
    debug: Optional[Dict[str, Any]] = None  # 디버깅용 추가 데이터 (선택)