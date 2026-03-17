import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.v1.endpoints import jobs_api, resume_api
from backend.db.base import Base
from backend.db.schema_patch import patch_user_table_columns
from backend.db.session import engine
from backend.models import refresh_token, user
from backend.routers import admin, auth, home, infer, social_auth, interview, attitude, agent

app = FastAPI()

from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    print(f"Validation Error: {exc.errors()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )

app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS 미들웨어 수정
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://192.168.2.1:5173", # 브라우저 로그에 찍힌 실제 IP 추가
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    patch_user_table_columns()

# 라우터 연결
app.include_router(auth.router)
app.include_router(social_auth.router)

# 소셜 로그인 관련 라우트 생략 (기존 코드 유지)

app.include_router(admin.router)
app.include_router(home.router)
app.include_router(infer.router)
app.include_router(jobs_api.router)

# 이력서 API 주소를 프론트와 맞춤 (/api/v1/resumes가 되도록 수정)
app.include_router(resume_api.router, prefix="/api/v1") 

app.include_router(interview.router)
app.include_router(attitude.router)
app.include_router(agent.router, prefix="/api/v1/agent", tags=["Agent"])