"""
File: personality_vector_service.py
Author: 유헌상
Created: 2026-03-15
Description: 사용자의 답변을 기준으로 피드백 생성하는 서비스 파일

Modification History:
- 2026-03-15 (유헌상): 초기 생성 (인성면접 답변 피드백 생성)
"""
import os
from openai import OpenAI
from backend.services.personality_vector_service import search_similar_board_answers
from backend.ai.personality_prompts import (
    PERSONALITY_SYSTEM_PROMPT,
    personality_user_prompt,
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def generate_board_answer_feedback(
    question_text: str,
    answer_text: str,
    user_id: int,
):
    query_text = f"[질문]\n{question_text}\n\n[답변]\n{answer_text}"
    similar_results = search_similar_board_answers(
        query_text=query_text,
        user_id=user_id,
        top_k=3,
    )

    docs = similar_results.get("documents", [[]])[0]
    rag_context = "\n\n".join(docs) if docs else "이전 답변 없음"

    user_prompt = personality_user_prompt(
        question_text=question_text,
        answer_text=answer_text,
        rag_context=rag_context,
    )


    response = client.responses.create(
        model="gpt-4.1-mini",
        input=[
            {
                "role": "system",
                "content": PERSONALITY_SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": user_prompt,
            },
        ],
    )

    return response.output_text