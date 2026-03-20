import os
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from openai import OpenAI

from backend.db.database import (
    count_board_answers,
    get_board_answer,
    get_board_answers,
    get_board_question,
    get_board_questions,
    toggle_board_answer_like,
    upsert_board_answer,
    delete_board_answer,
    get_all_board_questions,
    create_board_question,
    delete_board_question
)
from backend.db.session import get_db
from backend.routers.auth import get_current_user
from backend.services import auth_service
from backend.services.personality_service import save_and_evaluate_answer, generate_board_answer_feedback

router = APIRouter(prefix="/api/board", tags=["board"])

class CreateQuestionRequest(BaseModel):
    raw_content: str

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
def create_answer(question_id: int, body: dict, request: Request, db: Session = Depends(get_db)):
    question = get_board_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="질문을 찾을 수 없습니다.")

    content = (body.get("content") or "").strip()
    if len(content) < 5:
        raise HTTPException(status_code=400, detail="답변은 5자 이상 입력해주세요.")

    user = get_current_user(request, db)
    author_name = user.name or user.email.split("@")[0]

    answer_id = upsert_board_answer(question_id, user.id, author_name, content)

    feedback = None
    try:
        feedback = save_and_evaluate_answer(answer_id, user.id, question_id, question["content"], content)
    except Exception:
        pass

    return {"ok": True, "answer_id": answer_id, "author_name": author_name, "feedback": feedback}

@router.post("/answers/{answer_id}/like")
def toggle_answer_like(answer_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    answer = get_board_answer(answer_id)
    if not answer:
        raise HTTPException(status_code=404, detail="답변을 찾을 수 없습니다.")

    liked = toggle_board_answer_like(answer_id, user.id)
    updated = get_board_answer(answer_id) or answer
    return {"ok": True, "liked": liked, "like_count": int(updated.get("like_count", 0)), "question_id": answer.get("question_id")}

@router.post("/answers/{answer_id}/feedback")
def get_answer_feedback(answer_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    answer = get_board_answer(answer_id)
    if not answer:
        raise HTTPException(status_code=404, detail="답변을 찾을 수 없습니다.")

    if answer["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="본인 답변만 피드백 받을 수 있습니다.")

    question = get_board_question(answer["question_id"])
    feedback = generate_board_answer_feedback(
        question_id=answer["question_id"],
        question_text=question["content"],
        answer_text=answer["content"],
        user_id=user.id,
    )
    return {"ok": True, "answer_id": answer_id, "feedback": feedback}

@router.delete("/answers/{answer_id}")
def delete_answer_api(answer_id: int, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    answer = get_board_answer(answer_id)
    
    if not answer:
        raise HTTPException(status_code=404, detail="답변을 찾을 수 없습니다.")
    
    if answer["user_id"] != user.id:
        raise HTTPException(status_code=403, detail="본인의 답변만 삭제할 수 있습니다.")

    delete_board_answer(answer_id)
    return {"ok": True, "message": "삭제되었습니다."}

@router.post("/questions")
def create_question_api(body: CreateQuestionRequest, request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)
    raw_content = body.raw_content.strip()
    
    if len(raw_content) < 5:
        raise HTTPException(status_code=400, detail="내용이 너무 짧습니다.")

    existing_questions = get_all_board_questions()
    existing_text = "\n".join([f"- {q}" for q in existing_questions])

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(status_code=500, detail="서버에 OPENAI_API_KEY가 설정되지 않았습니다.")
        
    client = OpenAI(api_key=api_key)
    
    prompt = f"""
    아래는 기존 인성 면접 질문 목록입니다:
    {existing_text}

    사용자가 입력한 새로운 상황/질문:
    "{raw_content}"

    요청 사항:
    1. 사용자의 입력이 장난, 욕설, 일상 대화(예: 점심 메뉴 추천, 롤 재밌다 등) 등 면접과 전혀 무관한 내용이라면 오직 "INVALID" 라고만 출력하세요.
    2. 사용자의 입력이 인성/행동 면접이 아닌 기술 면접 질문(예: 프 프레임워크 동작 원리, 알고리즘, 코딩 지식 등)이라면 오직 "TECHNICAL" 이라고만 출력하세요.
    3. 사용자의 입력이 기존 질문 목록 중 하나와 핵심 의미가 거의 똑같거나 의도가 겹친다면, 오직 "DUPLICATE" 라고만 출력하세요.
    4. 위 3가지에 해당하지 않는 유효한 인성 면접 질문이라면, 다른 지원자들이 진지하게 고민해볼 수 있는 '전문적이고 깔끔한 형태의 인성 면접 질문'으로 교정해 주세요. 교정한 문장 앞에는 "REFINED: "를 붙여서 출력하세요.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        ai_result = response.choices[0].message.content.strip()
        
        if ai_result == "INVALID":
            raise HTTPException(status_code=422, detail="INVALID_CONTENT")
        elif ai_result == "TECHNICAL":
            raise HTTPException(status_code=422, detail="TECHNICAL_CONTENT")
        elif ai_result == "DUPLICATE":
            raise HTTPException(status_code=409, detail="DUPLICATE_CONTENT")
        
        refined_content = ai_result.replace("REFINED:", "").strip()
        new_question_id = create_board_question(refined_content)
        
        return {
            "ok": True, 
            "question_id": new_question_id,
            "refined_content": refined_content
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail="AI 질문 교정 중 오류가 발생했습니다.")


@router.delete("/questions/{question_id}")
def delete_question_api(question_id: int, request: Request, db: Session = Depends(get_db)):
    token = None
    
    # 1. 헤더에서 토큰 강제 추출
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        token = auth.split(" ", 1)[1].strip()
    
    # 2. 헤더에 없으면 쿠키에서 강제 추출 (최후의 보루)
    if not token:
        token = request.cookies.get("access_token") 
        
    # 3. 그래도 없으면 진짜 로그인 안 한 것!
    if not token:
        raise HTTPException(status_code=401, detail="토큰이 전달되지 않았습니다 (헤더/쿠키 모두 없음).")
    
    try:
        user = auth_service.get_user_from_access(db, token)
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"토큰이 만료되었거나 손상되었습니다: {str(e)}")

    # 4. 관리자 권한 최종 확인
    if not hasattr(user, 'role') or user.role != "admin":
        raise HTTPException(status_code=403, detail="관리자만 질문을 삭제할 수 있습니다.")
    
    question = get_board_question(question_id)
    if not question:
        raise HTTPException(status_code=404, detail="질문을 찾을 수 없습니다.")

    delete_board_question(question_id)
    
    return {"ok": True, "message": "질문이 삭제되었습니다."}