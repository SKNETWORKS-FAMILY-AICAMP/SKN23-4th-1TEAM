from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.db.database import (
    count_board_answers,
    create_board_answer,
    get_board_answer,
    get_board_answers,
    get_board_question,
    get_board_questions,
    toggle_board_answer_like,
)
from backend.db.session import get_db
from backend.routers.auth import get_current_user
from backend.services import auth_service


router = APIRouter(prefix="/api/board", tags=["board"])


@router.get("/questions")
def read_board_questions():
    return {"items": get_board_questions()}


@router.get("/questions/{question_id}")
def read_board_question(
    question_id: int,
    request: Request,
    db: Session = Depends(get_db),
    limit: int = 10,
    offset: int = 0,
):
    question = get_board_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="질문을 찾을 수 없습니다.")

    viewer_id = None
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        try:
            token = auth.split(" ", 1)[1].strip()
            viewer = auth_service.get_user_from_access(db, token)
            viewer_id = viewer.id
        except Exception:
            viewer_id = None

    answers = get_board_answers(question_id, limit=limit, offset=offset, viewer_id=viewer_id)
    total_count = count_board_answers(question_id)
    return {
        "question": question,
        "answers": answers,
        "total_count": total_count,
        "limit": limit,
        "offset": offset,
        "has_more": offset + len(answers) < total_count,
    }


@router.post("/questions/{question_id}/answers")
def create_answer(
    question_id: int,
    body: dict,
    request: Request,
    db: Session = Depends(get_db),
):
    question = get_board_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="질문을 찾을 수 없습니다.")

    content = (body.get("content") or "").strip()
    if len(content) < 5:
        raise HTTPException(status_code=400, detail="답변은 5자 이상 입력해주세요.")

    user = get_current_user(request, db)
    author_name = user.name or user.email.split("@")[0]
    answer_id = create_board_answer(question_id, user.id, author_name, content)

    return {
        "ok": True,
        "answer_id": answer_id,
        "author_name": author_name,
    }


@router.post("/answers/{answer_id}/like")
def toggle_answer_like(
    answer_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)
    answer = get_board_answer(answer_id)
    if not answer:
        raise HTTPException(status_code=404, detail="답변을 찾을 수 없습니다.")

    liked = toggle_board_answer_like(answer_id, user.id)
    updated = get_board_answer(answer_id) or answer
    return {
        "ok": True,
        "liked": liked,
        "like_count": int(updated.get("like_count", 0)),
        "question_id": answer.get("question_id"),
    }
