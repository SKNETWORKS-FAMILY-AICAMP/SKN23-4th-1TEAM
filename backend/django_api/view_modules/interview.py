from .shared import *  # noqa: F401,F403


@api_view(["POST"])
def interview_analyze_resume(request):
    body = json_body(request)
    try:
        result = analyze_resume_comprehensive(body["resume_text"], body["job_role"])
    except Exception as exc:
        raise ApiError(str(exc), 500) from exc
    return {"status": "success", "data": result}


@api_view(["POST"])
def interview_store_resume(request):
    body = json_body(request)
    try:
        chunk_count = store_resume(body["resume_text"], body["user_id"])
    except Exception as exc:
        raise ApiError(str(exc), 500) from exc
    return {"status": "success", "chunk_count": chunk_count}


@api_view(["POST"])
def interview_evaluate(request):
    body = json_body(request)
    try:
        result = generate_evaluation(
            body["messages"],
            body["job_role"],
            body["difficulty"],
            body.get("resume_text"),
        )
    except Exception as exc:
        raise ApiError(str(exc), 500) from exc
    return {"status": "success", "evaluation": result}


@api_view(["POST"])
def interview_chat(request):
    body = json_body(request)
    try:
        result = evaluate_and_respond(
            question=body.get("current_question", "시작"),
            answer=body.get("user_answer", ""),
            job_role=body.get("job_role") or "개발자",
            difficulty=body.get("difficulty") or "중급",
            persona_style=body.get("persona") or "꼼꼼한 기술 면접관",
            user_id=str(body.get("user_id", "anonymous")),
            resume_text=body.get("resume_text"),
            next_main_question=body.get("next_main_question"),
            followup_count=body.get("followup_count", 0),
        )
    except Exception as exc:
        raise ApiError(str(exc), 500) from exc
    return {"status": "success", "data": result}


@api_view(["POST"])
def interview_save_details(request):
    body = json_body(request)
    session_id = body.get("session_id")
    if not session_id:
        raise ApiError("session_id is required", 400)
    with db_session() as db:
        new_detail = base.InterviewDetail(
            session_id=session_id,
            turn_index=body.get("turn_index", 0),
            question=body.get("question", ""),
            answer=body.get("answer", ""),
            response_time=body.get("response_time", 0),
            score=body.get("score", 0.0),
            sentiment_score=body.get("sentiment_score", 0.0),
            feedback=body.get("feedback", ""),
            is_followup=body.get("is_followup", False),
        )
        db.add(new_detail)
        db.commit()
    return {"message": "상세 기록 저장 완료"}


@api_view(["GET", "PUT", "DELETE"])
def interview_session_resource(request, session_id: int):
    if request.method == "GET":
        return {"items": get_details_by_session(session_id)}

    if request.method == "DELETE":
        with db_session() as db:
            current_user = get_current_user(request, db)
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT id FROM interview_sessions WHERE id=%s AND user_id=%s",
                        (session_id, current_user.id),
                    )
                    session = cur.fetchone()
                    if not session:
                        raise ApiError(
                            "세션을 찾을 수 없거나 삭제 권한이 없습니다.",
                            404,
                        )
                    cur.execute(
                        "DELETE FROM interview_details WHERE session_id=%s",
                        (session_id,),
                    )
                    cur.execute(
                        "DELETE FROM interview_sessions WHERE id=%s",
                        (session_id,),
                    )
        return {"message": "삭제 완료", "session_id": session_id}

    body = json_body(request)
    with db_session() as db:
        session_record = (
            db.query(base.InterviewSession)
            .filter(base.InterviewSession.id == session_id)
            .first()
        )
        if not session_record:
            raise ApiError("세션을 찾을 수 없습니다.", 404)
        if "total_score" in body:
            session_record.total_score = body["total_score"]
        if "status" in body:
            session_record.status = body["status"]
            if body["status"] == "COMPLETED":
                if "total_score" not in body:
                    avg_score = (
                        db.query(func.avg(base.InterviewDetail.score))
                        .filter(
                            base.InterviewDetail.session_id == session_id,
                            base.InterviewDetail.score.isnot(None),
                        )
                        .scalar()
                    )
                    if avg_score is not None:
                        session_record.total_score = round(float(avg_score), 2)
                session_record.ended_at = datetime.now()
        db.commit()
    return {"message": "세션 업데이트 완료"}


@api_view(["GET"])
def interview_sessions(request):
    user_id = int(request.GET.get("user_id", 0))
    return {"items": get_sessions_by_user(user_id)}
