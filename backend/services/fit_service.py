# backend/services/fit_service.py
import os
import chromadb
from openai import OpenAI
from backend.ai.fit_prompts import (
    FIT_SYSTEM_PROMPT,
    build_first_answer_prompt,
    build_comparison_prompt,
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
chroma_client = chromadb.PersistentClient(path="backend/data/chroma")
collection = chroma_client.get_or_create_collection("fit_board_answers")


def save_and_evaluate_answer(
    answer_id: int,
    user_id: int,
    question_id: int,
    question_text: str,
    current_answer: str,
) -> str:
    document_text = f"[질문]\n{question_text}\n[답변]\n{current_answer}"
    embed_res = client.embeddings.create(
        model="text-embedding-3-small", input=document_text
    )
    vector_data = embed_res.data[0].embedding

    search_result = collection.query(
        query_embeddings=[vector_data], n_results=1, where={"user_id": user_id}
    )
    docs = search_result.get("documents", [[]])[0]

    # 과거 답변 유무에 따른 분기 처리 및 터미널 출력
    if docs:
        past_answer = docs[0]
        print(
            f"\n[fit_service] 과거 답변 발견됨 - 비교 프롬프트 생성 (user_id: {user_id}, question_id: {question_id})"
        )
        user_prompt = build_comparison_prompt(
            question_text, current_answer, past_answer
        )
    else:
        print(
            f"\n[fit_service] 과거 답변 없음 - 첫 답변 프롬프트 생성 (user_id: {user_id}, question_id: {question_id})"
        )
        user_prompt = build_first_answer_prompt(question_text, current_answer)

    chat_res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": FIT_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
    )
    feedback = chat_res.choices[0].message.content

    # 생성된 피드백을 백엔드 터미널에 전체 출력
    print("\n" + "=" * 50)
    print(f"=== [AI 분석 리포트 확인용 - Answer ID: {answer_id}] ===")
    print(feedback)
    print("=" * 50 + "\n")

    unique_id = f"user_{user_id}_question_{question_id}"
    collection.upsert(
        ids=[unique_id],
        documents=[document_text],
        embeddings=[vector_data],
        metadatas=[
            {"answer_id": answer_id, "user_id": user_id, "question_id": question_id}
        ],
    )

    return feedback
