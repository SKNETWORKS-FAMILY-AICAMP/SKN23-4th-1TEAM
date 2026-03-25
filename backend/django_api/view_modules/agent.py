from .shared import *  # noqa: F401,F403


@api_view(["POST"])
def agent_chat(request):
    body = AgentChatRequest(**json_body(request))
    try:
        return run_agent(body.message)
    except Exception as exc:
        raise ApiError("에이전트 처리 중 서버 오류가 발생했습니다.", 500) from exc
