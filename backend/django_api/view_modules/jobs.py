from .shared import *  # noqa: F401,F403
from backend.django_api.utils import (
    api_view,
    json_body,
    run_async,
    ApiError,
    infer_jobs_cd_value,
)


@api_view(["POST"])
def jobs_search(request):
    body = json_body(request)

    start_page = body.get("startPage", 1)
    display = body.get("display", 10)
    emp_co_no = body.get("empCoNo")
    co_clcd = body.get("coClcd")
    jobs_cd = body.get("jobsCd")
    sort_field = body.get("sortField")
    sort_order_by = body.get("sortOrderBy")
    job_role = body.get("jobRole")
    base_params: dict[str, str | int] = {
        "startPage": start_page,
        "display": display,
    }

    if emp_co_no:
        base_params["empCoNo"] = emp_co_no

    if sort_field:
        base_params["sortField"] = sort_field
    if sort_order_by:
        base_params["sortOrderBy"] = sort_order_by

    v = _join_multi(co_clcd)
    if v:
        base_params["coClcd"] = v

    resolved_jobs_cd = jobs_cd or infer_jobs_cd_value(job_role)
    if resolved_jobs_cd:
        base_params["jobsCd"] = resolved_jobs_cd

    try:
        return run_async(fetch_jobs(base_params))
    except ExternalJobsAPIError as e:
        raise ApiError(str(e), 502)
    