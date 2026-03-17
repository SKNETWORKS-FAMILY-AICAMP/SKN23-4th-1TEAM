"""
File: jobs_service.py
Author: 유헌상
Created: 2026-02-23
Description: 채용공고(워크넷) API 호출

Modification History:
- 2026-02-23 (유헌상): 초기 생성 (외부 채용공고 OpenAPI 호출)
"""

from fastapi import APIRouter, HTTPException
from backend.schemas.jobs_schema import JobsSearchQuery, JobsSearchResponse
from backend.services.jobs_service import (
    fetch_jobs,
    ExternalJobsAPIError,
    _join_multi,
)

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("/search", response_model=JobsSearchResponse)
async def search_jobs(body: JobsSearchQuery):
    # 외부 API에 보낼 파라미터 구성
    params = {
        "startPage": body.startPage,
        "display": body.display,
    }

    # optional
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

    # multi
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
    
    try:
        data = await fetch_jobs(params)
        return data
    except ExternalJobsAPIError as e:
        raise HTTPException(status_code=502, detail=str(e))