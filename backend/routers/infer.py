"""
File: infer.py
Author: 양창일
Created: 2026-02-15
Description: AI 실행해주는 API 주소

Modification History:
- 2026-02-15: 초기 생성
- 2026-02-22: RAG + DB 질문 풀 기반 AI 면접 실행 및 기록 API 통합, 면접 종료 시 최종 점수 계산 및 세션 정보 업데이트
"""
from fastapi import APIRouter, Depends, Request, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.db.session import get_db
from backend.db import base  # JobCategory, QuestionPool, InterviewDetail 등 포함
from backend.schemas.infer_schema import InferRequest, InferResponse
from backend.services.rag_service import get_ai_service  # 통합된 AI 서비스
from backend.services import auth_service
from backend.models.user import User

router = APIRouter(prefix="/api/infer", tags=["infer"])
# ✅ 서버 시작 시 즉시 초기화하지 않고, 실제 요청 시점에 초기화 (OpenAI/Chroma 블로킹 방지)
def _get_ai():
    return get_ai_service()

def require_user(req: Request, db: Session) -> User:
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="인증되지 않은 사용자입니다.")
    token = auth.split(" ", 1)[1].strip()
    user = auth_service.get_user_from_access(db, token)
    if not user:
        raise HTTPException(status_code=401, detail="유효하지 않은 토큰입니다.")
    return user

@router.post("/ingest")
async def ingest_resume(file: UploadFile = File(...), session_id: str = "default"):
    """이력서 PDF 수신 및 벡터 DB 학습
    ⚠️ OpenAI 임베딩 + PDF 처리는 동기 블로킹 작업이므로
       run_in_executor로 스레드 풀에 위임 (이벤트 루프 블로킹 방지)
    """
    import os
    import asyncio

    contents  = await file.read()
    file_path = f"temp_{file.filename}"
    with open(file_path, "wb") as buffer:
        buffer.write(contents)

    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _get_ai().ingest_resume, file_path, session_id)

    os.remove(file_path)
    return {"message": "이력서 분석 완료"}

@router.post("/start")
def start_interview(req: Request, body: dict, db: Session = Depends(get_db)):
    """새로운 면접 세션을 생성하고 자동 증가된 session_id를 반환.
    ✅ 인증은 선택적: 토큰이 있으면 user_id 연결, 없으면 게스트 세션으로 생성
    """
    # 토큰이 있을 때만 유저 확인 (없어도 면접 시작 가능)
    user_id = None
    try:
        auth = req.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            token = auth.split(" ", 1)[1].strip()
            user = auth_service.get_user_from_access(db, token)
            if user:
                user_id = user.id
    except Exception:
        pass

    job_role = body.get("job_role", "개발자")

    new_session = base.InterviewSession(
        user_id=user_id,
        job_role=job_role,
        status="START"
    )
    db.add(new_session)
    db.commit()
    db.refresh(new_session)
    return {"session_id": new_session.id}


