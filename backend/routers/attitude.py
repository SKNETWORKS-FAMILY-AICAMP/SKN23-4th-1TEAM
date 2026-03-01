"""
File: attitude.py
Author: 양창일
Created: 2026-02-28
Description: 화상면접 태도

Modification History:
- 2026-02-28 (양창일): 초기 생성
"""


from fastapi import APIRouter, HTTPException
from backend.schemas.attitude_schema import AttitudeRequest, AttitudeResponse, AttitudeMetrics, AttitudeEvent
from backend.services.attitude_service import analyze_attitude

router = APIRouter(prefix="/api/infer", tags=["attitude"])

@router.post("/attitude", response_model=AttitudeResponse)
def infer_attitude(req: AttitudeRequest):
    if not req.frames:
        raise HTTPException(status_code=400, detail="frames is empty")
    result = analyze_attitude([f.model_dump() for f in req.frames], fps=2.0)

    metrics = AttitudeMetrics(**result["metrics"])
    events = [AttitudeEvent(**e) for e in result["events"]]
    return AttitudeResponse(metrics=metrics, events=events, summary_text=result["summary_text"])