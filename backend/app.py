"""
File: app.py
Author: 양창일
Created: 2026-02-15
Description:  # 서버 시작 파일 (전체를 연결하는 중심 파일)

Modification History:
- 2026-02-15: 초기 생성
- 2026-02-22 (김지우) : streamlit 포트 하나 추가
- 2026-02-25: infer 및 jobs_api 라우터 통합
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.db.session import engine
from backend.db.base import Base
from backend.models import user, refresh_token

# ─── 라우터 임포트 ─────────────────────────────────────────
from backend.routers import auth, social_auth, infer
from backend.api.v1.endpoints import jobs_api

app = FastAPI()

# ─── 정적 파일 마운트 ──────────────────────────────────────
app.mount("/static", StaticFiles(directory="static"), name="static")

# ─── CORS 미들웨어 설정 ────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://localhost:8502",  # 현재 사용 중인 포트
        "http://127.0.0.1:8501",
        "http://127.0.0.1:8502",
    ],
    allow_credentials=True,
    allow_methods=["*"],  # GET, POST 등을 모두 허용
    allow_headers=["*"],  # 모든 헤더 허용
)

# ─── 앱 시작 시 DB 테이블 생성 ─────────────────────────────
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)  # 테이블 생성(초기용)

# ─── 라우터 등록 ───────────────────────────────────────────
app.include_router(auth.router)
app.include_router(social_auth.router)
app.include_router(infer.router)        # 👈 infer 라우터 활성화 완료

# 💡 만약 jobs_api 쪽에도 router가 정의되어 있다면 아래 주석을 풀고 사용하세요!
app.include_router(jobs_api.router)

