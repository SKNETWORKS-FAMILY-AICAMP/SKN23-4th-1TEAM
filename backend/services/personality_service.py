"""
File: personality_service.py
Description: 인성면접 게시판 답변의 벡터 저장, 검색, AI 피드백 생성을 통합한 서비스
"""
import os
import chromadb
from openai import OpenAI
from backend.ai.personality_prompts import (
    PERSONALITY_SYSTEM_PROMPT,
    build_first_answer_prompt,
    build_comparison_prompt,
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
chroma_client = chromadb.PersistentClient(path="backend/data/chroma")
collection = chroma_client.get_or_create_collection("personality_board_answers")


def _build_document(question_text: str, answer_text: str) -> str:
    return f"[질문]\n{question_text}\n\n[답변]\n{answer_text}"


def _embed(text: str) -> list[float]:
    res = client.embeddings.create(model="text-embedding-3-small", input=text)
    return res.data[0].embedding


def _call_llm(user_prompt: str) -> str:
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": PERSONALITY_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    return res.choices[0].message.content


def save_board_answer_to_vector_db(
    answer_id: int,
    user_id: int,
    question_id: int,
    question_text: str,
    answer_text: str,
):
    """답변을 벡터 DB에 저장한다."""
    document = _build_document(question_text, answer_text)
    embedding = _embed(document)
    collection.upsert(
        ids=[f"board_answer_{answer_id}"],
        documents=[document],
        embeddings=[embedding],
        metadatas=[{
            "answer_id": answer_id,
            "user_id": user_id,
            "question_id": question_id,
            "source": "board_answer",
        }],
    )


def generate_board_answer_feedback(
    question_text: str,
    answer_text: str,
    user_id: int,
    question_id: int | None = None,
) -> str:
    """과거 답변을 RAG로 참조하여 AI 피드백을 생성한다."""
    query_text = _build_document(question_text, answer_text)
    query_embedding = _embed(query_text)

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=3,
        where={"user_id": user_id},
    )
    docs = result.get("documents", [[]])[0]

    if docs:
        user_prompt = build_comparison_prompt(question_text, answer_text, docs[0])
    else:
        user_prompt = build_first_answer_prompt(question_text, answer_text)

    return _call_llm(user_prompt)


def save_and_evaluate_answer(
    answer_id: int,
    user_id: int,
    question_id: int,
    question_text: str,
    current_answer: str,
) -> str:
    """답변 제출 시 호출: 과거 답변과 비교하여 피드백을 생성하고 벡터 DB에 저장한다."""
    document = _build_document(question_text, current_answer)
    embedding = _embed(document)

    result = collection.query(
        query_embeddings=[embedding],
        n_results=1,
        where={"user_id": user_id},
    )
    docs = result.get("documents", [[]])[0]

    if docs:
        print(f"\n[personality_service] 과거 답변 발견됨 - 비교 프롬프트 생성 (user_id: {user_id}, question_id: {question_id})")
        user_prompt = build_comparison_prompt(question_text, current_answer, docs[0])
    else:
        print(f"\n[personality_service] 과거 답변 없음 - 첫 답변 프롬프트 생성 (user_id: {user_id}, question_id: {question_id})")
        user_prompt = build_first_answer_prompt(question_text, current_answer)

    feedback = _call_llm(user_prompt)

    print("\n" + "=" * 50)
    print(f"=== [AI 분석 리포트 확인용 - Answer ID: {answer_id}] ===")
    print(feedback)
    print("=" * 50 + "\n")

    collection.upsert(
        ids=[f"board_answer_{answer_id}"],
        documents=[document],
        embeddings=[embedding],
        metadatas=[{
            "answer_id": answer_id,
            "user_id": user_id,
            "question_id": question_id,
            "source": "board_answer",
        }],
    )

    return feedback


def debug_get_vector_document(answer_id: int):
    return collection.get(ids=[f"board_answer_{answer_id}"])
