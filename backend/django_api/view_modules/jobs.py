from .shared import *  # noqa: F401,F403


@api_view(["POST"])
def jobs_search(request):
    body = json_body(request)
    query = JobsSearchQuery(**body)
    params = {"startPage": query.startPage, "display": query.display}
    if query.empCoNo:
        params["empCoNo"] = query.empCoNo
    if query.jobsCd:
        params["jobsCd"] = query.jobsCd
    if query.empWantedTitle:
        params["empWantedTitle"] = query.empWantedTitle
    if query.sortField:
        params["sortField"] = query.sortField
    if query.sortOrderBy:
        params["sortOrderBy"] = query.sortOrderBy
    for field in ("coClcd", "empWantedTypeCd", "empWantedCareerCd", "empWantedEduCd"):
        value = _join_multi(getattr(query, field))
        if value:
            params[field] = value
    try:
        return run_async(fetch_jobs(params))
    except ExternalJobsAPIError as exc:
        raise ApiError(str(exc), 502) from exc
