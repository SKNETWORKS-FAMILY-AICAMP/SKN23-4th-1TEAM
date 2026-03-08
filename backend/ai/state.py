from __future__ import annotations

from typing import Any, Dict, List, Optional, TypedDict, Literal


Stage = Literal["pick_question", "await_answer", "evaluate", "follow_up", "end"]


class InterviewState(TypedDict, total=False):
    """
    LangGraph가 들고 다니는 세션 상태(State)
    - 흐름: PICK_QUESTION -> (프론트 입력) -> EVALUATE -> (조건) FOLLOW_UP -> EVALUATE ...
    """

    # 세션 식별
    session_id: str

    # 진행 상태
    stage: Stage

    # 중복 방지용: 이미 출제한 question_id들
    asked_question_ids: List[str]

    # 현재 질문(화면에 보여줄 질문)
    current_question_id: Optional[str]
    current_question_text: Optional[str]

    # 사용자 최신 답변(STT 텍스트; 현재는 텍스트 입력)
    last_user_answer_text: Optional[str]

    # 평가 결과(JSON 원문 그대로 저장)
    last_eval_json: Optional[Dict[str, Any]]
    last_score: Optional[int]

    # (선택) 턴 누적 기록: DB 저장/리포트에 유용
    history: List[Dict[str, Any]]

    # (선택) RAG 결과(팀원 지우가 넘겨주는 컨텍스트)
    rag_context: Optional[Dict[str, Any]]

    # (선택) 현재 질문 row(질문은행에서 조회한 1개 row)
    question_row: Optional[Dict[str, Any]]


def init_state(session_id: str) -> InterviewState:
    """
    새 세션 시작 시 초기 상태 생성
    """
    return {
        "session_id": session_id,
        "stage": "pick_question",
        "asked_question_ids": [],
        "current_question_id": None,
        "current_question_text": None,
        "last_user_answer_text": None,
        "last_eval_json": None,
        "last_score": None,
        "history": [],
        "rag_context": None,
        "question_row": None,
    }


def set_question(st: InterviewState, question_id: str, question_text: str, question_row: Optional[Dict[str, Any]] = None) -> InterviewState:
    """
    PICK_QUESTION 노드가 호출: 현재 질문 세팅
    """
    st["current_question_id"] = str(question_id)
    st["current_question_text"] = str(question_text)
    if question_row is not None:
        st["question_row"] = question_row
    st["stage"] = "await_answer"
    return st


def set_user_answer(st: InterviewState, answer_text: str) -> InterviewState:
    """
    프론트가 답변을 보내면 호출: 사용자 답변 저장
    """
    st["last_user_answer_text"] = answer_text
    st["stage"] = "evaluate"
    return st


def set_evaluation(st: InterviewState, eval_json: Dict[str, Any]) -> InterviewState:
    """
    EVALUATE 노드가 호출: 평가 결과 저장 + 히스토리 누적
    """
    st["last_eval_json"] = eval_json
    try:
        st["last_score"] = int(eval_json.get("score")) if eval_json.get("score") is not None else None
    except Exception:
        st["last_score"] = None

    # 턴 기록 누적 (팀 B DB 저장 시 그대로 INSERT 가능)
    st["history"].append(
        {
            "question_id": st.get("current_question_id"),
            "question_text": st.get("current_question_text"),
            "user_answer_text": st.get("last_user_answer_text"),
            "eval_json": eval_json,
        }
    )
    return st


def need_follow_up(st: InterviewState, threshold: int = 70) -> bool:
    """
    Conditional Edge에서 사용할 분기 조건
    - 기본: score < 70이면 꼬리질문 루프
    """
    score = st.get("last_score")
    if score is None:
        return True  # 점수 파싱 실패면 안전하게 follow-up로
    return score < threshold


def get_follow_up_question(st: InterviewState) -> str:
    """
    FOLLOW_UP 노드가 사용할 꼬리질문 텍스트 추출
    """
    ej = st.get("last_eval_json") or {}
    q = ej.get("follow_up_question", "")
    return str(q or "").strip()