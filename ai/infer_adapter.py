from __future__ import annotations

from typing import Any, Dict, Optional

from ai.state import init_state, set_user_answer, set_question, InterviewState
from ai.graph import build_answer_graph
from ai.question_bank import get_bank


class InterviewEngine:
    """
    [score] | [confidence] | [feedback] | [next_question]
    """

    def __init__(self):
        self._states: Dict[str, InterviewState] = {}
        self._g_answer = build_answer_graph()
        self._bank = get_bank()

    def _get_or_create_state(self, session_id: str) -> InterviewState:
        sid = str(session_id)
        st = self._states.get(sid)
        if st is None:
            st = init_state(sid)
            # 첫 질문을 아직 모를 수 있으므로 placeholder로 시작
            self._states[sid] = st
        return st

    def generate_interview_response(
        self,
        *,
        session_id: Any,
        user_answer: Any,
        settings: Optional[Dict[str, Any]] = None,
        current_question: Optional[str] = None,
        rag_context: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> str:
        """
        호출 규격에 맞게
          _get_ai().generate_interview_response(session_id=..., user_answer=..., settings={...})

        current_question / rag_context를 넘기면 정확도 향상
        """
        st = self._get_or_create_state(str(session_id))

        # 1) 현재 질문 세팅(프론트에서 current_question을 주는 경우 우선)

        qtext = (current_question or st.get("current_question_text") or "자기소개").strip()

        # question_row가 없으면 평가 프롬프트 입력에 맞게 최소 row를 구성
        # (프롬프트는 QUESTION_LIST_ROW가 필요)
        if not st.get("question_row"):
            st["question_row"] = {
                "id": st.get("current_question_id") or "external:current",
                "question": qtext,
                "answer": "",
                "difficulty": (settings or {}).get("difficulty", ""),
                "topic": (settings or {}).get("job_role", ""),
                "subcategory": "",
                "difficulty_score": None,
                "tags": [],
                "code_example": "",
                "time_complexity": "",
                "space_complexity": "",
            }

        st = set_question(
            st,
            question_id=st.get("question_row", {}).get("id", "external:current"),
            question_text=qtext,
            question_row=st.get("question_row"),
        )

        # 2) RAG 컨텍스트가 있으면 추가
        if rag_context is not None:
            st["rag_context"] = rag_context
        else:
            st["rag_context"] = st.get("rag_context") or {}

        # 3) 사용자 답변 세팅
        st = set_user_answer(st, str(user_answer or "").strip())

        # 4) 평가 + 다음질문/꼬리질문 세팅(우리 LangGraph 실행)
        st = self._g_answer.invoke(st)
        self._states[str(session_id)] = st  # 상태 저장

        ev = st.get("last_eval_json") or {}
        score = float(ev.get("score", 0))
        # sentiment_score로 confidence를 저장하므로, 최소한 score 제공
        confidence = score

        feedback = str(ev.get("feedback", "")).strip()
        next_q = str(st.get("current_question_text") or "").strip()

        # 5) 다음 질문이 비어있으면 질문리스트에서 하나 뽑아 채워줌(파싱 실패 대비)
        if not next_q:
            asked = st.get("asked_question_ids", []) or []
            q = self._bank.pick_next(asked)
            asked.append(q.id)
            st["asked_question_ids"] = asked
            next_q = q.question
            st = set_question(st, q.id, q.question, question_row=q.to_dict())
            self._states[str(session_id)] = st
        print(f"[{score}] | [{confidence}] | {feedback} | {next_q}")
        # [점수] | [자신감] | [피드백] | [다음질문]
        return f"[{score}] | [{confidence}] | {feedback} | {next_q}"
    


if __name__ == "__main__":
    engine = InterviewEngine()

    session_id = "sess-cli"

    # 1) 첫 호출(현재 질문을 명시)
    out1 = engine.generate_interview_response(
        session_id=session_id,
        user_answer="잘 모르겠습니다",
        settings={"job_role": "Python 개발자", "difficulty": "middle"},
        current_question="파이썬 GIL(Global Interpreter Lock)이 무엇이며 어떤 영향이 있나요?",
        rag_context={"chunks": []},
    )
    print("OUT1:", out1)
    print()
    # 2) 두 번째 호출(같은 session_id로 이어서)
    out2 = engine.generate_interview_response(
        session_id=session_id,
        user_answer="CPython에서 한 번에 하나의 스레드만 바이트코드를 실행하게 하는 락이고 CPU-bound에서는 이점이 제한됩니다. I/O-bound는 비교적 괜찮고 멀티프로세싱으로 우회할 수 있습니다.",
        settings={"job_role": "Python 개발자", "difficulty": "middle"},
        rag_context={"chunks": []},
    )
    print("OUT2:", out2)
    print('---' * 20)