"""
File: jobs_service.py
Author: 유헌상
Created: 2026-02-23
Description: 채용공고  로직
"""

import httpx
import logging
from xml.etree import ElementTree as ET
from backend.core.config import settings

logger = logging.getLogger("uvicorn.error")


class ExternalJobsAPIError(RuntimeError):
    pass


def _get_text(parent: ET.Element, tag: str) -> str | None:
    node = parent.find(tag)
    if node is None or node.text is None:
        return None
    return node.text.strip()


def _join_multi(values: list[str] | None) -> str | None:
    if not values:
        return None
    return ",".join(values)


def parse_jobs_xml(xml_text: str) -> dict:
    root = ET.fromstring(xml_text)

    total = int(_get_text(root, "total") or 0)
    start_page = int(_get_text(root, "startPage") or 1)
    display = int(_get_text(root, "display") or 10)

    items: list[dict] = []
    for info in root.findall("dhsOpenEmpInfo"):
        items.append(
            {
                "empSeqno": _get_text(info, "empSeqno"),
                "empWantedTitle": _get_text(info, "empWantedTitle"),
                "empBusiNm": _get_text(info, "empBusiNm"),
                "coClcdNm": _get_text(info, "coClcdNm"),
                "empWantedStdt": _get_text(info, "empWantedStdt"),
                "empWantedEndt": _get_text(info, "empWantedEndt"),
                "empWantedTypeNm": _get_text(info, "empWantedTypeNm"),
                "regLogImgNm": _get_text(info, "regLogImgNm"),
                "empWantedHomepgDetail": _get_text(info, "empWantedHomepgDetail"),
                "empWantedMobileUrl": _get_text(info, "empWantedMobileUrl"),
            }
        )

    return {
        "total": total,
        "startPage": start_page,
        "display": display,
        "items": items,
    }


async def fetch_jobs(params: dict) -> dict:
    if not settings.WORKNET_URL_BASE:
        raise ExternalJobsAPIError("WORKNET_URL_BASE 설정이 비어있습니다.")

    url = settings.WORKNET_URL_BASE

    # 프론트에서 POST로 받은 params를 그대로 외부 API 쿼리에 합침
    qp = {
        "authKey": settings.WORKNET_API_KEY,
        "callTp": "L",
        "returnType": "XML",
        **params,
    }

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "*/*",
    }

    try:
        async with httpx.AsyncClient(
            timeout=settings.WORKNET_TIMEOUT_SEC,
            follow_redirects=True,   # 302 자동 추적
            headers=headers,
        ) as client:
            res = await client.get(url, params=qp)

            # “데이터를 실제로 받아오는지” 확인용 로그
            # logger.warning(f"[WORK24] final_url={res.request.url}")

            res.raise_for_status()
            return parse_jobs_xml(res.text)

    except httpx.TimeoutException as e:
        raise ExternalJobsAPIError("외부 채용 API 호출이 시간 초과되었습니다.") from e
    except httpx.HTTPStatusError as e:
        r = e.response
        raise ExternalJobsAPIError(
            f"외부 채용 API HTTP 에러: {r.status_code} (final_url={r.request.url}) body_head={r.text[:200]}"
        ) from e
    except httpx.RequestError as e:
        raise ExternalJobsAPIError(f"외부 채용 API 요청 실패: {type(e).__name__}: {e}") from e
    except ET.ParseError as e:
        raise ExternalJobsAPIError("외부 채용 API의 XML 응답 파싱에 실패했습니다.") from e
    


if __name__ == "__main__":
    import asyncio
    import json

    async def _test():
        # 프론트가 보낼 파라미터라고 가정
        params = {
            "startPage": 1,
            "display": 3,
            # 필요하면 여기에 추가 파라미터
        }

        data = await fetch_jobs(params)
        print(json.dumps(data, ensure_ascii=False, indent=2))

    asyncio.run(_test())