from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.v1.endpoints import jobs_api, resume_api
from backend.db.base import Base
from backend.db.schema_patch import patch_user_table_columns
from backend.db.session import engine
from backend.models import refresh_token, user
from backend.routers import admin, auth, home, infer, social_auth, interview, attitude

# 앱 생성 및 정적 파일 세팅
app = FastAPI()
# app.mount : 정적파일을 주소로 접근 가능하게 폴더 열어주는 기능.
app.mount("/static", StaticFiles(directory="static"), name="static")


# CORS 미들웨어 : 프론트 <-> 백엔드 통신을 허용하기 위함
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://localhost:8502",
        "http://localhost:8503",
        "http://127.0.0.1:8501",
        "http://127.0.0.1:8502",
        "http://127.0.0.1:8503",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 서버 시작 시 실행할 함수 호출
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    # 기존 테이블 구조 변경시 에러 안나게 DB 스키마 덧대는 커스텀 함수
    patch_user_table_columns()

# 라우터 연결  - 메인 서버에 하나씩 끼워 넣는 과정
app.include_router(auth.router)
app.include_router(social_auth.router)
app.add_api_route(
    "/api/v1/auth/kakao/start",
    social_auth.kakao_start,
    methods=["GET"],
    tags=["social-auth"],
)
app.add_api_route(
    "/api/v1/auth/kakao/callback",
    social_auth.kakao_callback,
    methods=["GET"],
    tags=["social-auth"],
)
app.add_api_route(
    "/api/v1/auth/google/start",
    social_auth.google_start,
    methods=["GET"],
    tags=["social-auth"],
)
app.add_api_route(
    "/api/v1/auth/google/callback",
    social_auth.google_callback,
    methods=["GET"],
    tags=["social-auth"],
)
app.include_router(admin.router)
app.include_router(home.router)
app.include_router(infer.router)
app.include_router(jobs_api.router)
app.include_router(resume_api.router, prefix="/api")
app.include_router(interview.router)
app.include_router(attitude.router)
