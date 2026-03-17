"""
File: jobs.py
Author: 유헌상
Created: 2026-02-23
Description: 워크넷 외부 API 호출 API 주소

Modification History:
- 2026-02-23: 초기 생성
"""
from fastapi import APIRouter, HTTPException
import httpx

from backend.schemas.jobs_schema import JobsSearchQuery, JobsSearchResponse
from backend.core.config import settings
from backend.services.jobs_service import parse_jobs_xml, _join_multi  # 이 2개만 재사용

router = APIRouter(prefix="/jobs", tags=["jobs"])

@router.post("/search", response_model=JobsSearchResponse)
async def search_jobs(body: JobsSearchQuery):
    # 외부 API 필수 파라미터
    params: dict[str, str | int] = {
        "authKey": settings.WORKNET_API_KEY,
        "callTp": "L",
        "returnType": "xml",
        "startPage": body.startPage,
        "display": body.display,
    }

    # 선택 파라미터
    if body.empCoNo:
        params["empCoNo"] = body.empCoNo
    if body.jobsCd:
        params["jobsCd"] = body.jobsCd
    if body.empWantedTitle:
        params["empWantedTitle"] = body.empWantedTitle
    if body.sortField:
        params["sortField"] = body.sortField
    if body.sortOrderBy:
        params["sortOrderBy"] = body.sortOrderBy


    # 다중 파라미터(list -> string)
    v = _join_multi(body.coClcd)
    if v:
        params["coClcd"] = v
    v = _join_multi(body.empWantedTypeCd)
    if v:
        params["empWantedTypeCd"] = v
    v = _join_multi(body.empWantedCareerCd)
    if v:
        params["empWantedCareerCd"] = v
    v = _join_multi(body.empWantedEduCd)
    if v:
        params["empWantedEduCd"] = v

    # 호출
    if not settings.WORKNET_URL_BASE:
        raise HTTPException(status_code=500, detail="WORKNET_URL_BASE이 비어있습니다.")

    url = f"{settings.WORKNET_URL_BASE}"

    try:
        async with httpx.AsyncClient(timeout=settings.WORKNET_TIMEOUT_SEC, follow_redirects=True) as client:
            res = await client.get(url, params=params)
            res.raise_for_status()
            return parse_jobs_xml(res.text)
    except httpx.TimeoutException:
        raise HTTPException(status_code=502, detail="외부 채용 API 호출 시간 초과")
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=502, detail=f"외부 채용 API 호출 실패: {e.response.status_code}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Server error: {type(e).__name__}: {e}")