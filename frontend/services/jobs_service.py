"""
File: jobs_service.py
Author: 유헌상
Created: 2026-02-24
Description: 채용 공고 데이터 가공

Modification History:
- 2026-02-24 (유헌상): 초기 작성
"""

def build_job_cards_data(data: dict) -> list[dict]:
    items = data.get("items", []) if isinstance(data, dict) else []
    cards = []

    for it in items:
        company = it.get("empBusiNm") or "(회사명 없음)"
        title = it.get("empWantedTitle") or "(공고명 없음)"
        logo = it.get("regLogImgNm") or ""
        co_type = it.get("coClcdNm") or ""
        emp_type = it.get("empWantedTypeNm") or ""
        start_dt = it.get("empWantedStdt") or ""
        end_dt = it.get("empWantedEndt") or ""
        link = it.get("empWantedHomepgDetail") or it.get("empWantedMobileUrl") or ""

        # period = f"{start_dt} ~ {end_dt}" if (start_dt or end_dt) else ""
        # desc_parts = [x for x in [co_type, emp_type, period] if x]
        # desc = " | ".join(desc_parts) if desc_parts else "채용공고 상세정보"

        cards.append({
            "id": it.get("empSeqno") or f"{company}_{title}",
            "company": company,
            'logo': logo,
            "co_type": co_type,
            "emp_type": emp_type,
            "title": title,
            "start_dt": start_dt,
            "end_dt": end_dt,
            "link": link,
        })

    return cards


def dateparse(date:str):
    return f'{date[2:4]}년 {int(date[4:6])}월 {int(date[6:8])}일'