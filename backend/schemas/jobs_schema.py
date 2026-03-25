"""
File: jobs_schema.py
Author: 유헌상
Created: 2026-02-23
Description: 채용공고 스키마 정의

Modification History:
- 2026-02-22: 초기 생성
"""

from pydantic import BaseModel, Field  
from typing import List, Optional     

class JobsSearchQuery(BaseModel):
    # startPage: Number (필수, 기본값 1, 최대 1000)
    # - 외부 API에서 "검색 시작 위치(페이지)"를 의미
    # - ge=1: 1 이상만 허용
    # - le=1000: 1000 이하만 허용 (문서 스펙)
    startPage: int = Field(
        1,
        ge=1,
        le=1000,
        description="검색 시작 페이지(기본값 1, 최대 1000)"
    )

    # display: Number (필수, 기본값 10, 최대 100)
    # - 외부 API에서 "출력(반환) 건수"를 의미
    # - ge=1: 1 이상만 허용
    # - le=100: 100 이하만 허용 (문서 스펙)
    display: int = Field(
        10,
        ge=1,
        le=100,
        description="출력 건수(기본값 10, 최대 100)"
    )

    # empCoNo: String (선택)
    # - 특정 기업 공고
    empCoNo: Optional[str] = Field(
        None,
        description="채용기업번호(특정 기업 공고 필터)"
    )

    # coClcd: String (다중검색 가능, 선택)
    # - 문서 예: 10(대기업),20(공기업),30(공공기관),40(중견기업),50(외국계기업)
    coClcd: Optional[List[str]] = Field(
        None,
        description="기업구분 코드(다중). 예: ['10','40']"
    )

    # empWantedTypeCd: String (다중검색 가능, 선택)
    # - 예: 10(정규직),20(정규직전환),30(비정규직),40(기간제),50(시간선택제),60(기타)
    empWantedTypeCd: Optional[List[str]] = Field(
        None,
        description="고용형태 코드(다중). 예: ['10','40']"
    )

    # empWantedCareerCd: String (다중검색 가능, 선택)
    # - 경력 구분 코드 목록
    # - 예: 10(경력무관),20(경력),30(신입),40(인턴)
    empWantedCareerCd: Optional[List[str]] = Field(
        None,
        description="경력구분 코드(다중). 예: ['10','30']"
    )

    # jobsCd: String (선택)
    # - 직종코드(특정 직종만 필터)
    jobsCd: Optional[str] = Field(
        None,
        description="직종코드"
    )

    # empWantedTitle: String (선택)
    # - 채용제목
    empWantedTitle: Optional[str] = Field(
        None,
        description="채용제목(검색어)"
    )

    # empWantedEduCd: String (다중검색 가능, 선택)
    # - 예: 10(고졸),20(대졸2~3),30(대졸),40(석사),50(박사),99(학력무관)
    empWantedEduCd: Optional[List[str]] = Field(
        None,
        description="학력 코드(다중). 예: ['30','99']"
    )

    # sortField: String (선택)
    # - 문서 예: regDt(등록일), coNm(회사명)
    sortField: Optional[str] = Field(
        None,
        description="정렬 필드. 예: 'regDt' 또는 'coNm'"
    )

    # sortOrderBy: String (선택)
    # - 예: desc(기본), asc
    sortOrderBy: Optional[str] = Field(
        None,
        description="정렬 방향. 예: 'desc' 또는 'asc'"
    )

class JobItem(BaseModel):
    # empSeqno: String
    # - 공개채용공고순번(공고의 고유 ID 역할)
    empSeqno: Optional[str] = Field(
        None,
        description="공개채용공고순번(공고 고유 ID)"
    )

    # empWantedTitle: String
    empWantedTitle: Optional[str] = Field(
        None,
        description="채용제목"
    )

    # empBusiNm: String
    empBusiNm: Optional[str] = Field(
        None,
        description="채용업체명(회사명)"
    )

    # coClcdNm: String
    # - 기업구분명(대기업/공기업/공공기관/중견/외국계 등)
    coClcdNm: Optional[str] = Field(
        None,
        description="기업구분명"
    )

    # empWantedStdt: String
    # - 채용 시작 일자(문서상 문자열. 날짜 포맷은 외부 API 제공 형태 그대로)
    empWantedStdt: Optional[str] = Field(
        None,
        description="채용 시작일자"
    )

    # empWantedEndt: String
    # - 채용 종료 일자
    empWantedEndt: Optional[str] = Field(
        None,
        description="채용 종료일자"
    )

    # empWantedTypeNm: String
    # - 고용형태(정규직/기간제 등) "이름" 버전
    empWantedTypeNm: Optional[str] = Field(
        None,
        description="고용형태(이름)"
    )

    # regLogImgNm: String
    regLogImgNm: Optional[str] = Field(
        None,
        description="채용기업로고(식별자/파일명 등)"
    )

    # empWantedHomepgDetail: String
    empWantedHomepgDetail: Optional[str] = Field(
        None,
        description="채용사이트 URL(PC)"
    )

    # empWantedMobileUrl: String
    # - 모바일 채용 사이트 URL
    empWantedMobileUrl: Optional[str] = Field(
        None,
        description="모바일 채용사이트 URL"
    )


class JobsSearchResponse(BaseModel):
    # total: Number
    # - 총 건수 (외부 API에서 내려주는 전체 결과 수)
    total: int = Field(
        0,
        description="총 건수"
    )

    # startPage: Number
    # - 외부 API가 응답에 돌려주는 startPage 값(요청값과 같거나 보정된 값)
    startPage: int = Field(
        1,
        description="검색 시작 페이지"
    )

    # display: Number
    # - 외부 API가 응답에 돌려주는 display 값(요청값과 같거나 보정된 값)
    display: int = Field(
        10,
        description="출력 건수"
    )

    # items: List[JobItem]
    # - 공고 목록(각 원소가 <dhsOpenEmpInfo> 1개에 해당)
    items: List[JobItem] = Field(
        default_factory=list,
        description="채용공고 목록"
    )