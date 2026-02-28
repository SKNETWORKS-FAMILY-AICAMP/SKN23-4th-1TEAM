from fastapi import APIRouter

from backend.db.database import get_all_memos, save_memo
from backend.services.llm_service import (
    get_home_guide_response_stream,
    get_translated_news_summary,
)
from backend.services.tavily_service import get_web_context_first, get_web_context_second


router = APIRouter(prefix="/api/home", tags=["home"])


@router.get("/memos")
def read_memos(limit: int = 30):
    return {"items": get_all_memos(limit=limit)}


@router.post("/memos")
def create_memo(body: dict):
    save_memo(
        author=body.get("author", "anonymous"),
        content=body.get("content", ""),
        color=body.get("color", "#FFF9C4"),
        border=body.get("border", "#FFF59D"),
        text_color=body.get("text_color", "#5D4037"),
    )
    return {"ok": True}


@router.post("/news")
def create_news_summary(body: dict):
    query = body.get("query", "")
    raw_news = get_web_context_second(query) if query else ""
    summary = get_translated_news_summary(raw_news) if raw_news else ""
    return {"content": summary}


@router.post("/guide")
def create_guide_response(body: dict):
    user_message = body.get("message", "")
    use_web_search = bool(body.get("use_web_search", False))
    web_context = get_web_context_first(user_message) if use_web_search and user_message else ""
    reply = "".join(get_home_guide_response_stream(user_message, web_context))
    return {"content": reply, "web_context": web_context}
