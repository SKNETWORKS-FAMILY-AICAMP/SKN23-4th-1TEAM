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
from backend.services.personality_vector_service import save_board_answer_to_vector_db
from backend.services.personality_feedback_service import generate_board_answer_feedback
from backend.services.personality_vector_service import debug_get_vector_document



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

    try:
        save_board_answer_to_vector_db(
            answer_id=answer_id,
            user_id=user.id,
            question_id=question_id,
            question_text=question["content"],
            answer_text=content,
        )
    except Exception as e:
        print("벡터DB 저장 실패:", e)

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


@router.post("/answers/{answer_id}/feedback")
def get_answer_feedback(
    answer_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)

    answer = get_board_answer(answer_id)
    if not answer:
        raise HTTPException(status_code=404, detail="답변을 찾을 수 없습니다.")

    if answer["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="본인 답변만 피드백 받을 수 있습니다.")

    question = get_board_question(answer["question_id"])
    if not question:
        raise HTTPException(status_code=404, detail="질문을 찾을 수 없습니다.")

    feedback = generate_board_answer_feedback(
        question_text=question["content"],
        answer_text=answer["content"],
        user_id=user.id,
    )

    return {
        "ok": True,
        "answer_id": answer_id,
        "feedback": feedback,
    }



# swagger 테스트용(확인 후 지울것)
@router.get("/answers/{answer_id}/vector-debug")
def vector_debug(
    answer_id: int,
):
    result = debug_get_vector_document(answer_id)
    return {
        "ok": True,
        "answer_id": answer_id,
        "vector_result": result,
    }


# swagger테스트용(확인 후 지울것)
@router.post("/answers/{answer_id}/feedback-test")
def feedback_test(
    answer_id: int,
):
    answer = get_board_answer(answer_id)
    if not answer:
        raise HTTPException(status_code=404, detail="답변을 찾을 수 없습니다.")

    question = get_board_question(answer["question_id"])
    if not question:
        raise HTTPException(status_code=404, detail="질문을 찾을 수 없습니다.")

    feedback = generate_board_answer_feedback(
        question_text=question["content"],
        answer_text=answer["content"],
        user_id=answer["user_id"],
    )

    return {
        "ok": True,
        "answer_id": answer_id,
        "feedback": feedback,
    }