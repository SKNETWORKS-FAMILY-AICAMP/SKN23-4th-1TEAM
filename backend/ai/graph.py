"""
File: graph.py
Author: 유헌상
Created: 2026-02-23
Description: 랭그래프 생성

Modification History: 
- 2026-02-23 (유헌상): 초기 랭그래프 생성
"""

from __future__ import annotations

from langgraph.graph import StateGraph, END

from backend.ai.state import (
    InterviewState,
    set_question,
    set_evaluation,
    need_follow_up,
    get_follow_up_question,
)
from backend.ai.question_bank import get_bank
from backend.ai.evaluator import evaluate_answer

# 면접관 에이전트 : 라우터의 결정에 따라 실제 사용자에게 던질 대사 세팅함. 꼬리 질문시 이전 질문의 메타데이터(topic, subcategory)를 활용해 관련 질문을 던짐
def node_pick_question(st: InterviewState) -> InterviewState:
    bank = get_bank()
    asked = st.get("asked_question_ids", []) or []

    q = bank.pick_next(asked)

    if q.id not in asked:
        asked.append(q.id)
    st["asked_question_ids"] = asked

    return set_question(st, q.id, q.question, question_row=q.to_dict())


# 평가 에이전트 : 사용자의 답변(ans)과 RAG를 통해 가져온 팩트 데이터(rag_context)를 기반으로 평가
def node_evaluate(st: InterviewState) -> InterviewState:
    question_row = st.get("question_row")
    if not question_row:
        raise RuntimeError("question_row is missing. Run pick_question first.")

    ans = (st.get("last_user_answer_text") or "").strip()
    if not ans:
        ans = "잘 모르겠습니다"
        st["last_user_answer_text"] = ans

    rag_context = st.get("rag_context") or {}

    eval_json, _, _ = evaluate_answer(
        question_row=question_row,
        user_answer_text=ans,
        rag_context=rag_context,
    )

    st = set_evaluation(st, eval_json)
    return st

# 면접관 에이전트 : 라우터의 결정에 따라 실제 사용자에게 던질 대사 세팅함. 꼬리 질문시 이전 질문의 메타데이터(topic, subcategory)를 활용해 관련 질문을 던짐
def node_follow_up(st: InterviewState) -> InterviewState:
    fq = get_follow_up_question(st)
    if not fq:
        fq = "방금 답변에서 가장 자신 없는 부분을 하나 골라 더 구체적으로 설명해보세요."

    base = st.get("current_question_id") or "unknown"
    follow_id = f"followup:{base}"

    st["question_row"] = {
        "id": follow_id,
        "question": fq,
        "answer": "",
        "difficulty": "follow_up",
        "topic": (st.get("last_eval_json") or {}).get("metadata_used", {}).get("topic", ""),
        "subcategory": (st.get("last_eval_json") or {}).get("metadata_used", {}).get("subcategory", ""),
        "difficulty_score": None,
        "tags": [],
        "code_example": "",
        "time_complexity": "",
        "space_complexity": "",
    }

    return set_question(st, follow_id, fq, question_row=st["question_row"])

# 라우터 에이전트 (매니저) : 점수가 70점 미만일 경우 꼬리질문(follow_up), 70점 이상일 경우 새로운 질문(pick_question)
def route_after_eval(st: InterviewState):
    return "follow_up" if need_follow_up(st, threshold=70) else "pick_question"


# 시작시 그래프 
def build_start_graph():
    g = StateGraph(InterviewState)
    g.add_node("pick_question", node_pick_question)
    g.set_entry_point("pick_question")
    g.add_edge("pick_question", END)  # 질문 제시 후 사용자 입력 대기
    return g.compile()

# 답변 후 순환하는 그래프 (무한루프 방지)
def build_answer_graph():
    g = StateGraph(InterviewState)
    g.add_node("evaluate", node_evaluate)
    g.add_node("follow_up", node_follow_up)
    g.add_node("pick_question", node_pick_question)

    g.set_entry_point("evaluate")
    g.add_conditional_edges(
        "evaluate",
        route_after_eval,
        {"follow_up": "follow_up", "pick_question": "pick_question"},
    )
    g.add_edge("follow_up", END)
    g.add_edge("pick_question", END)
    return g.compile()


"""
수정할 부분 
1. node_pick_question : 이력서 기반 + 기술 기반 출제 연동
- 현재 get_bank()를 호출해 고정된 질문 (qustion_pool)에서만 문제 가져옴.
- 여기서 벡터DB(ChromaDB)를 활용해 이력서 기반 + 기술 기반 출제 (1:1)연동 로직 추가하기.
- 이번 턴이 직무 지식을 물어볼지 아니면 이력서 경험(RAG)을 물어볼지 결정하는 로직 추가하기.

2. node_evaluate : 평가 로직 고도화
- 지금은 상태값에 이미 저장된 st.get("rag_context")를 그대로 평가에 사용
- 실제 면접처럼 강점/약점 분석, 개선 방향 제시 등 상세 피드백을 생성하도록 수정하기.
- LLM을 활용해 평가 로직을 더 정교하게 만들기.
- 사용자의 답변(ans) 텍스트 자체를 쿼리로 삼아 ChromaDB를 한 번 더 검색해 오는 로직을 추가
    - 지원자가 답변 중에 이력서에 없는 기술을 언급했는지 팩트 체크용
"""