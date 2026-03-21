from .shared import *  # noqa: F401,F403


@api_view(["POST"])
def agent_chat(request):
    body = AgentChatRequest(**json_body(request))
    try:
        return run_agent(body.message)
    except Exception as exc:
        raise ApiError("?먯씠?꾪듃 泥섎━ 以??쒕쾭 ?ㅻ쪟媛 諛쒖깮?덉뒿?덈떎.", 500) from exc