@router.post("/ask", response_model=dict)
def ask_next_question(req: Request, body: dict, db: Session = Depends(get_db)):
    """
    사용자 답변을 분석하고, DB 질문 풀과 이력서를 참고하여 다음 질문 생성
    """
    user = require_user(req, db)
    
    user_answer = body.get("answer")
    session_id = body.get("session_id")
    job_role = body.get("job_role", "Python 개발자")
    difficulty = body.get("difficulty", "미들")
    
    # 🔥 프론트엔드에서 계산해서 보낸 소요 시간 및 현재 질문 텍스트 파싱
    response_time = body.get("response_time", 0)
    current_question = body.get("current_question", "자기소개")

    # 1. 500개 질문 DB에서 해당 직무/난이도 질문 랜덤 추출
    question_record = db.query(base.QuestionPool).join(base.JobCategory).filter(
        base.JobCategory.target_role == job_role,
        base.QuestionPool.difficulty == difficulty
    ).order_by(func.rand()).first()

    # 2. AI 서비스(RAG + GPT-4o-mini) 호출
    # 이력서 문맥과 사용자 답변을 대조하여 피드백 및 다음 질문 생성
    ai_result_raw = _get_ai().generate_interview_response(
        session_id=session_id,
        user_answer=user_answer,
        settings={"job_role": job_role, "difficulty": difficulty}
    )

    # 3. 결과 파싱 (형식: [점수] | [자신감] | [피드백] | [다음질문])
    try:
        score_str, conf_str, feedback, next_q = [p.strip() for p in ai_result_raw.split("|")]
        score = float(score_str.strip("[]"))
        confidence = float(conf_str.strip("[]"))
    except ValueError:
        # 파싱 실패 시 기본 질문 제공
        score, confidence, feedback, next_q = 0.0, 0.0, "분석 중", question_record.content if question_record else "다음 질문입니다."

    # 4. 💾 일반 DB(MySQL)에 문항별 상세 내역 저장 (소요 시간 및 실제 질문 텍스트 포함)
    new_detail = base.InterviewDetail(
        session_id=session_id,
        question_text=current_question, 
        answer_text=user_answer,
        response_time=int(response_time),
        score=score,
        sentiment_score=confidence,
        feedback=feedback
    )
    db.add(new_detail)
    db.commit()

    # 5. 실시간 대화 내용을 벡터 DB에 추가 (동적 RAG)
    _get_ai().append_interview_log(session_id, "이전 질문", user_answer)

    return {
        "answer": next_q,
        "score": score,
        "feedback": feedback,
        "session_id": session_id
    }

@router.post("/save")
def save_final_result(body: dict, db: Session = Depends(get_db)):
    """면접 종료 후 최종 점수 합산 및 세션 종료"""
    session_id = body.get("session_id")
    # 세션 내 모든 문항의 평균 점수 계산 로직 등을 추가하세요.
    return {"message": "면접 결과가 성공적으로 저장되었습니다."}


@router.post("/end")
def end_interview(body: dict, db: Session = Depends(get_db)):
    """
    면접 종료 시 호출: 개별 문항 점수 합산 및 최종 결과 저장
    """
    session_id = body.get("session_id")
    
    # 1. 해당 세션의 모든 답변 점수 가져오기
    results = db.query(
        func.avg(base.InterviewDetail.score).label('avg_score'),
        func.avg(base.InterviewDetail.sentiment_score).label('avg_sentiment')
    ).filter(base.InterviewDetail.session_id == session_id).first()

    if not results or results.avg_score is None:
        raise HTTPException(status_code=404, detail="면접 기록을 찾을 수 없습니다.")

    # 2. interview_sessions 테이블 업데이트 (최종 점수 및 상태 변경)
    session_record = db.query(base.InterviewSession).filter(
        base.InterviewSession.id == session_id
    ).first()
    
    if session_record:
        session_record.total_score = round(results.avg_score, 2)
        session_record.status = "COMPLETED" # 면접 완료 상태로 변경
        db.commit()

    return {
        "message": "면접이 종료되었습니다.",
        "final_score": round(results.avg_score, 2),
        "avg_confidence": round(results.avg_sentiment, 2)
    }


@router.post("/stt")
async def speech_to_text(file: UploadFile = File(...)):
    """Whisper 모델을 이용한 음성 -> 텍스트 변환"""
    import os
    # 임시 파일 저장 후 Whisper 호출
    content = await file.read()
    temp_filename = f"temp_{file.filename}.wav"
    with open(temp_filename, "wb") as f:
        f.write(content)
    
    # 지연 초기화된 AI 서비스의 STT 호출
    with open(temp_filename, "rb") as audio_data:
        text = _get_ai().stt_whisper(audio_data)
    
    os.remove(temp_filename)
    return {"text": text}

from fastapi.responses import Response

@router.post("/tts")
def text_to_speech(body: dict):
    """텍스트를 받아 OpenAI TTS 음성 바이너리로 응답"""
    text = body.get("text", "")
    if not text:
        raise HTTPException(status_code=400, detail="텍스트가 제공되지 않았습니다.")
    
    try:
        audio_content = _get_ai().tts_voice(text)
        return Response(content=audio_content, media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"TTS 생성 실패: {str(e)}")