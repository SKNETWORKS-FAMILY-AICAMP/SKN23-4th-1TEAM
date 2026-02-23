"""
File: app.py
Author: 양창일
Created: 2026-02-15
Description:  # 서버 시작 파일 (전체를 연결하는 중심 파일)

Modification History:
- 2026-02-15: 초기 생성
- 2026-02-22 (김지우) : streamlit 포트 하나 추가
"""

from fastapi import FastAPI  # fastapi
from fastapi.middleware.cors import CORSMiddleware  # cors
from backend.db.session import engine  # engine
from backend.db.base import Base  # base
from backend.models import user, refresh_token  # 모델 등록용(임포트)
from backend.routers import infer, auth, social_auth 
from fastapi.staticfiles import StaticFiles # 👈 맨 위에 임포트 추가

app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

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

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)  # 테이블 생성(초기용)

app.include_router(auth.router)
app.include_router(social_auth.router)
app.include_router(infer.router)
