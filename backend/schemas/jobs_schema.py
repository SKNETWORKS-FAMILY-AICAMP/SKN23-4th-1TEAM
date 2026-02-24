import requests

BACKEND_URL = "http://localhost:8000/api/v1/jobs/search"


def search_jobs(start_page=1, display=3, extra_params=None):
    payload = {
        "startPage": start_page,
        "display": display,
    }

    if extra_params:
        payload.update({k: v for k, v in extra_params.items() if v is not None})

    res = requests.post(BACKEND_URL, json=payload, timeout=20)

    if not res.ok:
        try:
            detail = res.json().get("detail", res.text)
        except Exception:
            detail = res.text
        raise Exception(f"jobs API 호출 실패 ({res.status_code}): {detail}")

    return res.json()