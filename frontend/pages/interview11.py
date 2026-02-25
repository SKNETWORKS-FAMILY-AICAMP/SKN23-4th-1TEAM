"""
File: chatbot.py
Author: 김다빈, 김지우
Created: 2026-02-21
Description: AI 면접관 채팅 페이지 (통합본)
             - 텍스트/실시간 음성 면접 모드 (OpenAI Realtime API)
             - ChromaDB RAG 기반 이력서 맞춤 꼬리질문
             - MySQL 세션/상세 기록 자동 저장 및 자동 채점

Modification History:
- 2026-02-21 (김다빈): 초기 생성
- 2026-02-22 (김다빈): STT/TTS 연동, 면접 종료 시 GPT-4o 피드백
- 2026-02-22 (김다빈): 실시간 음성 면접 모드 추가
- 2026-02-23 (김다빈): 실시간 음성 컴포넌트 한국어 번역 및 UI 개선
- 2026-02-23 (김다빈): 세션 상태 캐싱 적용
- 2026-02-23 (김지우): RAG(ChromaDB) 및 MySQL DB 연동, 페르소나/채점 로직 통합
"""

import streamlit as st
import os
import sys

# 외부 패키지 경로
_EXT_PKG_PATH = "/tmp/fw_pkg"
if os.path.isdir(_EXT_PKG_PATH) and _EXT_PKG_PATH not in sys.path:
    sys.path.insert(0, _EXT_PKG_PATH)

# ─── 경로 설정: backend/ 와 프로젝트 루트 모두 sys.path에 추가 ───
# • _BACKEND_PATH → `from db.database import ...` 처럼 backend 내부 모듈 직접 임포트
# • _PROJECT_ROOT  → `from backend.db import ...`  처럼 backend를 패키지로 임포트
_PROJECT_ROOT  = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_BACKEND_PATH  = os.path.join(_PROJECT_ROOT, "backend")
for _p in (_PROJECT_ROOT, _BACKEND_PATH):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

# ─── 내부 모듈 (지우님 코어 로직 임포트) ──────────────────────────────
from db.database import (
    init_db, create_session, end_session, save_detail,
    get_questions_by_role, get_common_questions
)
from services.rag_service import InterviewAIService

# ─── 서비스 인스턴스 (지연 생성) ────────────────────────────────
_ai_svc: InterviewAIService | None = None
def _get_svc() -> InterviewAIService:
    global _ai_svc
    if _ai_svc is None:
        _ai_svc = InterviewAIService()
    return _ai_svc

# ─── 래퍼 함수 (interview.py 전용) ──────────────────────────────
def store_resume(text: str, user_id: str):
    """이력서 텍스트를 ChromaDB에 저장합니다."""
    import tempfile, os
    svc = _get_svc()
    # InterviewAIService.ingest_resume는 파일 경로를 받으므로 임시 파일로 저장
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write(text)
        tmp_path = f.name
    try:
        svc.vector_db.add_texts(
            texts=[text],
            metadatas=[{"source": "resume", "session_id": str(user_id)}]
        )
    finally:
        os.unlink(tmp_path)

def get_ai_response(
    messages: list, job_role: str, difficulty: str,
    q_count: int, persona_style: str, resume_text: str | None, user_id: str
) -> str:
    """대화 히스토리를 바탕으로 AI 면접관 응답을 생성합니다."""
    from openai import OpenAI as _OAI
    client = _OAI(api_key=os.getenv("OPENAI_API_KEY"))

    answered = sum(1 for m in messages if m["role"] == "user")
    end_signal = "\n\n답변이 완료되면 '[INTERVIEW_END]' 를 응답 마지막에 추가하세요." if answered >= q_count else ""

    system_prompt = f"""당신은 {job_role} 전문 면접관입니다. 스타일: {persona_style}. 난이도: {difficulty}.
총 {q_count}개 질문. 지원자 답변에 짧은 피드백 후 다음 질문을 하거나, 꼬리질문(💡 추가 질문:)을 던지세요.
{'이력서 요약:\n' + resume_text[:800] if resume_text else ''}{end_signal}"""

    chat_history = [{"role": "system", "content": system_prompt}]
    for m in messages:
        chat_history.append({"role": m["role"], "content": m["content"]})

    resp = client.chat.completions.create(model="gpt-4o-mini", messages=chat_history, temperature=0.7)
    return resp.choices[0].message.content

