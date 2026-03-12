import requests
import os
from dotenv import load_dotenv

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000/api")

JOB_MAPPING = {
    '133300': ('웹 개발자', '프론트엔드 개발자', 'AI/ML 엔지니어', '백엔드개발자', '백엔드 개발자', 'Python 백엔드 개발자',),
    '133301': ('웹 개발자', '프론트엔드 개발자', 'AI/ML 엔지니어', '백엔드개발자', '백엔드 개발자', 'Python 백엔드 개발자', ),
    '133302': ('웹 기획자', '웹 개발자', '프론트엔드 개발자', 'AI/ML 엔지니어', '백엔드 개발자', 'Python 백엔드 개발자', 'JAVA 백엔드 개발자'),
    '135101': ('데이터 설계', '웹 기획자', '웹 개발자', '프론트엔드 개발자', 'AI/ML 엔지니어', '백엔드 개발자',),
    '135102': ('데이터베이스 운영', '웹 기획자', '웹 개발자', '프론트엔드 개발자', 'AI/ML 엔지니어', '백엔드 개발자',),
    '135103': ('데이터 분석가', '빅데이터 분석가', '웹 기획자', '웹 개발자', '프론트엔드 개발자', 'AI/ML 엔지니어', '백엔드 개발자',),
    '133201': ('JAVA', 'JAVA 프로그래밍', 'JAVA 백엔드 개발자', '웹 기획자', '웹 개발자', '프론트엔드 개발자', 'AI/ML 엔지니어', '백엔드 개발자',),
    '133202': ('C', 'C언어', '프로그래밍', '웹 기획자', '웹 개발자', '프론트엔드 개발자', 'AI/ML 엔지니어', '백엔드 개발자',),
    '133100': ('소프트웨어', '시스템 소프트웨어', '웹 기획자', '웹 개발자', '프론트엔드 개발자', 'AI/ML 엔지니어', '백엔드 개발자',),
    '133101': ('소프트웨어', '시스템 소프트웨어', '프로그래머', '웹 기획자', '웹 개발자', '프론트엔드 개발자', 'AI/ML 엔지니어', '백엔드 개발자',),
    '133102': ('펌웨어', '임베디드', '웹 기획자', '웹 개발자', '프론트엔드 개발자', 'AI/ML 엔지니어', '백엔드 개발자',),
    '133200': ('응용 소프트웨어', '웹 기획자', '웹 개발자', '프론트엔드 개발자', 'AI/ML 엔지니어', '백엔드 개발자',),

    # 추가 맵핑 필요 (백엔드, AI, 데이터 등등등등등드읃읃ㅇ)

}


def search_jobs(payload: dict):
    # 매 호출 시마다 최신 환경변수를 로드하여 캐싱 현상 방지
    load_dotenv(override=True)
    job_role = payload.get("job_role")
    
    jobsCd_list = []
    for k, v in JOB_MAPPING.items():
        if isinstance(v, str):
            v = (v,)
        if job_role in v:
            jobsCd_list.append(k)
    # print(jobsCd_list)

    payload = dict(payload)  # 원본 payload 보호(참조 공유 방지)
    payload["jobsCd"] = '|'.join(jobsCd_list)

    if API_BASE_URL.rstrip("/").endswith("/api"):
        backend_url = f"{API_BASE_URL.replace('/api', '')}/jobs/search"
    else:
        backend_url = f"{API_BASE_URL}/jobs/search"
    # print('업뎃페이', payload)
    res = requests.post(backend_url, json=payload, timeout=20)


    if not res.ok:
        try:
            detail = res.json().get("detail", res.text)
        except Exception:
            detail = res.text
        raise Exception(f"jobs API 호출 실패 ({res.status_code}): {detail}")

    return res.json()



def get_latest_resume(user_id: str | None) -> dict:
    # FastAPI 서버의 최신 이력서 조회 엔드포인트
    BASE_URL = API_BASE_URL.rstrip("/")
    RESUME_LATEST_URL = f"{BASE_URL}/resumes/latest"

    res = requests.get(RESUME_LATEST_URL, params={"user_id": user_id}, timeout=20)
    
    # 이력서가 없거나 오류 발생 시 None을 반환하여 모달 호출 로직으로 넘김
    if not res.ok:
        return None
        
    return res.json()