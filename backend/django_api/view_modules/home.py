from .shared import *  # noqa: F401,F403


@api_view(["GET", "POST"])
def home_memos(request):
    if request.method == "GET":
        limit = int(request.GET.get("limit", 30))
        return {"items": get_all_memos(limit=limit)}

    body = json_body(request)
    with db_session() as db:
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


@api_view(["POST"])
def home_news(request):
    body = json_body(request)
    query = body.get("query", "")
    raw_news = get_web_context_second(query) if query else ""
    summary = get_translated_news_summary(raw_news) if raw_news else ""
    return {"content": summary}


@api_view(["POST"])
def home_guide(request):
    body = json_body(request)
    user_message = body.get("message", "")
    use_web_search = bool(body.get("use_web_search", False))
    web_context = (
        get_web_context_first(user_message)
        if use_web_search and user_message
        else ""
    )
    reply = "".join(get_home_guide_response_stream(user_message, web_context))
    return {"content": reply, "web_context": web_context}


@api_view(["POST"])
def home_proofread_file(request):
    file = request.FILES.get("file")
    document_type = request.POST.get("document_type")
    if not file or not document_type:
        raise ApiError("file and document_type are required", 422)
    content_text = ""
    if file.name.endswith(".pdf"):
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            content_text += (page.extract_text() or "") + "\n"
    else:
        content_text = file.read().decode("utf-8", errors="ignore")
    if not content_text.strip():
        raise ApiError("문서에서 텍스트를 추출할 수 없습니다.", 400)
    return {"feedback": get_proofread_result(content_text, document_type)}