def score_answer(question: str, answer: str, job_role: str) -> tuple[float, str]:
    """답변을 채점하고 (점수, 피드백) 튜플을 반환합니다."""
    from openai import OpenAI as _OAI
    client = _OAI(api_key=os.getenv("OPENAI_API_KEY"))
    prompt = f"""다음 면접 답변을 0~10점으로 채점하고 한 줄 피드백을 주세요.
직무: {job_role}
질문: {question}
답변: {answer}

반드시 아래 형식으로만 답하세요:
점수: <숫자>
피드백: <한 줄>"""
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        raw = resp.choices[0].message.content
        lines = {l.split(":")[0].strip(): ":".join(l.split(":")[1:]).strip() for l in raw.splitlines() if ":" in l}
        score = float(lines.get("점수", 5))
        feedback = lines.get("피드백", "")
        return score, feedback
    except Exception:
        return 5.0, ""

def generate_evaluation(
    messages: list, job_role: str, difficulty: str, resume_text: str | None
) -> str:
    """전체 면접 내용을 바탕으로 종합 평가 리포트를 생성합니다."""
    from openai import OpenAI as _OAI
    client = _OAI(api_key=os.getenv("OPENAI_API_KEY"))
    script = "\n".join([f"[{'면접관' if m['role']=='assistant' else '지원자'}] {m['content']}" for m in messages])
    prompt = f"""아래 {job_role} ({difficulty}) 면접 내용을 분석하여 종합 평가 리포트(마크다운)를 작성해주세요.
{'이력서: ' + resume_text[:500] if resume_text else ''}

[면접 스크립트]
{script[:3000]}

## 평가 항목
- 기술 역량
- 커뮤니케이션
- 논리적 사고
- 개선 포인트
- 합격 가능성 및 총평"""
    try:
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        return resp.choices[0].message.content
    except Exception as e:
        return f"평가 생성 실패: {e}"

# ─── streamlit-realtime-audio 임포트 ──────────────────────────────
try:
    from st_realtime_audio import realtime_audio_conversation
    _REALTIME_AVAILABLE = True
except ImportError:
    _REALTIME_AVAILABLE = False

# --- 페이지 설정 ---
st.set_page_config(page_title="AI 면접관", page_icon="🎯", layout="centered")

# DB 초기화 (최초 1회)
try:
    init_db()
except Exception as e:
    st.warning(f"DB 초기화 실패 (MySQL 연결을 확인하세요): {e}")

# ============================================================
# CSS — 다빈님의 라이트 테마 + 지우님의 뱃지 UI 결합
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
* { font-family: 'Noto Sans KR', sans-serif !important; box-sizing: border-box; }

