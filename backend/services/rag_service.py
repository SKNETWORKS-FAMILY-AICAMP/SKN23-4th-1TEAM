"""
File: services/rag_service.py
Description: ChromaDB 기반 RAG 서비스
             - 이력서 텍스트 → 청크 분할 → 임베딩 → ChromaDB 저장
             - 면접 중 질문 주제와 유사한 이력서 청크 검색
"""

import os
import hashlib
from typing import Optional
import chromadb
from chromadb.utils import embedding_functions

# ─── ChromaDB 클라이언트 초기화 ───────────────────────────────
_CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
_COLLECTION_NAME = "resumes"

# OpenAI 임베딩 함수 (text-embedding-3-small 사용, 저렴 + 충분한 품질)
def _get_embed_fn():
    api_key = os.getenv("OPENAI_API_KEY", "")
    return embedding_functions.OpenAIEmbeddingFunction(
        api_key=api_key,
        model_name="text-embedding-3-small",
    )


def _get_collection():
    client = chromadb.PersistentClient(path=_CHROMA_PATH)
    return client.get_or_create_collection(
        name=_COLLECTION_NAME,
        embedding_function=_get_embed_fn(),
        metadata={"hnsw:space": "cosine"},
    )


# ─── 텍스트 청킹 ──────────────────────────────────────────────
def _chunk_text(text: str, chunk_size: int = 400, overlap: int = 80) -> list[str]:
    """
    이력서 텍스트를 의미 단위로 분할합니다.
    - 줄바꿈 기준으로 우선 분리 후 chunk_size 초과 시 슬라이딩 윈도우 적용
    """
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks, current = [], ""

    for para in paragraphs:
        if len(current) + len(para) + 1 <= chunk_size:
            current = (current + "\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            # 단락 자체가 chunk_size보다 길면 슬라이딩 윈도우 적용
            if len(para) > chunk_size:
                for i in range(0, len(para), chunk_size - overlap):
                    chunks.append(para[i:i + chunk_size])
                current = ""
            else:
                current = para

    if current:
        chunks.append(current)

    return [c for c in chunks if len(c) > 30]  # 너무 짧은 청크 제거


# ─── 이력서 저장 (Upsert) ─────────────────────────────────────
def store_resume(resume_text: str, user_id: str = "anonymous") -> int:
    """
    이력서 텍스트를 ChromaDB에 저장합니다.
    동일 user_id의 기존 데이터는 삭제 후 재삽입(Upsert).
    반환값: 저장된 청크 수
    """
    if not resume_text or len(resume_text.strip()) < 50:
        return 0

    collection = _get_collection()

    # 기존 이 유저의 청크 삭제
    try:
        existing = collection.get(where={"user_id": user_id})
        if existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass

    chunks = _chunk_text(resume_text)
    if not chunks:
        return 0

    # 청크별 고유 ID 생성
    ids, documents, metadatas = [], [], []
    for i, chunk in enumerate(chunks):
        chunk_hash = hashlib.md5(f"{user_id}_{i}_{chunk[:50]}".encode()).hexdigest()[:12]
        ids.append(f"resume_{user_id}_{chunk_hash}")
        documents.append(chunk)
        metadatas.append({
            "user_id":    user_id,
            "chunk_idx":  i,
            "total_chunks": len(chunks),
        })

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    return len(chunks)


# ─── 유사 청크 검색 ───────────────────────────────────────────
def retrieve_relevant_chunks(
    query: str,
    user_id: str = "anonymous",
    n_results: int = 3,
) -> list[str]:
    """
    면접 질문/주제와 유사한 이력서 청크를 검색합니다.
    반환값: 유사도 높은 청크 텍스트 리스트
    """
    try:
        collection = _get_collection()
        results = collection.query(
            query_texts=[query],
            n_results=n_results,
            where={"user_id": user_id},
        )
        docs = results.get("documents", [[]])[0]
        return [d for d in docs if d]
    except Exception:
        return []


# ─── 이력서 기반 꼬리질문 힌트 생성 ──────────────────────────
def get_resume_context_for_question(
    user_answer: str,
    user_id: str = "anonymous",
) -> Optional[str]:
    """
    지원자 답변과 연관된 이력서 내용을 찾아
    LLM이 꼬리질문을 생성할 때 쓸 컨텍스트 문자열을 반환합니다.
    """
    chunks = retrieve_relevant_chunks(user_answer, user_id, n_results=3)
    if not chunks:
        return None

    context = "\n---\n".join(chunks)
    return (
        f"[이력서에서 발견된 관련 내용]\n{context}\n"
        f"위 이력서 내용을 참고해서, "
        f"지원자 답변에 이력서에 언급된 구체적 기술/경험을 연결하는 꼬리질문을 생성하세요."
    )


# ─── 이력서 청크 삭제 (세션 종료 시) ─────────────────────────
def clear_resume_for_session(session_id: str) -> None:
    """
    특정 사용자(세션)의 이력서 청크 데이터를 삭제합니다.
    면접 종료 후 보안 및 용량 관리를 위해 호출할 수 있습니다.
    """
    if not session_id:
        return
        
    try:
        collection = _get_collection()
        existing = collection.get(where={"user_id": session_id})
    except Exception as e:
        pass


# ─── 통합 AI 서비스 파사드 (Facade) ──────────────────────────
class AIServiceFacade:
    def __init__(self):
        import sys
        import os
        
        # 1. 현재 파일 위치를 기준으로 최상위 폴더(SKN23-3rd-1TEAM) 경로 찾기
        current_dir = os.path.dirname(os.path.abspath(__file__)) # services/
        backend_dir = os.path.dirname(current_dir)               # backend/
        root_dir = os.path.dirname(backend_dir)                  # SKN23-3rd-1TEAM/
        
        # 2. 파이썬 지도(sys.path)에 최상위 폴더를 강제로 등록!
        if root_dir not in sys.path:
            sys.path.insert(0, root_dir)
            
        # 3. 이제 최상위 폴더 안에 있는 'ai' 폴더를 정상적으로 찾을 수 있습니다!
        from ai.infer_adapter import InterviewEngine
        self.engine = InterviewEngine()

    def ingest_resume(self, file_path: str, session_id: str) -> None:
        import fitz  # PyMuPDF
        text = ""
        try:
            with fitz.open(file_path) as doc:
                for page in doc:
                    text += page.get_text() + "\n"
        except Exception as e:
            text = f"PDF 추출 실패: {e}"
        store_resume(text, session_id)

    def generate_interview_response(self, session_id: str, user_answer: str, settings: dict) -> str:
        chunks = retrieve_relevant_chunks(user_answer, session_id, n_results=3)
        rag_context = {"chunks": chunks} if chunks else None
        
        return self.engine.generate_interview_response(
            session_id=session_id,
            user_answer=user_answer,
            settings=settings,
            rag_context=rag_context
        )

    def append_interview_log(self, session_id: str, role: str, content: str) -> None:
        import hashlib
        import time
        try:
            collection = _get_collection()
            text = f"[{role}] {content}"
            if len(text.strip()) > 10:
                chunk_hash = hashlib.md5(f"{session_id}_{time.time()}_{text[:50]}".encode()).hexdigest()[:12]
                collection.add(
                    ids=[f"log_{session_id}_{chunk_hash}"],
                    documents=[text],
                    metadatas=[{"user_id": session_id, "type": "interview_log"}]
                )
        except Exception:
            pass

    def stt_whisper(self, audio_data) -> str:
        from backend.services.local_inference import local_stt
        audio_bytes = audio_data.read() if hasattr(audio_data, "read") else audio_data
        return local_stt(audio_bytes)

    def tts_voice(self, text: str) -> bytes:
        from backend.services.local_inference import local_tts
        return local_tts(text)

_ai_service_instance = AIServiceFacade()

def get_ai_service() -> AIServiceFacade:
    return _ai_service_instance