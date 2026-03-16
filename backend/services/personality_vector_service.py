"""
File: personality_vector_service.py
Author: 유헌상
Created: 2026-03-15
Description: 인성면접 답변을 벡터 DB에 저장하고 답변 검색 서비스

Modification History:
- 2026-03-15 (유헌상): 초기 생성 (인성면접 답변을 벡터 DB에 저장하고 검색하는 로직)
"""
import os
import chromadb
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

chroma_client = chromadb.PersistentClient(path="backend/data/chroma")
collection = chroma_client.get_or_create_collection("personality_board_answers")


def build_board_answer_document(question_text: str, answer_text: str) -> str:
    return f"[질문]\n{question_text}\n\n[답변]\n{answer_text}"


def save_board_answer_to_vector_db(
    answer_id: int,
    user_id: int,
    question_id: int,
    question_text: str,
    answer_text: str,
):
    document = build_board_answer_document(question_text, answer_text)

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=document,
    )
    embedding = response.data[0].embedding

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


def search_similar_board_answers(
    query_text: str,
    user_id: int | None = None,
    top_k: int = 3,
):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=query_text,
    )
    query_embedding = response.data[0].embedding

    where = {"user_id": user_id} if user_id is not None else None

    result = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where,
    )
    return result


def debug_get_vector_document(answer_id: int):
    return collection.get(ids=[f"board_answer_{answer_id}"], )