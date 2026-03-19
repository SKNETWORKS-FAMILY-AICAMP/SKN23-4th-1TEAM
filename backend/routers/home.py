from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session

from backend.db.database import get_all_memos, save_memo
from backend.db.session import get_db
from backend.routers.auth import get_current_user
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
def create_memo(body: dict, request: Request, db: Session = Depends(get_db)):
    # 선택 사항: 로그인 안 한 경우도 허용하려면 get_current_user 대신 수동 추출 필요
    # 여기서는 "계정에 맞게 연결" 요청에 따라 로그인을 필수로 처리
    user = get_current_user(request, db)
    author = user.name or user.email.split("@")[0]
    
    save_memo(
        user_id=user.id,
        author=author,
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


# 첨삭용 라우터
from fastapi import UploadFile, File, Form, HTTPException
from backend.services.llm_service import get_proofread_result
import PyPDF2

@router.post("/proofread-file")
async def proofread_file(
    file: UploadFile = File(...),
    document_type: str = Form(...)
):
    try:
        content_text = ""
        
        if file.filename.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(file.file)
            for page in pdf_reader.pages:
                content_text += page.extract_text() + "\n"
        else:
            content = await file.read()
            content_text = content.decode("utf-8", errors="ignore")
            
        if not content_text.strip():
            raise HTTPException(status_code=400, detail="문서에서 텍스트를 추출할 수 없습니다.")
            
        feedback = get_proofread_result(content_text, document_type)
        
        return {"feedback": feedback}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))