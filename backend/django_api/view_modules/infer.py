from .shared import *  # noqa: F401,F403


@api_view(["POST"])
def infer_proofread(request):
    body = json_body(request)
    return {
        "feedback": get_proofread_result(
            body.get("content", ""),
            body.get("document_type", "resume"),
        )
    }


@api_view(["POST"])
def infer_ingest(request):
    file = request.FILES.get("file")
    session_id = request.GET.get("session_id", "default")
    if not file:
        raise ApiError("file is required", 422)
    contents = file.read()
    file_path = f"temp_{file.name}"
    with open(file_path, "wb") as buffer:
        buffer.write(contents)
    content_text = ""
    try:
        if file.name.endswith(".pdf"):
            pdf_reader = PyPDF2.PdfReader(file_path)
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    content_text += extracted + "\n"
        else:
            content_text = contents.decode("utf-8", errors="ignore")
        store_resume(content_text, session_id)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
    return {"message": "이력서 분석 완료", "resume_text": content_text.strip()}


@api_view(["POST"])
def infer_start(request):
    body = json_body(request)
    user_id = None
    with db_session() as db:
        user = optional_current_user(request, db)
        if user:
            user_id = user.id
        new_session = base.InterviewSession(
            user_id=user_id,
            job_role=body.get("job_role", "개발자"),
            difficulty=body.get("difficulty", "중"),
            persona=body.get("persona", "꼼꼼한 기술 면접관"),
            resume_used=body.get("resume_used", False),
            resume_id=body.get("resume_id"),
            manual_tech_stack=body.get("manual_tech_stack"),
            status="START",
        )
        db.add(new_session)
        db.commit()
        db.refresh(new_session)
        return {"session_id": new_session.id}


@api_view(["GET"])
def infer_questions(request):
    job_role = request.GET.get("job_role")
    difficulty = request.GET.get("difficulty")
    limit = int(request.GET.get("limit", 5))
    with db_session() as db:
        rows = (
            db.query(base.QuestionPool)
            .join(base.JobCategory)
            .filter(
                base.JobCategory.target_role == job_role,
                base.QuestionPool.difficulty == difficulty,
            )
            .order_by(func.rand())
            .limit(limit)
            .all()
        )
    return {
        "items": [
            {"id": row.id, "question": row.content, "difficulty": row.difficulty}
            for row in rows
        ]
    }


@api_view(["POST"])
def infer_stt(request):
    file = request.FILES.get("file")
    if not file:
        raise ApiError("file is required", 422)
    temp_filename = f"temp_{file.name}.wav"
    with open(temp_filename, "wb") as f:
        for chunk in file.chunks():
            f.write(chunk)
    try:
        with open(temp_filename, "rb") as audio_data:
            text = _get_ai().stt_whisper(audio_data)
    finally:
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
    return {"text": text}


@api_view(["POST"])
def infer_tts(request):
    body = json_body(request)
    text = body.get("text", "")
    if not text:
        raise ApiError("텍스트가 제공되지 않았습니다.", 400)
    try:
        audio_content = _get_ai().tts_voice(text)
    except Exception as local_exc:
        try:
            api_key = os.getenv("OPENAI_API_KEY", "")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY가 설정되지 않았습니다.")
            client = OpenAI(api_key=api_key)
            tts_response = client.audio.speech.create(
                model="tts-1",
                voice="alloy",
                input=text,
            )
            audio_content = tts_response.content
        except Exception as openai_exc:
            raise ApiError(
                f"TTS 생성 실패: local={str(local_exc)} | openai={str(openai_exc)}",
                500,
            ) from openai_exc
    return HttpResponse(audio_content, content_type="audio/mpeg")


@api_view(["POST"])
def infer_evaluate_turn(request):
    body = json_body(request)
    answer = body.get("answer", "")
    if not str(answer).strip():
        raise ApiError("answer가 비어 있습니다.", 400)
    result = evaluate_and_respond(
        question=body.get("question", "면접 질문"),
        answer=answer,
        job_role=body.get("job_role", "Python 백엔드 개발자"),
        difficulty=body.get("difficulty", "중"),
        persona_style=body.get("persona_style", "꼼꼼한 기술 면접관"),
        user_id=str(body.get("user_id", "guest")),
        resume_text=body.get("resume_text"),
        next_main_question=body.get("next_main_question"),
        followup_count=int(body.get("followup_count", 0)),
    )
    attitude = body.get("attitude")
    summary_text = (
        (attitude.get("summary_text") or "").strip()
        if isinstance(attitude, dict)
        else ""
    )
    if summary_text:
        base_feedback = (result.get("feedback") or "").strip()
        base_reply = (result.get("reply_text") or "").strip()
        result["feedback"] = (
            f"{base_feedback} 태도 측면에서는 {summary_text}"
            if base_feedback
            else f"태도 측면에서는 {summary_text}"
        )
        result["reply_text"] = (
            f"{base_reply}\n\n[태도 피드백] {summary_text}"
            if base_reply
            else f"[태도 피드백] {summary_text}"
        )
    return result


@api_view(["GET"])
def infer_realtime_token(request):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ApiError("서버에 OPENAI_API_KEY가 설정되지 않았습니다.", 500)
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = {
        "model": os.getenv(
            "OPENAI_REALTIME_MODEL",
            "gpt-4o-realtime-preview-2024-12-17",
        ),
        "voice": "echo",
    }
    try:
        response = requests.post(
            "https://api.openai.com/v1/realtime/sessions",
            headers=headers,
            json=data,
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as exc:
        raise ApiError("AI 면접용 토큰 발급에 실패했습니다.", 500) from exc


@api_view(["POST"])
def attitude_infer(request):
    parsed = AttitudeRequest(**json_body(request))
    if not parsed.frames:
        raise ApiError("frames is empty", 400)
    result = analyze_attitude(
        [frame.model_dump() for frame in parsed.frames],
        fps=2.0,
    )
    response = AttitudeResponse(
        metrics=AttitudeMetrics(**result["metrics"]),
        events=[AttitudeEvent(**event) for event in result["events"]],
        summary_text=result["summary_text"],
    )
    return response.model_dump()
