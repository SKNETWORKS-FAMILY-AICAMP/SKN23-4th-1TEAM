from .shared import *  # noqa: F401,F403


@api_view(["GET", "POST"])
def board_questions_collection(request):
    if request.method == "GET":
        return {"items": get_board_questions()}

    body = json_body(request)
    raw_content = (body.get("raw_content") or "").strip()
    if len(raw_content) < 5:
        raise ApiError("내용이 너무 짧습니다.", 400)

    with db_session() as db:
        get_current_user(request, db)

    existing_questions = get_all_board_questions()
    existing_text = "\n".join(f"- {question}" for question in existing_questions)
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ApiError("서버에 OPENAI_API_KEY가 설정되지 않았습니다.", 500)

    client = OpenAI(api_key=api_key)
    prompt = (
        f"아래는 기존 인성 면접 질문 목록입니다.\n{existing_text}\n\n"
        f"사용자가 입력한 새로운 상황/질문:\n\"{raw_content}\"\n\n"
        "유효하지 않으면 INVALID, 기술 질문이면 TECHNICAL, 중복이면 DUPLICATE, "
        "정제 가능한 유효 질문이면 'REFINED: ...' 형식으로만 답해주세요."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        ai_result = response.choices[0].message.content.strip()
    except Exception as exc:
        raise ApiError("AI 질문 교정 중 오류가 발생했습니다.", 500) from exc

    if ai_result == "INVALID":
        raise ApiError("INVALID_CONTENT", 422)
    if ai_result == "TECHNICAL":
        raise ApiError("TECHNICAL_CONTENT", 422)
    if ai_result == "DUPLICATE":
        raise ApiError("DUPLICATE_CONTENT", 409)

    refined_content = ai_result.replace("REFINED:", "").strip()
    new_question_id = create_board_question(refined_content)
    return {
        "ok": True,
        "question_id": new_question_id,
        "refined_content": refined_content,
    }


@api_view(["GET", "DELETE"])
def board_question_resource(request, question_id: int):
    if request.method == "GET":
        limit = int(request.GET.get("limit", 10))
        offset = int(request.GET.get("offset", 0))
        question = get_board_question(question_id)
        if not question:
            raise ApiError("질문을 찾을 수 없습니다.", 404)

        with db_session() as db:
            viewer = optional_current_user(request, db)
            viewer_id = viewer.id if viewer else None

        answers = get_board_answers(
            question_id,
            limit=limit,
            offset=offset,
            viewer_id=viewer_id,
        )
        total_count = count_board_answers(question_id)
        return {
            "question": question,
            "answers": answers,
            "total_count": total_count,
            "limit": limit,
            "offset": offset,
            "has_more": offset + len(answers) < total_count,
        }

    with db_session() as db:
        user = get_current_user(request, db)
        if getattr(user, "role", "user") != "admin":
            raise ApiError("관리자만 질문을 삭제할 수 있습니다.", 403)

    question = get_board_question(question_id)
    if not question:
        raise ApiError("질문을 찾을 수 없습니다.", 404)

    delete_board_question(question_id)
    return {"ok": True, "message": "질문이 삭제되었습니다."}


@api_view(["POST"])
def board_create_answer(request, question_id: int):
    body = json_body(request)
    question = get_board_question(question_id)
    if not question:
        raise ApiError("질문을 찾을 수 없습니다.", 404)

    content = (body.get("content") or "").strip()
    if len(content) < 5:
        raise ApiError("답변은 5자 이상 입력해주세요.", 400)

    with db_session() as db:
        user = get_current_user(request, db)
        author_name = user.name or user.email.split("@")[0]
        answer_id = upsert_board_answer(question_id, user.id, author_name, content)
        feedback = None
        try:
            feedback = save_and_evaluate_answer(
                answer_id,
                user.id,
                question_id,
                question["content"],
                content,
            )
        except Exception:
            feedback = None

    return {
        "ok": True,
        "answer_id": answer_id,
        "author_name": author_name,
        "feedback": feedback,
    }


@api_view(["POST"])
def board_toggle_like(request, answer_id: int):
    with db_session() as db:
        user = get_current_user(request, db)
        answer = get_board_answer(answer_id)
        if not answer:
            raise ApiError("답변을 찾을 수 없습니다.", 404)
        liked = toggle_board_answer_like(answer_id, user.id)

    updated = get_board_answer(answer_id) or answer
    return {
        "ok": True,
        "liked": liked,
        "like_count": int(updated.get("like_count", 0)),
        "question_id": answer.get("question_id"),
    }


@api_view(["POST"])
def board_feedback(request, answer_id: int):
    with db_session() as db:
        user = get_current_user(request, db)
        answer = get_board_answer(answer_id)
        if not answer:
            raise ApiError("답변을 찾을 수 없습니다.", 404)
        if answer["user_id"] != user.id:
            raise ApiError("본인 답변만 피드백을 받을 수 있습니다.", 403)

    question = get_board_question(answer["question_id"])
    feedback = generate_board_answer_feedback(
        question_id=answer["question_id"],
        question_text=question["content"],
        answer_text=answer["content"],
        user_id=user.id,
    )
    return {"ok": True, "answer_id": answer_id, "feedback": feedback}


@api_view(["DELETE"])
def board_delete_answer(request, answer_id: int):
    with db_session() as db:
        user = get_current_user(request, db)
        answer = get_board_answer(answer_id)
        if not answer:
            raise ApiError("답변을 찾을 수 없습니다.", 404)
        if answer["user_id"] != user.id:
            raise ApiError("본인 답변만 삭제할 수 있습니다.", 403)

    delete_board_answer(answer_id)
    return {"ok": True, "message": "삭제되었습니다."}
