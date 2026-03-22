from .shared import *  # noqa: F401,F403
from backend.django_api.utils import (
    api_view,
    json_body,
    run_async,
    ApiError,
    infer_jobs_cd_value,
    resolve_emp_wanted_title,
)


@api_view(["POST"])
def jobs_search(request):
    body = json_body(request)

    start_page = body.get("startPage", 1)
    display = body.get("display", 10)
    emp_co_no = body.get("empCoNo")
    co_clcd = body.get("coClcd")
    jobs_cd = body.get("jobsCd")
    emp_wanted_title = body.get("empWantedTitle")
    sort_field = body.get("sortField")
    sort_order_by = body.get("sortOrderBy")
    job_role = body.get("jobRole")
    keywords = body.get("keywords")

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

    resolved_title = resolve_emp_wanted_title(
        emp_wanted_title=emp_wanted_title,
        keywords=keywords,
        job_role=job_role,
    )

    resolved_jobs_cd = jobs_cd or infer_jobs_cd_value(job_role)
    if resolved_jobs_cd:
        base_params["jobsCd"] = resolved_jobs_cd

    if resolved_title:
        base_params["empWantedTitle"] = resolved_title

    resolved_jobs_cd = "133100|133101|133102|133200|133201|133202|133203|133204|133205|133206|133207|133300|133301|133302|133900"
    base_params["jobsCd"] = resolved_jobs_cd
    try:
        return run_async(fetch_jobs(base_params))
    except ExternalJobsAPIError as e:
        raise ApiError(str(e), 502)
    