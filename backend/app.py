from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.v1.endpoints import jobs_api, resume_api
from backend.db.base import Base
from backend.db.schema_patch import patch_user_table_columns
from backend.db.session import engine
from backend.models import refresh_token, user
from backend.routers import admin, auth, home, infer, social_auth


app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8501",
        "http://localhost:8502",
        "http://127.0.0.1:8501",
        "http://127.0.0.1:8502",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)
    patch_user_table_columns()


app.include_router(auth.router)
app.include_router(social_auth.router)
app.include_router(admin.router)
app.include_router(home.router)
app.include_router(infer.router)
app.include_router(jobs_api.router)
app.include_router(resume_api.router, prefix="/api")
