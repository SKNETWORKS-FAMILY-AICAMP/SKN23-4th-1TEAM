from .shared import *  # noqa: F401,F403


@api_view(["GET", "POST"])
def resumes_collection(request):
    if request.method == "GET":
        user_id = int(request.GET.get("user_id", 0))
        return {"items": get_user_resumes(user_id)}
    body = json_body(request)
    analysis_result = body.get("analysis_result")
    if analysis_result is None:
        analysis_result = analyze_resume_comprehensive(body["resume_text"], body["job_role"])
    resume_id = save_user_resume(
        user_id=body["user_id"],
        title=body["title"],
        job_role=body["job_role"],
        resume_text=body["resume_text"],
        analysis_result=analysis_result,
    )
    return {"id": resume_id, "analysis_result": analysis_result}


@api_view(["GET"])
def resumes_latest(request):
    user_id = int(request.GET.get("user_id", 0))
    if not user_id or user_id <= 0:
        return {"user_id": user_id, "job_role": None, "analysis_result": None}
    with db_session() as db:
        job_role, analysis_result = get_latest_resume_fields(db, str(user_id))
    return {"user_id": user_id, "job_role": job_role, "analysis_result": analysis_result}


@api_view(["DELETE"])
def resumes_delete(request, resume_id: int):
    delete_user_resume(resume_id)
    return {"ok": True}
