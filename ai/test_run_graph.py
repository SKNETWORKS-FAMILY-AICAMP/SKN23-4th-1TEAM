import os
import json
from datetime import datetime

from ai.state import init_state, set_user_answer
from ai.graph import build_start_graph, build_answer_graph


def append_jsonl(path: str, obj: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def main():
    g_start = build_start_graph()
    g_answer = build_answer_graph()

    session_id = f"sess-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    st = init_state(session_id)

    log_path = os.path.join("ai/logs", f"session_{session_id}.jsonl")

    # 첫 질문
    st = g_start.invoke(st)

    while True:
        qid = st.get("current_question_id")
        qtext = st.get("current_question_text")
        print("\nQ:", qtext)

        user_text = input("A 입력(종료: /q): ").strip()
        if user_text.lower() == "/q":
            break

        st = set_user_answer(st, user_text)

        # 평가 + 다음 질문 세팅
        st = g_answer.invoke(st)

        ev = st.get("last_eval_json") or {}
        print("\nscore:", ev.get("score"), "passed:", ev.get("passed"))
        print("feedback:", ev.get("feedback"))

        # Q/A 저장 확인용
        record = {
            "ts": datetime.now().isoformat(),
            "session_id": session_id,
            "question_id": qid,
            "question": qtext,
            "answer_text": user_text,
            "evaluation": ev,  # JSON 그대로 저장
            "next_question_id": st.get("current_question_id"),
            "next_question": st.get("current_question_text"),
        }
        append_jsonl(log_path, record)
        print(f"\n[저장됨] {log_path}")

        if not st.get("current_question_text"):
            print("\n다음 질문이 없어 종료합니다.")
            break


if __name__ == "__main__":
    main()