html, body, .stApp,
[data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main {
    background-color: #f5f5f5 !important;
}
[data-testid="stHeader"] { background: transparent !important; }
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

.block-container { max-width: 680px !important; padding-top: 1.5rem !important; padding-bottom: 5rem !important; }
h1, h2, h3, p, div, span, label { color: #333 !important; }

/* ─── 카드 ─── */
.setup-card { background: #fff; border-radius: 16px; box-shadow: 0 2px 16px rgba(0,0,0,0.08); padding: 36px 32px; margin-bottom: 24px; }
.page-title { font-size: 26px; font-weight: 700; color: #bb38d0 !important; text-align: center; margin-bottom: 6px; }
.page-subtitle { font-size: 14px; color: #888 !important; text-align: center; margin-bottom: 0; }

/* ─── 채팅 헤더 & 뱃지 ─── */
.chat-header { display: flex; align-items: center; gap: 12px; background: #fff; border-radius: 14px; box-shadow: 0 1px 8px rgba(0,0,0,0.06); padding: 14px 20px; margin-bottom: 16px; }
.chat-header-icon { width: 40px; height: 40px; border-radius: 10px; background: #bb38d0; display: flex; align-items: center; justify-content: center; font-size: 18px; color: #fff; flex-shrink: 0; }
.chat-header-name { font-size: 16px; font-weight: 700; color: #333 !important; }
.chat-header-info { font-size: 12px; color: #999 !important; }

.persona-badge { display: inline-block; background: linear-gradient(135deg, #bb38d0, #7b2cb1); color: white !important; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; margin-left: 8px; }
.followup-badge { display: inline-block; background: #fff3e0; color: #e67e22 !important; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 6px; margin-bottom: 6px; }
.score-mini { display: inline-block; background: #f0fdf4; color: #16a34a !important; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 6px; margin-top: 4px; }

/* ─── 메시지 버블 ─── */
.ai-bubble { background: #fff; border: 1px solid #eee; border-radius: 16px; border-top-left-radius: 4px; padding: 14px 18px; max-width: 80%; color: #333 !important; font-size: 15px; line-height: 1.7; margin-bottom: 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.04); white-space: pre-wrap; }
.user-bubble { background: #bb38d0; border-radius: 16px; border-top-right-radius: 4px; padding: 14px 18px; max-width: 80%; color: #fff !important; font-size: 15px; line-height: 1.7; margin-bottom: 10px; box-shadow: 0 2px 8px rgba(187,56,208,0.2); white-space: pre-wrap; }
.sender-label { font-size: 11px; color: #bb38d0 !important; font-weight: 700; margin-bottom: 4px; }

/* ─── 기타 컴포넌트 ─── */
[data-testid="stButton"] > button[kind="primary"] { background-color: #bb38d0 !important; color: #fff !important; border: none !important; border-radius: 8px !important; height: 50px !important; font-size: 16px !important; font-weight: 700 !important; transition: background 0.15s; }
[data-testid="stButton"] > button[kind="primary"]:hover { background-color: #a02db5 !important; }
[data-testid="stButton"] > button:not([kind="primary"]) { background: #fff !important; color: #555 !important; border: 1px solid #ddd !important; border-radius: 8px !important; font-weight: 600 !important; }
[data-testid="stSelectbox"] > div > div { background-color: #fafafa !important; border: 1px solid #eee !important; border-radius: 8px !important; }
[data-testid="stChatInput"] textarea { background: #fafafa !important; border: 1px solid #eee !important; border-radius: 10px !important; }
[data-testid="stChatInput"] button { background: #bb38d0 !important; border-radius: 8px !important; }

/* ─── 결과 리포트 ─── */
.result-card { background: #fff; border-radius: 14px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); padding: 28px 24px; margin-bottom: 16px; }
.result-title { font-size: 22px; font-weight: 700; color: #bb38d0 !important; text-align: center; margin-bottom: 16px; }
.score-circle { width: 100px; height: 100px; border-radius: 50%; background: linear-gradient(135deg, #bb38d0, #7b2cb1); display: flex; flex-direction: column; align-items: center; justify-content: center; margin: 0 auto 20px auto; box-shadow: 0 4px 15px rgba(187,56,208,0.3); }
.score-number { font-size: 28px; font-weight: 800; color: #fff !important; }
.score-label  { font-size: 10px; color: rgba(255,255,255,0.85) !important; font-weight: 600; }
hr { border-color: #eee !important; }

/* 실시간 음성 UI */
.realtime-status { display: inline-flex; align-items: center; gap: 8px; padding: 8px 20px; border-radius: 24px; font-weight: 600; font-size: 14px; margin: 8px 0 16px 0; }
.status-idle { background: #f3f4f6; color: #6b7280; } .status-connected { background: #f0fdf4; color: #16a34a; } .status-recording { background: #fdf4ff; color: #bb38d0; } .status-speaking { background: #eff6ff; color: #2563eb; }
.pulse-dot { width: 8px; height: 8px; border-radius: 50%; background: currentColor; animation: pulse 1.2s infinite; display: inline-block; }
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
iframe[title="st_realtime_audio.realtime_audio_conversation"] { border: 2px solid #eee !important; border-radius: 14px !important; background: #fff !important; box-shadow: 0 2px 12px rgba(0,0,0,0.06) !important; min-height: 120px !important; max-height: 200px !important; }
.realtime-guide { background: #fff; border: 1px solid #eee; border-radius: 12px; padding: 16px 20px; margin-bottom: 12px; font-size: 14px; color: #555; line-height: 1.6; }
.realtime-guide strong { color: #bb38d0 !important; }
</style>
""", unsafe_allow_html=True)

# --- 인증 확인 ---
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("로그인이 필요합니다.")
    st.stop()

user_id = st.session_state.user.get("id", "demo_user")

# --- Session State 초기화 (DB 연동 변수 추가) ---
defaults = {
    "messages": [], "interview_ended": False, "interview_mode": None, "chatbot_started": False,
    "evaluation_result": None, "resume_text": None, "persona_style": "깐깐한 기술팀장",
    "db_session_id": None, "pending_question": None, "db_scores": []
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
# 헬퍼 함수
# ============================================================
def extract_resume_text(uploaded_file) -> str:
    try:
        import fitz
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        return "".join(page.get_text() for page in doc).strip()
    except ImportError:
        try:
            return uploaded_file.read().decode("utf-8", errors="ignore")
        except:
            return ""

def save_turn_to_db(question: str, answer: str):
    """GPT로 답변을 채점하고 interview_details에 저장합니다.
    
    테이블 콼럼: session_id, question_text, answer_text,
                    response_time, score, feedback, sentiment_score
    """
    if not st.session_state.db_session_id:
        return None, ""

    score, feedback = score_answer(question, answer, st.session_state.get("job_role", "개발자"))
    save_detail(
        session_id=st.session_state.db_session_id,
        question=question,
        answer=answer,
        score=score,
        feedback=feedback,
        response_time=0,         # 현재는 0으로 저장, STT 도입 시 실측값 대체
        sentiment_score=None,    # 음성 STT 도입 전까지 None
    )
    st.session_state.db_scores.append(score)
    return score, feedback

def render_message(role, content, is_followup=False, score=None):
    if role == "user":
        score_badge = f'<div class="score-mini">✦ {score:.1f}/10</div>' if score is not None else ""
        st.markdown(
            f'<div style="display:flex;justify-content:flex-end;flex-direction:column;align-items:flex-end;margin-bottom:4px;">'
            f'<div class="user-bubble">{content}</div>{score_badge}</div>',
            unsafe_allow_html=True,
        )
    elif role == "assistant":
        followup_badge = '<div class="followup-badge">💡 꼬리질문 포함</div>' if is_followup else ""
        st.markdown(
            f'<div style="display:flex;justify-content:flex-start;margin-bottom:4px;">'
            f'<div style="display:flex;flex-direction:column;">'
            f'<div class="sender-label">AI 면접관</div>{followup_badge}'
            f'<div class="ai-bubble">{content}</div></div></div>',
            unsafe_allow_html=True,
        )

# ============================================================
# 면접 시작 전: 설정 화면
# ============================================================
if not st.session_state.chatbot_started:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div class="setup-card">
        <div class="page-title">AI 모의면접</div>
        <div class="page-subtitle">실전과 동일한 환경에서 기술 면접을 연습하세요</div>
    </div>
    """, unsafe_allow_html=True)

    mode_options = ["💬 텍스트 면접"]
    mode_captions = ["타이핑으로 답변합니다. AI 면접관의 응답도 텍스트로 표시됩니다."]
    if _REALTIME_AVAILABLE:
        mode_options.append("🎙️ 실시간 음성 면접")
        mode_captions.append("실시간 음성 대화. AI가 즉시 음성으로 응답합니다.")
    else:
        mode_options.append("🎙️ 음성 면접 (설치 필요)")
        mode_captions.append("pip install streamlit-realtime-audio 필요")

    mode = st.radio("면접 방식을 선택하세요", mode_options, captions=mode_captions, index=0)
    st.markdown("---")

    persona_style = st.radio(
        "면접관 스타일", ["깐깐한 기술팀장", "부드러운 인사담당자", "스타트업 CTO"],
        captions=["기술적 모순을 파고드는 압박", "경험과 성장을 공감하는 인성", "결과물을 중시하는 실용주의"],
        horizontal=True
    )
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        job_role = st.selectbox("직무 선택", ["Python 백엔드 개발자", "Java 백엔드 개발자", "데이터 엔지니어", "프론트엔드 개발자"])
    with col2:
        difficulty = st.selectbox("난이도 선택", ["주니어", "미들", "시니어"], index=1)
    q_count = st.slider("질문 수", 3, 10, 5)

    st.markdown("---")
    st.markdown("**📄 이력서 업로드 (선택 사항)**")
    uploaded_resume = st.file_uploader("PDF/TXT 이력서 업로드", type=["pdf", "txt"], label_visibility="collapsed")

    is_realtime = "실시간" in mode
    if is_realtime and not _REALTIME_AVAILABLE:
        st.error("streamlit-realtime-audio가 설치되지 않았습니다.")
        st.stop()

    if st.button("면접 시작하기 🚀", type="primary", use_container_width=True):
        resume_text = None
        if uploaded_resume:
            with st.spinner("🔍 이력서를 Vector DB에 저장 중입니다..."):
                resume_text = extract_resume_text(uploaded_resume)
                if resume_text:
                    store_resume(resume_text, user_id=user_id)
        
        # 1. 일반 DB 세션 생성
        try:
            db_session_id = create_session(user_id=user_id, job_role=job_role)
        except Exception as e:
            st.warning("DB 세션 생성 실패 (결과가 저장되지 않습니다.)")
            db_session_id = None

        # 🔥 2. DB에서 직무/난이도에 맞는 메인 질문 리스트 뽑기
        # get_common_questions / get_questions_by_role 는 list[str] 반환 (딕셔너리 아님)
        _fallback_common = ["간단하게 자기소개를 부탁드립니다."]
        _fallback_tech   = [f"{job_role} 관련 핵심 기술과 경험을 설명해주세요." for _ in range(q_count - 1)]
        try:
            common_qs = get_common_questions(limit=1) or _fallback_common
            tech_qs   = get_questions_by_role(job_role, difficulty, limit=q_count - 1) or _fallback_tech
            db_questions = common_qs + tech_qs   # str 그대로 사용
        except Exception:
            db_questions = _fallback_common + _fallback_tech

        if not db_questions:   # 최후 안전망: 어떤 경우에도 빈 리스트 방지
            db_questions = _fallback_common + _fallback_tech

        # 3. 세션 주머니에 데이터 저장
        st.session_state.update({
            "interview_mode": "realtime" if is_realtime else "text",
            "chatbot_started": True, "job_role": job_role, "difficulty": difficulty,
            "q_count": q_count, "persona_style": persona_style,
            "resume_text": resume_text, "db_session_id": db_session_id,
            "db_questions": db_questions,
            "current_q_idx": 0
        })

        # 🔥 4. 텍스트 모드일 경우: 시작하자마자 냅다 첫 인사 + 첫 질문 띄우기!
        if not is_realtime:
            first_q = st.session_state.db_questions[0] # DB에서 뽑아온 첫 번째 질문
            
            # 지우님이 원하시는 찰떡같은 오프닝 멘트 적용
            greeting = (
                f"안녕하세요, 반갑습니다! "
                f"저는 오늘 {job_role} 포지션 면접을 진행하게 된 AI 면접관입니다. "
                f"총 {q_count}개의 질문으로 진행할 예정이니 편하게 답변해 주세요.\n\n"
                f"먼저, {first_q}"
            )
            
            # 메시지 창에 AI의 첫 대사로 꽂아넣기
            st.session_state.messages.append({"role": "assistant", "content": greeting})
            
            # 다음 턴 채점을 위해 "AI가 방금 한 질문"을 저장해두기
            st.session_state.pending_question = first_q

        # 화면 새로고침 -> 방금 추가한 greeting이 화면에 뿅! 나타남
        st.rerun()
    st.stop()

# ============================================================
# 면접 종료 — 리포트 및 DB 저장 (공통)
# ============================================================
if st.session_state.interview_ended:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="result-card"><div class="result-title">📋 면접 결과 리포트</div></div>', unsafe_allow_html=True)

    scores = st.session_state.db_scores
    total_score = round((sum(scores) / len(scores)) * 10, 1) if scores else 0.0

    st.markdown(f"""
    <div class="score-circle">
        <span class="score-number">{total_score}</span>
        <span class="score-label">/ 100점</span>
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.db_session_id:
        try:
            end_session(st.session_state.db_session_id, total_score)
        except:
            pass

    if st.session_state.evaluation_result is None:
        with st.spinner("결과를 분석 중입니다..."):
            st.session_state.evaluation_result = generate_evaluation(
                st.session_state.messages, st.session_state.get("job_role", "개발자"),
                st.session_state.get("difficulty", "미들"), st.session_state.get("resume_text")
            )

    st.markdown(st.session_state.evaluation_result)
    st.markdown("<br>", unsafe_allow_html=True)

    script_text = "\n".join([f"[{'면접관' if m['role'] == 'assistant' else '지원자'}] {m['content']}" for m in st.session_state.messages])

    col1, col2 = st.columns(2)
    with col1:
        st.download_button("📥 스크립트 다운로드", script_text.encode("utf-8"), file_name="interview_script.txt", mime="text/plain", use_container_width=True)
    with col2:
        if st.button("🔄 다시 시작하기", type="primary", use_container_width=True):
            for k in defaults:
                st.session_state[k] = defaults[k]
            st.rerun()
    st.stop()

# ============================================================
# 🎙️ 실시간 음성 면접 모드
# ============================================================
if st.session_state.interview_mode == "realtime":
    job_role = st.session_state.get("job_role", "Python 백엔드 개발자")
    difficulty = st.session_state.get("difficulty", "미들")
    q_count = st.session_state.get("q_count", 5)
    persona_style = st.session_state.get("persona_style", "깐깐한 기술팀장")

    st.markdown(f"""
    <div class="chat-header">
        <div class="chat-header-icon">🎙️</div>
        <div>
            <div class="chat-header-name">AI 면접관 · 실시간 음성 <span class="persona-badge">{persona_style}</span></div>
            <div class="chat-header-info">{job_role} · {difficulty} · {q_count}문항</div>
        </div>
    </div>
    <div class="realtime-guide">
        <strong>사용 방법</strong><br> 아래 <strong>Start</strong> 버튼을 누르면 연결됩니다.<br> 마이크가 활성화되면 자유롭게 말씀하세요. AI가 즉시 음성으로 응답합니다.
    </div>
    """, unsafe_allow_html=True)

    instructions = f"""당신은 {job_role} 전문 면접관입니다. 스타일: {persona_style}. 한국어로 기술 면접을 진행하세요. 난이도: {difficulty}. 총 {q_count}개 질문. "반갑습니다. 자기소개 부탁드립니다."로 시작하고 꼬리질문을 던지세요."""

    result = realtime_audio_conversation(api_key=os.getenv("OPENAI_API_KEY", ""), instructions=instructions, voice="echo", temperature=0.7, turn_detection_threshold=0.5, auto_start=False, key="interview_realtime")

    status = result.get("status", "idle") if result else "idle"
    status_map = {"idle": ("대기 중 — 아래 버튼을 눌러주세요", "status-idle"), "connecting": ("연결 중...", "status-idle"), "connected": ("연결 완료 — 마이크 활성화", "status-connected"), "recording": ("듣는 중...", "status-recording"), "speaking": ("면접관이 말하는 중...", "status-speaking")}
    label, css_class = status_map.get(status, ("알 수 없음", "status-idle"))
    st.markdown(f'<div class="realtime-status {css_class}"><span class="pulse-dot"></span> {label}</div>', unsafe_allow_html=True)

    transcript = result.get("transcript", []) if result else []
    if transcript:
        st.markdown("---")
        st.markdown("**대화 기록**")
        for msg in transcript:
            if msg.get("content"):
                render_message("assistant" if msg.get("type") == "assistant" else "user", msg.get("content", ""))

    st.markdown("---")
    if st.button("면접 종료하기", use_container_width=True):
        st.session_state.interview_ended = True
        st.session_state.messages = [{"role": "assistant" if m.get("type") == "assistant" else "user", "content": m.get("content", "")} for m in transcript if m.get("content")]
        st.rerun()
    st.stop()

# ============================================================
# 💬 텍스트 면접 모드
# ============================================================
job_role = st.session_state.get("job_role", "Python 백엔드 개발자")
difficulty = st.session_state.get("difficulty", "미들")
q_count = st.session_state.get("q_count", 5)
persona_style = st.session_state.get("persona_style", "깐깐한 기술팀장")
resume_text = st.session_state.get("resume_text", None)

st.markdown(f"""
<div class="chat-header">
    <div class="chat-header-icon">🎯</div>
    <div>
        <div class="chat-header-name">AI 면접관 <span class="persona-badge">{persona_style}</span></div>
        <div class="chat-header-info">{job_role} · {difficulty} · {q_count}문항 {'· 📄 RAG 활성' if resume_text else ''}</div>
    </div>
</div>
""", unsafe_allow_html=True)

# 메시지 렌더링
for message in st.session_state.messages:
    is_followup = "💡 추가 질문:" in message.get("content", "")
    render_message(message["role"], message["content"], is_followup=is_followup, score=message.get("score"))

# 채팅 입력
prompt = st.chat_input("답변을 입력하세요...")

if prompt:
    prev_question = st.session_state.pending_question or "면접 질문"
    st.session_state.messages.append({"role": "user", "content": prompt, "score": None})

    with st.spinner("면접관이 다음 질문을 준비하고 있습니다..."):
        ai_reply = get_ai_response(st.session_state.messages, job_role, difficulty, q_count, persona_style, resume_text, user_id)

        if "[INTERVIEW_END]" in ai_reply:
            st.session_state.interview_ended = True
            ai_reply = ai_reply.replace("[INTERVIEW_END]", "").strip()

        is_followup = "💡 추가 질문:" in ai_reply
        
        # 답변 채점 및 DB 저장
        score, feedback = save_turn_to_db(prev_question, prompt)
        st.session_state.messages[-1]["score"] = score # 방금 올린 답변 버블에 점수 추가

        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
        st.session_state.pending_question = ai_reply

    st.rerun()

if st.session_state.db_scores:
    avg = sum(st.session_state.db_scores) / len(st.session_state.db_scores)
    st.caption(f"현재 평균 점수: **{avg:.1f} / 10**")

st.markdown("<br>", unsafe_allow_html=True)
if st.button("면접 종료 및 리포트 받기 📊", use_container_width=True):
    st.session_state.interview_ended = True
    st.rerun()