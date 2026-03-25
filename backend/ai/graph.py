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
    st["follow_up_count"] = 0  # 새 질문 시 꼬리질문 횟수 초기화

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
    
    st["follow_up_count"] = st.get("follow_up_count", 0) + 1  # 꼬리질문 횟수 증가

    return set_question(st, follow_id, fq, question_row=st["question_row"])

# 라우터 에이전트 (매니저) : 꼬리질문 로직에 따라 분기
def route_after_eval(st: InterviewState):
    return "follow_up" if need_follow_up(st) else "pick_question"


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
