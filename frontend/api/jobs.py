import requests
import os
from dotenv import load_dotenv

def search_jobs(payload: dict):
    # 매 호출 시마다 최신 환경변수를 로드하여 캐싱 현상 방지
    load_dotenv(override=True)
    
    backend_base_url = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8000")
    backend_url = f"{backend_base_url}/jobs/search"
    
    print(f"Requesting jobs API at: {backend_url} with payload: {payload}")
    
    res = requests.post(backend_url, json=payload, timeout=20)
    if not res.ok:
        try:
            detail = res.json().get("detail", res.text)
        except Exception:
            detail = res.text
        raise Exception(f"jobs API 호출 실패 ({res.status_code}): {detail}")

    return res.json()