"""
File: chatbot.py
Author: 김다빈
Created: 2026-02-21
Description: AI 면접관 채팅 페이지
             - 텍스트 면접 모드: OpenAI GPT (텍스트 입력 전용)
             - 실시간 음성 면접 모드: OpenAI Realtime API + WebRTC (streamlit-realtime-audio)
               → CSS로 영어 UI 숨김, TTS 음성 자동 출력

Modification History:
- 2026-02-21 (김다빈): 초기 생성
- 2026-02-22 (김다빈): STT/TTS 연동, 면접 종료 시 GPT-4o 피드백
- 2026-02-22 (김다빈): 실시간 음성 면접 모드 추가
- 2026-02-23 (김다빈): 실시간 음성 면접 컴포넌트(JS) 한국어 번역 및 UI 개선
- 2026-02-23 (김다빈): 면접 종료 후 분석 결과 증발 이슈 해결 (세션 상태 캐싱 적용)
"""

import streamlit as st
import os
import sys
import io
import hashlib
from pathlib import Path
import json
import streamlit.components.v1 as components
from utils.webcam_box import webcam_box
from utils.function import require_login

require_login()


# 외부 패키지 경로
_EXT_PKG_PATH = "/tmp/fw_pkg"
if os.path.isdir(_EXT_PKG_PATH) and _EXT_PKG_PATH not in sys.path:
    sys.path.insert(0, _EXT_PKG_PATH)

# 프로젝트 루트 경로 (backend.* 임포트용)
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import fitz
from openai import OpenAI

from db.database import (
    init_db,
    create_session,
    end_session,
    save_detail,
    get_questions_by_role,
    get_common_questions,
)
from services.rag_service import store_resume, clear_resume_for_session
from services.llm_service import (
    evaluate_and_respond,
    generate_evaluation,
    extract_keywords_from_resume,
)

try:
    init_db()
except Exception as e:
    pass


def extract_resume_text(uploaded_file):
    if uploaded_file is None:
        return ""
    try:
        if uploaded_file.name.endswith(".pdf"):
            doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
            text = ""
            for page in doc:
                text += page.get_text()
            return text.strip()
        elif uploaded_file.name.endswith(".txt"):
            return uploaded_file.read().decode("utf-8").strip()
    except Exception as e:
        st.error(f"이력서 텍스트 추출 중 오류 발생: {e}")
    return ""


# streamlit-realtime-audio 임포트
try:
    from st_realtime_audio import realtime_audio_conversation

    _REALTIME_AVAILABLE = True
except ImportError:
    _REALTIME_AVAILABLE = False

# --- 페이지 설정 ---
st.set_page_config(page_title="AI 면접관", page_icon="🎯", layout="centered")

# ============================================================
# CSS — 라이트 테마 + 실시간 음성 컴포넌트 영어 UI 숨기기
# ============================================================
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

* { font-family: 'Noto Sans KR', sans-serif !important; box-sizing: border-box; }

html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main {
    background-color: #f5f5f5 !important;
}
[data-testid="stHeader"] { background: transparent !important; }
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

.block-container {
    max-width: 680px !important;
    padding-top: 1.5rem !important;
    padding-bottom: 5rem !important;
}

h1, h2, h3, p, div, span, label { color: #333 !important; }

/* ─── 카드 ─── */
.setup-card {
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 2px 16px rgba(0,0,0,0.08);
    padding: 36px 32px;
    margin-bottom: 24px;
}
.page-title {
    font-size: 26px; font-weight: 700; color: #bb38d0 !important;
    text-align: center; margin-bottom: 6px;
}
.page-subtitle {
    font-size: 14px; color: #888 !important;
    text-align: center; margin-bottom: 0;
}

/* ─── 채팅 헤더 ─── */
.chat-header {
    display: flex; align-items: center; gap: 12px;
    background: #fff;
    border-radius: 14px;
    box-shadow: 0 1px 8px rgba(0,0,0,0.06);
    padding: 14px 20px;
    margin-bottom: 16px;
}
.chat-header-icon {
    width: 40px; height: 40px; border-radius: 10px;
    background: #bb38d0;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; color: #fff; flex-shrink: 0;
}
.chat-header-name { font-size: 16px; font-weight: 700; color: #333 !important; }
.chat-header-info { font-size: 12px; color: #999 !important; }

/* ─── 메시지 버블 ─── */
.ai-bubble {
    background: #fff;
    border: 1px solid #eee;
    border-radius: 16px; border-top-left-radius: 4px;
    padding: 14px 18px;
    max-width: 80%;
    color: #333 !important;
    font-size: 15px; line-height: 1.7;
    margin-bottom: 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.user-bubble {
    background: #bb38d0;
    border-radius: 16px; border-top-right-radius: 4px;
    padding: 14px 18px;
    max-width: 80%;
    color: #fff !important;
    font-size: 15px; line-height: 1.7;
    margin-bottom: 10px;
    box-shadow: 0 2px 8px rgba(187,56,208,0.2);
}
.sender-label {
    font-size: 11px; color: #bb38d0 !important;
    font-weight: 700; margin-bottom: 4px;
}

/* ─── 버튼 ─── */
[data-testid="stButton"] > button[kind="primary"] {
    background-color: #bb38d0 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    height: 50px !important;
    font-size: 16px !important;
    font-weight: 700 !important;
    transition: background 0.15s;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background-color: #a02db5 !important;
}
[data-testid="stButton"] > button[kind="secondary"],
[data-testid="stButton"] > button:not([kind="primary"]) {
    background: #fff !important;
    color: #555 !important;
    border: 1px solid #ddd !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}

/* ─── 입력 필드 ─── */
[data-testid="stSelectbox"] > div > div {
    background-color: #fafafa !important;
    border: 1px solid #eee !important;
    border-radius: 8px !important;
}
label[data-testid="stWidgetLabel"] > div > p {
    font-size: 13px !important; color: #555 !important;
    font-weight: 500 !important;
}

/* ─── chat_input ─── */
[data-testid="stChatInput"] textarea {
    background: #fafafa !important;
    border: 1px solid #eee !important;
    border-radius: 10px !important;
    color: #333 !important;
}
[data-testid="stChatInput"] button {
    background: #bb38d0 !important;
    border-radius: 8px !important;
}

/* ─── 라디오 ─── */
[data-testid="stRadio"] label span { color: #333 !important; }
[data-testid="stRadio"] label p { color: #888 !important; font-size: 13px !important; }

/* ─── 결과 카드 ─── */
.result-card {
    background: #fff;
    border-radius: 14px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    padding: 28px 24px;
    margin-bottom: 16px;
}
.result-title {
    font-size: 22px; font-weight: 700;
    color: #bb38d0 !important;
    text-align: center; margin-bottom: 16px;
}

hr { border-color: #eee !important; }

/* ─── 상태 인디케이터 ─── */
.realtime-status {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 8px 20px; border-radius: 24px;
    font-weight: 600; font-size: 14px;
    margin: 8px 0 16px 0;
}
.status-idle { background: #f3f4f6; color: #6b7280; }
.status-connected { background: #f0fdf4; color: #16a34a; }
.status-recording { background: #fdf4ff; color: #bb38d0; }
.status-speaking { background: #eff6ff; color: #2563eb; }

.pulse-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: currentColor; animation: pulse 1.2s infinite;
    display: inline-block;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

/* ─── TTS 오디오 플레이어 간소화 ─── */
audio {
    height: 36px !important;
    border-radius: 8px !important;
}

/* ============================================================
   실시간 음성 컴포넌트 영어 UI 숨기기 + 한국어 대체
   streamlit-realtime-audio의 내부 React 요소를 CSS로 덮어씌움
   ============================================================ */

/* iframe 내부 접근이 불가하므로, iframe 자체를 깔끔하게 스타일링 */
iframe[title="st_realtime_audio.realtime_audio_conversation"] {
    border: 2px solid #eee !important;
    border-radius: 14px !important;
    background: #fff !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06) !important;
    min-height: 120px !important;
    max-height: 200px !important;
}

/* 실시간 컴포넌트 안내 카드 */
.realtime-guide {
    background: #fff;
    border: 1px solid #eee;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
    font-size: 14px;
    color: #555;
    line-height: 1.6;
}
.realtime-guide strong {
    color: #bb38d0 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# --- 인증 확인 ---
# if "user" not in st.session_state or st.session_state.user is None:
#     st.warning("로그인이 필요합니다.")
#     st.stop()

# --- OpenAI 클라이언트 ---
from dotenv import load_dotenv

load_dotenv()
try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
except Exception:
    client = None
    st.error("OpenAI API 키가 설정되지 않았습니다.")

# --- Session State 초기화 ---
defaults = {
    "messages": [],
    "interview_ended": False,
    "last_processed_audio": None,
    "interview_mode": None,
    "chatbot_started": False,
    "evaluation_result": None,
    "voice_turn_active": False,
    "voice_turn_index": 0,
    "realtime_greeted": False,
    "persona_style": "깐깐한 기술팀장",
    "resume_text": "",
    "db_session_id": None,
    "turn_index": 0,
    "db_scores": [],
    "current_is_followup": False,
    "user_id": "",
    "pending_question": None,
    "db_questions": [],
    "current_q_idx": 0,
    "current_followup_count": 0,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

st.sidebar.markdown("### 👤 내 정보 설정")
input_id = st.sidebar.text_input("사용자 ID (이름)", value=st.session_state["user_id"])
if input_id:
    st.session_state["user_id"] = input_id
    st.sidebar.success(f"현재 접속자: {input_id}님 🟢")
else:
    st.sidebar.warning("ID를 입력해주세요!")


# build_system_prompt와 get_ai_response 함수는 evaluate_and_respond로 대체되므로 삭제합니다.


def transcribe_audio(audio_bytes: bytes) -> str:
    """음성 bytes를 텍스트로 변환. OpenAI Whisper 우선, 실패 시 로컬 STT 폴백."""
    openai_err = None
    if client:
        try:
            audio_file = io.BytesIO(audio_bytes)
            audio_file.name = "voice_turn.wav"
            result = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ko",
            )
            text = (result.text or "").strip()
            if text:
                return text
        except Exception as e:
            openai_err = str(e)

    try:
        from backend.services.local_inference import local_stt

        text = local_stt(audio_bytes, language="ko")
        if text and text.strip():
            return text.strip()
    except Exception as e:
        raise RuntimeError(f"STT 실패 (openai={openai_err or 'N/A'}, local={e})") from e

    raise RuntimeError(f"STT 실패 (openai={openai_err or 'N/A'}, local=empty)")


def generate_tts(text):
    if not client:
        return None
    try:
        tts_response = client.audio.speech.create(
            model="tts-1", voice="echo", input=text
        )
        return tts_response.content
    except Exception:
        return None


def render_message(
    role: str, content: str, is_followup: bool = False, score: float | None = None
):
    if role == "user":
        score_badge = (
            f'<div class="score-mini">✦ {score:.1f}/10</div>'
            if score is not None
            else ""
        )
        st.markdown(
            f'<div style="display:flex;justify-content:flex-end;flex-direction:column;align-items:flex-end;margin-bottom:4px;">'
            f'<div class="user-bubble">{content}</div>{score_badge}</div>',
            unsafe_allow_html=True,
        )
    elif role == "assistant":
        followup_badge = (
            '<div class="followup-badge">💡 꼬리질문 포함</div>' if is_followup else ""
        )
        st.markdown(
            f'<div style="display:flex;justify-content:flex-start;margin-bottom:4px;">'
            f'<div style="display:flex;flex-direction:column;">'
            f'<div class="sender-label">AI 면접관</div>{followup_badge}'
            f'<div class="ai-bubble">{content}</div>'
            f"</div></div>",
            unsafe_allow_html=True,
        )


# ============================================================
# 면접 시작 전: 설정 화면
# ============================================================
if not st.session_state.chatbot_started:
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        """
    <div class="setup-card">
        <div class="page-title">AI 모의면접</div>
        <div class="page-subtitle">실전과 동일한 환경에서 기술 면접을 연습하세요</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    mode_options = ["💬 텍스트 면접"]
    mode_captions = ["타이핑으로 답변합니다. AI 면접관의 응답도 텍스트로 표시됩니다."]

    if _REALTIME_AVAILABLE:
        mode_options.append("🎙️ 실시간 음성 면접")
        mode_captions.append(
            "실시간 음성 대화. AI가 즉시 음성으로 응답합니다. (OpenAI Realtime API)"
        )
    else:
        mode_options.append("🎙️ 음성 면접 (설치 필요)")
        mode_captions.append(
            "streamlit-realtime-audio 미설치. pip install streamlit-realtime-audio"
        )

    mode = st.radio(
        "면접 방식을 선택하세요",
        mode_options,
        captions=mode_captions,
        index=0,
    )

    st.markdown("---")

    persona_style = st.radio(
        "면접관 스타일",
        ["깐깐한 기술팀장", "부드러운 인사담당자", "스타트업 CTO"],
        horizontal=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        job_role = st.selectbox(
            "직무 선택",
            [
                "Python 백엔드 개발자",
                "Java 백엔드 개발자",
                "데이터 엔지니어",
                "프론트엔드 개발자",
            ],
        )
    with col2:
        difficulty = st.selectbox(
            "난이도 선택",
            ["주니어", "미들", "시니어"],
            index=1,
        )

    q_count = st.slider("질문 수", 3, 10, 5)

    st.markdown(
        "**📄 이력서 업로드 <span style='color:#e53e3e;font-size:13px;'>(필수)</span>**",
        unsafe_allow_html=True,
    )
    uploaded_resume = st.file_uploader(
        "PDF/TXT 이력서", type=["pdf", "txt"], label_visibility="collapsed"
    )
    if uploaded_resume:
        st.success(f"'{uploaded_resume.name}' 업로드 완료 ✅")
    else:
        st.warning("⚠️ 이력서를 업로드해야 면접을 시작할 수 있습니다.")

    st.markdown("<br>", unsafe_allow_html=True)

    is_realtime = "실시간" in mode
    if is_realtime and not _REALTIME_AVAILABLE:
        st.error("streamlit-realtime-audio가 설치되지 않았습니다.")
        st.stop()

    if st.button(
        "면접 시작하기",
        type="primary",
        use_container_width=True,
        disabled=not bool(uploaded_resume),
    ):
        st.session_state.interview_mode = "realtime" if is_realtime else "text"
        st.session_state.chatbot_started = True
        st.session_state.job_role = job_role
        st.session_state.difficulty = difficulty
        st.session_state.q_count = q_count
        st.session_state.persona_style = persona_style
        st.session_state.resume_text = extract_resume_text(uploaded_resume)

        try:
            db_session_id = create_session(
                user_id=st.session_state["user_id"],
                job_role=job_role,
                difficulty=difficulty,
                persona=persona_style,
                resume_used=bool(st.session_state.resume_text),
            )
        except Exception as e:
            st.warning(f"DB 연결 실패: {e}")
            db_session_id = None
        st.session_state.db_session_id = db_session_id

        # 2. 이력서 RAG 저장
        if st.session_state.resume_text and db_session_id:
            with st.spinner("이력서 저장 중..."):
                store_resume(st.session_state.resume_text, user_id=str(db_session_id))

        # 3. 질문 풀(DB)에서 질문 로드
        try:
            from db.database import get_questions_by_resume_keywords

            common_qs = get_common_questions(limit=1)
            if st.session_state.resume_text:
                resume_keywords = extract_keywords_from_resume(
                    st.session_state.resume_text
                )
                tech_qs = get_questions_by_resume_keywords(
                    job_role, difficulty, resume_keywords, limit=q_count - 1
                )
            else:
                tech_qs = get_questions_by_role(job_role, difficulty, limit=q_count - 1)

            db_questions = [q["question"] for q in common_qs] + [
                q["question"] for q in tech_qs
            ]
            if not db_questions:
                raise ValueError("DB에 해당 직무/난이도의 질문 데이터가 없습니다.")
        except Exception as e:
            print(f"⚠️ 임시 질문 대체: {e}")
            db_questions = ["간단하게 자기소개를 부탁드립니다."] + [
                f"{job_role} 관련 핵심 기술을 설명해주세요." for _ in range(q_count - 1)
            ]

        st.session_state.db_questions = db_questions
        st.session_state.current_q_idx = 0

        first_q = db_questions[0]
        greeting = f"안녕하세요! 오늘 {job_role} ({difficulty}) 면접을 진행할 면접관입니다. 총 {q_count}개의 큰 질문과 그에 대한 꼬리질문이 이어집니다.\n\n첫 번째 질문입니다.\n**{first_q}**"

        if not is_realtime:
            st.session_state.messages.append({"role": "assistant", "content": greeting})
            st.session_state.pending_question = first_q

        st.rerun()

    st.stop()


# ============================================================
# 면접 종료 — 결과 분석 (공통)
# ============================================================
if st.session_state.interview_ended:
    st.session_state.last_processed_audio = None

    scores = st.session_state.db_scores
    total_score = round((sum(scores) / len(scores)) * 10, 1) if scores else 0.0

    if st.session_state.db_session_id:
        try:
            end_session(st.session_state.db_session_id, total_score)
        except:
            pass

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
    <div class="result-card">
        <div class="result-title">면접 결과 분석</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    if st.session_state.evaluation_result is None:
        with st.spinner("결과를 분석 중입니다..."):
            st.session_state.evaluation_result = generate_evaluation(
                st.session_state.messages,
                st.session_state.get("job_role", "개발자"),
                st.session_state.get("difficulty", "미들"),
                st.session_state.get("resume_text", ""),
            )

    st.markdown(st.session_state.evaluation_result)

    st.markdown("<br>", unsafe_allow_html=True)

    script_text = "\n".join(
        [
            f"[{'면접관' if m['role'] == 'assistant' else '지원자'}] {m['content']}"
            for m in st.session_state.messages
        ]
    )

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "대화 스크립트 다운로드",
            script_text.encode("utf-8"),
            file_name="interview_script.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with col2:
        if st.button("다시 시작하기", type="primary", use_container_width=True):
            for k in defaults:
                st.session_state[k] = defaults[k]
            st.rerun()
    st.stop()

# ============================================================
# 🎙️ 음성 턴제 면접 모드 (Realtime API 직접 제어)
# ============================================================
if st.session_state.interview_mode == "realtime":
    job_role = st.session_state.get("job_role", "Python 백엔드 개발자")
    difficulty = st.session_state.get("difficulty", "미들")
    q_count = st.session_state.get("q_count", 5)
    persona_style = st.session_state.get("persona_style", "깐깐한 기술팀장")
    resume_text = st.session_state.get("resume_text", "")
    has_resume = "📄 이력서 포함" if resume_text else "이력서 없음"

    st.markdown(
        f"""
    <div class="chat-header">
        <div class="chat-header-icon">🎙️</div>
        <div>
            <div class="chat-header-name">AI 면접관 · 음성 턴제</div>
            <div class="chat-header-info">{job_role} · {difficulty} · {q_count}문항 · [{persona_style}] · {has_resume}</div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
    <div class="realtime-guide">
        <strong>사용 방법</strong><br>
        <strong>시작</strong>을 누르고 답변한 뒤 <strong>중지</strong>를 누르세요.<br>
        중지 순간 STT로 변환 후, 그 텍스트를 기반으로 면접관이 답변합니다.
    </div>
    """,
        unsafe_allow_html=True,
    )

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        st.error("OPENAI_API_KEY 환경변수가 필요합니다.")
        st.stop()

    resume_context = ""
    if resume_text:
        resume_context = f"\n\n지원자 이력서 내용 일부:\n{resume_text[:800]}\n이력서를 바탕으로 관련성 있는 꼬리질문을 구성하세요."

    instructions = f"""당신은 {job_role} 전문 면접관입니다. 한국어로 기술 면접을 진행하세요.
난이도: {difficulty}. 총 {q_count}개 질문. 면접관 스타일: {persona_style}.

규칙:
1. 면접관이 먼저 짧게 인사하고 자기소개를 요청
2. 답변을 들은 뒤 기술적 꼬리질문 1~2개
3. 각 답변에 간단한 피드백 후 다음 질문
4. {q_count}개 질문 완료 후 종합 평가
5. '{persona_style}' 스타일의 전문적인 톤 유지
6. 반드시 한국어로만 대화{resume_context}"""
    realtime_model = os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview")

    html = """
<div style="background:#fff;border:1px solid #eee;border-radius:12px;padding:14px;">
  <div style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px;">
    <button id="btnConnect" style="padding:10px 14px;border-radius:8px;border:1px solid #ddd;background:#fff;cursor:pointer;">연결</button>
    <button id="btnStart" style="padding:10px 14px;border-radius:8px;border:none;background:#bb38d0;color:#fff;cursor:pointer;" disabled>시작</button>
    <button id="btnStop" style="padding:10px 14px;border-radius:8px;border:none;background:#333;color:#fff;cursor:pointer;" disabled>중지</button>
    <button id="btnEnd" style="padding:10px 14px;border-radius:8px;border:1px solid #ddd;background:#fff;cursor:pointer;" disabled>종료</button>
    <button id="btnDownload" style="padding:10px 14px;border-radius:8px;border:1px solid #ddd;background:#fff;cursor:pointer;" disabled>스크립트 다운로드</button>
  </div>
  <div id="status" style="font-size:13px;color:#666;margin-bottom:8px;">대기 중</div>
  <div style="font-size:13px;font-weight:700;color:#444;margin:6px 0;">대화창</div>
  <div id="chat" style="height:340px;overflow:auto;background:#fafafa;border:1px solid #ddd;border-radius:10px;padding:10px;"></div>
  <audio id="remoteAudio" autoplay></audio>
</div>
<script>
(function() {
  const API_KEY = __API_KEY__;
  const MODEL = __MODEL__;
  const INSTRUCTIONS = __INSTRUCTIONS__;

  const btnConnect = document.getElementById("btnConnect");
  const btnStart = document.getElementById("btnStart");
  const btnStop = document.getElementById("btnStop");
  const btnEnd = document.getElementById("btnEnd");
  const btnDownload = document.getElementById("btnDownload");
  const statusEl = document.getElementById("status");
  const chatEl = document.getElementById("chat");
  const remoteAudio = document.getElementById("remoteAudio");

  let pc = null;
  let dc = null;
  let stream = null;
  let remoteStream = null;
  let micTrack = null;
  let connected = false;
  let recording = false;
  let committing = false;
  let awaitingResponse = false;
  let currentAssistantDiv = null;
  let pendingUserBubble = null;
  let pendingAssistantAudioTarget = null;
  const lines = [];
  const seenUserItems = new Set();
  const userAudioClips = [];
  const assistantAudioClips = [];
  let mediaRecorder = null;
  let assistantRecorder = null;
  let currentChunks = [];
  let assistantChunks = [];
  let recorderMime = "";
  let pendingUserAudioTarget = null;
  let assistantStopTimer = null;
  let assistantWaitingAudioDone = false;
  let assistantSpeaking = false;
  let audioCtx = null;
  let remoteAnalyser = null;
  let remoteData = null;
  let silenceCheckTimer = null;
  let lastNonSilentAt = 0;

  function setStatus(text) {
    statusEl.textContent = text;
  }

  function setButtons() {
    btnConnect.disabled = connected;
    btnStart.disabled = !connected || recording || committing || assistantSpeaking;
    btnStop.disabled = !connected || !recording;
    btnEnd.disabled = !connected;
    btnDownload.disabled = lines.length === 0;
  }

  function appendBubble(role, text) {
    const row = document.createElement("div");
    row.style.margin = "8px 0";
    row.style.display = "flex";
    row.style.justifyContent = role === "user" ? "flex-end" : "flex-start";

    const bubble = document.createElement("div");
    bubble.style.maxWidth = "80%";
    bubble.style.padding = "10px 12px";
    bubble.style.borderRadius = "12px";
    bubble.style.whiteSpace = "pre-wrap";
    bubble.style.fontSize = "14px";
    bubble.style.lineHeight = "1.5";
    if (role === "user") {
      bubble.style.background = "#bb38d0";
      bubble.style.color = "#fff";
    } else {
      bubble.style.background = "#fff";
      bubble.style.border = "1px solid #eee";
      bubble.style.color = "#333";
    }
    const textEl = document.createElement("span");
    textEl.textContent = text;
    bubble.appendChild(textEl);
    bubble._textEl = textEl;
    row.appendChild(bubble);
    chatEl.appendChild(row);
    chatEl.scrollTop = chatEl.scrollHeight;
    lines.push(`[${role === "user" ? "지원자" : "AI 면접관"}] ${text}`);
    setButtons();
    return bubble;
  }

  function attachAudioControls(targetBubble, clip) {
    if (!targetBubble) return;
    const wrap = document.createElement("div");
    wrap.style.marginTop = "6px";
    wrap.style.display = "flex";
    wrap.style.gap = "8px";
    wrap.style.alignItems = "center";
    wrap.style.flexWrap = "wrap";

    const audio = document.createElement("audio");
    audio.controls = true;
    audio.src = clip.url;
    audio.style.height = "28px";

    const btn = document.createElement("button");
    btn.textContent = "다운로드";
    btn.style.padding = "4px 8px";
    btn.style.border = "1px solid #ddd";
    btn.style.borderRadius = "6px";
    btn.style.background = "#fff";
    btn.style.cursor = "pointer";
    btn.addEventListener("click", () => {
      const a = document.createElement("a");
      a.href = clip.url;
      a.download = clip.filename;
      a.click();
    });

    wrap.appendChild(audio);
    wrap.appendChild(btn);
    targetBubble.appendChild(wrap);
  }

  async function ensureAssistantClipFromText(targetBubble) {
    if (!targetBubble) return null;
    if (targetBubble._assistantClip) return targetBubble._assistantClip;
    const text = (targetBubble._textEl ? targetBubble._textEl.textContent : targetBubble.textContent || "").trim();
    if (!text) return null;
    const res = await fetch("https://api.openai.com/v1/audio/speech", {
      method: "POST",
      headers: {
        "Authorization": `Bearer ${API_KEY}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        model: "tts-1",
        voice: "alloy",
        input: text
      }),
    });
    if (!res.ok) {
      const t = await res.text();
      throw new Error(`TTS 생성 실패: ${res.status} ${t}`);
    }
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const ts = new Date();
    const filename = `assistant_tts_${ts.toISOString().replace(/[:.]/g, "-")}.mp3`;
    targetBubble._assistantClip = { url, filename };
    return targetBubble._assistantClip;
  }

  function attachAssistantTextControls(targetBubble) {
    if (!targetBubble || targetBubble._assistantControlsAttached) return;
    targetBubble._assistantControlsAttached = true;

    const wrap = document.createElement("div");
    wrap.style.marginTop = "6px";
    wrap.style.display = "flex";
    wrap.style.gap = "8px";
    wrap.style.alignItems = "center";
    wrap.style.flexWrap = "wrap";

    const listenBtn = document.createElement("button");
    listenBtn.textContent = "다시듣기";
    listenBtn.style.padding = "4px 8px";
    listenBtn.style.border = "1px solid #ddd";
    listenBtn.style.borderRadius = "6px";
    listenBtn.style.background = "#fff";
    listenBtn.style.cursor = "pointer";

    const downloadBtn = document.createElement("button");
    downloadBtn.textContent = "저장";
    downloadBtn.style.padding = "4px 8px";
    downloadBtn.style.border = "1px solid #ddd";
    downloadBtn.style.borderRadius = "6px";
    downloadBtn.style.background = "#fff";
    downloadBtn.style.cursor = "pointer";

    const setBusy = (busy) => {
      listenBtn.disabled = busy;
      downloadBtn.disabled = busy;
      if (busy) {
        listenBtn.textContent = "생성 중...";
      } else {
        listenBtn.textContent = "다시듣기";
      }
    };

    listenBtn.addEventListener("click", async () => {
      try {
        setBusy(true);
        const clip = await ensureAssistantClipFromText(targetBubble);
        const a = new Audio(clip.url);
        await a.play();
      } catch (e) {
        setStatus(`면접관 TTS 오류: ${e.message || e}`);
      } finally {
        setBusy(false);
      }
    });

    downloadBtn.addEventListener("click", async () => {
      try {
        setBusy(true);
        const clip = await ensureAssistantClipFromText(targetBubble);
        const a = document.createElement("a");
        a.href = clip.url;
        a.download = clip.filename;
        a.click();
      } catch (e) {
        setStatus(`면접관 저장 오류: ${e.message || e}`);
      } finally {
        setBusy(false);
      }
    });

    wrap.appendChild(listenBtn);
    wrap.appendChild(downloadBtn);
    targetBubble.appendChild(wrap);
  }

  function updateAssistantDelta(delta) {
    if (!currentAssistantDiv) {
      currentAssistantDiv = appendBubble("assistant", "");
      lines.pop();
    }
    if (currentAssistantDiv._textEl) {
      currentAssistantDiv._textEl.textContent += delta;
    } else {
      currentAssistantDiv.textContent += delta;
    }
    chatEl.scrollTop = chatEl.scrollHeight;
  }

  function finalizeAssistant() {
    if (!currentAssistantDiv) return;
    const txt = currentAssistantDiv._textEl
      ? currentAssistantDiv._textEl.textContent
      : currentAssistantDiv.textContent;
    lines.push(`[AI 면접관] ${txt}`);
    attachAssistantTextControls(currentAssistantDiv);
    currentAssistantDiv = null;
    setButtons();
  }

  function startAssistantRecording() {
    if (assistantStopTimer) {
      clearTimeout(assistantStopTimer);
      assistantStopTimer = null;
    }
    assistantWaitingAudioDone = false;
    assistantSpeaking = true;
    setButtons();
    if (!assistantRecorder || assistantRecorder.state !== "inactive") return;
    assistantChunks = [];
    assistantRecorder.start(1000);
    lastNonSilentAt = Date.now();
  }

  function stopAssistantRecording() {
    if (!assistantRecorder || assistantRecorder.state !== "recording") return;
    if (assistantStopTimer) clearTimeout(assistantStopTimer);
    if (silenceCheckTimer) clearInterval(silenceCheckTimer);
    // audio.done 이벤트가 누락되면 무음 감지 기반으로 정지
    silenceCheckTimer = setInterval(() => {
      if (!assistantRecorder || assistantRecorder.state !== "recording") {
        clearInterval(silenceCheckTimer);
        silenceCheckTimer = null;
        return;
      }
      if (remoteAnalyser && remoteData) {
        remoteAnalyser.getByteTimeDomainData(remoteData);
        let sum = 0;
        for (let i = 0; i < remoteData.length; i++) {
          const v = (remoteData[i] - 128) / 128;
          sum += v * v;
        }
        const rms = Math.sqrt(sum / remoteData.length);
        if (rms > 0.006) lastNonSilentAt = Date.now();
      }
      if (Date.now() - lastNonSilentAt > 2200) {
        stopAssistantRecordingNow();
      }
    }, 120);
    // 최종 안전장치
    assistantStopTimer = setTimeout(() => {
      stopAssistantRecordingNow();
    }, 5000);
  }

  function stopAssistantRecordingNow() {
    if (silenceCheckTimer) {
      clearInterval(silenceCheckTimer);
      silenceCheckTimer = null;
    }
    if (assistantStopTimer) {
      clearTimeout(assistantStopTimer);
      assistantStopTimer = null;
    }
    if (assistantRecorder && assistantRecorder.state === "recording") {
      assistantRecorder.stop();
    }
    assistantWaitingAudioDone = false;
    assistantSpeaking = false;
    setStatus("응답 완료. 다음 발화를 시작하세요.");
    setButtons();
  }

  function sendEvent(evt) {
    if (!(dc && dc.readyState === "open")) return false;
    dc.send(JSON.stringify(evt));
    return true;
  }

  async function connect() {
    try {
      setStatus("마이크 권한 요청 중...");
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      micTrack = stream.getAudioTracks()[0];
      micTrack.enabled = false;
      if (MediaRecorder.isTypeSupported("audio/webm;codecs=opus")) {
        recorderMime = "audio/webm;codecs=opus";
      } else if (MediaRecorder.isTypeSupported("audio/webm")) {
        recorderMime = "audio/webm";
      } else {
        recorderMime = "";
      }
      mediaRecorder = new MediaRecorder(stream, recorderMime ? { mimeType: recorderMime } : undefined);
      mediaRecorder.ondataavailable = (e) => {
        if (e.data && e.data.size > 0) currentChunks.push(e.data);
      };
      mediaRecorder.onstop = () => {
        const blob = new Blob(currentChunks, { type: mediaRecorder.mimeType || "audio/webm" });
        currentChunks = [];
        if (blob.size > 0) {
          const url = URL.createObjectURL(blob);
          const ts = new Date();
          const name = `user_turn_${ts.toISOString().replace(/[:.]/g, "-")}.webm`;
          const clip = { url, filename: name };
          userAudioClips.push(clip);
          if (pendingUserAudioTarget) {
            attachAudioControls(pendingUserAudioTarget, clip);
            pendingUserAudioTarget = null;
          }
          setStatus("발언 음성 저장됨");
        } else {
          setStatus("발언 음성 저장 실패 (녹음 데이터 없음)");
        }
      };

      pc = new RTCPeerConnection();
      pc.addTrack(micTrack, stream);
      pc.ontrack = (e) => {
        remoteStream = e.streams[0];
        remoteAudio.srcObject = remoteStream;
        try {
          if (!audioCtx) audioCtx = new (window.AudioContext || window.webkitAudioContext)();
          const src = audioCtx.createMediaStreamSource(remoteStream);
          remoteAnalyser = audioCtx.createAnalyser();
          remoteAnalyser.fftSize = 1024;
          remoteData = new Uint8Array(remoteAnalyser.fftSize);
          src.connect(remoteAnalyser);
        } catch (_) {}
        if (!assistantRecorder && remoteStream) {
          assistantRecorder = new MediaRecorder(
            remoteStream,
            recorderMime ? { mimeType: recorderMime } : undefined
          );
          assistantRecorder.ondataavailable = (ev) => {
            if (ev.data && ev.data.size > 0) assistantChunks.push(ev.data);
          };
          assistantRecorder.onstop = () => {
            const blob = new Blob(assistantChunks, {
              type: assistantRecorder.mimeType || "audio/webm",
            });
            assistantChunks = [];
            if (blob.size > 0) {
              const url = URL.createObjectURL(blob);
              const ts = new Date();
              const name = `assistant_turn_${ts
                .toISOString()
                .replace(/[:.]/g, "-")}.webm`;
              const clip = { url, filename: name };
              assistantAudioClips.push(clip);
            }
          };
        }
      };

      dc = pc.createDataChannel("oai-events");
      dc.onclose = () => {
        connected = false;
        recording = false;
        committing = false;
        setStatus("데이터 채널이 종료되었습니다.");
        setButtons();
      };
      dc.onerror = () => {
        setStatus("데이터 채널 오류");
      };
      dc.onopen = () => {
        connected = true;
        setStatus("연결 완료. 시작을 누르면 발화가 전송됩니다.");
        setButtons();
        sendEvent({
          type: "session.update",
          session: {
            instructions: INSTRUCTIONS,
            modalities: ["audio", "text"],
            turn_detection: null,
            input_audio_transcription: { model: "whisper-1" }
          }
        });
        awaitingResponse = true;
        startAssistantRecording();
        sendEvent({
          type: "response.create",
          response: {
            modalities: ["audio", "text"],
            instructions: "면접관으로서 한 문장 인사 후 자기소개를 요청하세요."
          }
        });
        appendBubble("assistant", "안녕하세요. AI 면접관입니다. 시작을 누르고 답변 후 중지를 눌러 제출해주세요.");
      };

      dc.onmessage = (event) => {
        let data = null;
        try { data = JSON.parse(event.data); } catch (_) { return; }
        if (!data || !data.type) return;

        // 중지 전에는 어떤 자동 응답도 강제로 취소한다.
        if (recording && !awaitingResponse && data.type.startsWith("response.")) {
          sendEvent({ type: "response.cancel" });
          setStatus("녹음 유지 중... 중지를 눌러 제출하세요.");
          return;
        }

        if (data.type === "input_audio_buffer.committed") {
          setStatus("제출 완료. 면접관 응답 생성 중...");
          return;
        }

        if (data.type === "conversation.item.input_audio_transcription.failed") {
          committing = false;
          setStatus("음성 인식 실패. 다시 시작해서 말씀해 주세요.");
          setButtons();
          return;
        }

        if (data.type === "conversation.item.input_audio_transcription.completed") {
          if (recording && !awaitingResponse) {
            // 중지 전 자동 STT 이벤트는 무시 (턴 분할 방지)
            return;
          }
          if (data.transcript && data.transcript.trim()) {
            if (pendingUserBubble) {
              if (pendingUserBubble._textEl) {
                pendingUserBubble._textEl.textContent = data.transcript.trim();
              } else {
                pendingUserBubble.textContent = data.transcript.trim();
              }
              lines.pop();
              lines.push(`[지원자] ${data.transcript.trim()}`);
              pendingUserBubble = null;
              setButtons();
            } else {
              appendBubble("user", data.transcript.trim());
            }
          }
          return;
        }

        if (data.type === "conversation.item.created") {
          const item = data.item || {};
          if (item.id && seenUserItems.has(item.id)) return;
          if (item.role === "user") {
            let userText = "";
            const parts = Array.isArray(item.content) ? item.content : [];
            for (const p of parts) {
              if (p?.transcript) userText += p.transcript;
              else if (p?.text) userText += p.text;
            }
            userText = (userText || "").trim();
            if (userText) {
              if (item.id) seenUserItems.add(item.id);
              if (pendingUserBubble) {
                if (pendingUserBubble._textEl) {
                  pendingUserBubble._textEl.textContent = userText;
                } else {
                  pendingUserBubble.textContent = userText;
                }
                lines.pop();
                lines.push(`[지원자] ${userText}`);
                pendingUserBubble = null;
                setButtons();
              } else {
                appendBubble("user", userText);
              }
            }
          }
          return;
        }

        if (
          data.type === "response.output_audio_transcript.delta" ||
          data.type === "response.audio_transcript.delta" ||
          data.type === "response.text.delta" ||
          data.type === "response.output_text.delta"
        ) {
          if (!awaitingResponse) return;
          const d = data.delta || "";
          if (d) updateAssistantDelta(d);
          return;
        }

        if (
          data.type === "response.output_audio_transcript.done" ||
          data.type === "response.output_text.done"
        ) {
          if (!awaitingResponse) return;
          finalizeAssistant();
          return;
        }

        if (data.type === "response.done") {
          if (!awaitingResponse) return;
          committing = false;
          awaitingResponse = false;
          // 텍스트 done은 오디오 재생 종료보다 빠를 수 있어 대기 상태로 전환
          assistantWaitingAudioDone = true;
          stopAssistantRecording();
          if (!currentAssistantDiv) {
            const out = data.response?.output || [];
            let fullText = "";
            for (const item of out) {
              const parts = Array.isArray(item?.content) ? item.content : [];
              for (const p of parts) {
                if (p?.transcript) fullText += p.transcript;
                else if (p?.text) fullText += p.text;
              }
            }
            fullText = (fullText || "").trim();
            if (fullText) {
              const b = appendBubble("assistant", fullText);
              attachAssistantTextControls(b);
            }
          }
          finalizeAssistant();
          setStatus("면접관 음성 재생 중...");
          setButtons();
          return;
        }
        // response.audio.done은 내부 청크 완료 단위로 여러 번 올 수 있어
        // 중간 끊김을 유발한다. 실제 종료는 무음 감지(stopAssistantRecording)로 처리.
        if (data.type === "error") {
          stopAssistantRecordingNow();
          setStatus("오류: " + (data.error?.message || "unknown"));
        }
      };

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);

      const sdpResponse = await fetch(`https://api.openai.com/v1/realtime?model=${encodeURIComponent(MODEL)}`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${API_KEY}`,
          "Content-Type": "application/sdp"
        },
        body: offer.sdp
      });

      if (!sdpResponse.ok) {
        const errText = await sdpResponse.text();
        throw new Error(`Realtime 연결 실패: ${sdpResponse.status} ${errText}`);
      }

      const answerSdp = await sdpResponse.text();
      await pc.setRemoteDescription({ type: "answer", sdp: answerSdp });
      setStatus("데이터 채널 연결 중...");
    } catch (err) {
      setStatus("연결 오류: " + (err?.message || err));
      console.error(err);
    }
  }

  function startTurn() {
    if (!connected || !micTrack || committing) return;
    awaitingResponse = false;
    sendEvent({
      type: "session.update",
      session: {
        turn_detection: null,
        input_audio_transcription: { model: "whisper-1" }
      }
    });
    micTrack.enabled = true;
    recording = true;
    if (mediaRecorder && mediaRecorder.state === "inactive") {
      currentChunks = [];
      mediaRecorder.start(1000);
    }
    sendEvent({ type: "input_audio_buffer.clear" });
    setStatus("녹음 중... 중지를 누르면 제출됩니다.");
    setButtons();
  }

  function stopTurn() {
    if (!connected || !micTrack || !recording || committing) return;
    micTrack.enabled = false;
    recording = false;
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
    }
    committing = true;
    setButtons();
    setStatus("제출 중...");
    pendingUserBubble = appendBubble("user", "(음성 제출 중...)");
    pendingUserAudioTarget = pendingUserBubble;
    // 마지막 오디오 프레임이 전송 버퍼에 반영되도록 짧게 대기 후 commit
    setTimeout(() => {
      if (!connected) {
        committing = false;
        return;
      }
      const ok = sendEvent({ type: "input_audio_buffer.commit" });
      if (!ok) {
        committing = false;
        if (pendingUserBubble) {
          if (pendingUserBubble._textEl) {
            pendingUserBubble._textEl.textContent = "(제출 실패)";
          } else {
            pendingUserBubble.textContent = "(제출 실패)";
          }
          lines.pop();
          lines.push("[지원자] (제출 실패)");
          pendingUserBubble = null;
        }
        setStatus("제출 실패: 채널이 닫혀 있습니다.");
        setButtons();
        return;
      }
      sendEvent({
        type: "response.create",
        response: { modalities: ["audio", "text"] }
      });
      awaitingResponse = true;
      startAssistantRecording();
    }, 250);
  }

  function endSession() {
    try {
      recording = false;
      committing = false;
      connected = false;
      if (micTrack) micTrack.enabled = false;
      if (dc) dc.close();
      if (pc) pc.close();
      if (stream) stream.getTracks().forEach(t => t.stop());
      stopAssistantRecordingNow();
      if (remoteStream) remoteStream.getTracks().forEach(t => t.stop());
    } catch (_) {}
    dc = null;
    pc = null;
    stream = null;
    micTrack = null;
    setStatus("세션 종료됨");
    setButtons();
  }

  function downloadScript() {
    const blob = new Blob([lines.join("\\n")], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "interview_realtime.txt";
    a.click();
    URL.revokeObjectURL(url);
  }

  btnConnect.addEventListener("click", connect);
  btnStart.addEventListener("click", startTurn);
  btnStop.addEventListener("click", stopTurn);
  btnEnd.addEventListener("click", endSession);
  btnDownload.addEventListener("click", downloadScript);
  setButtons();
})();
</script>
"""
    html = (
        html.replace("__API_KEY__", json.dumps(api_key))
        .replace("__MODEL__", json.dumps(realtime_model))
        .replace("__INSTRUCTIONS__", json.dumps(instructions))
    )
    components.html(html, height=520, scrolling=False)
    webcam_box(height=520)

    st.stop()


# ============================================================
# 💬 텍스트 면접 모드
# ============================================================
job_role = st.session_state.get("job_role", "Python 백엔드 개발자")
difficulty = st.session_state.get("difficulty", "미들")
q_count = st.session_state.get("q_count", 5)
persona_style = st.session_state.get("persona_style", "깐깐한 기술팀장")
resume_text = st.session_state.get("resume_text", "")
has_resume = "📄 이력서 포함" if resume_text else "이력서 없음"

# 채팅 헤더
st.markdown(
    f"""
<div class="chat-header">
    <div class="chat-header-icon">🎯</div>
    <div>
        <div class="chat-header-name">AI 면접관</div>
        <div class="chat-header-info">{job_role} · {difficulty} · {q_count}문항 · [{persona_style}] · {has_resume}</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# 메시지 렌더링
for message in st.session_state.messages:
    render_message(
        message["role"],
        message["content"],
        is_followup="💡" in message.get("content", ""),
        score=message.get("score"),
    )

# TTS 자동 재생
if "latest_audio_content" in st.session_state:
    st.audio(st.session_state.latest_audio_content, format="audio/mp3", autoplay=True)
    del st.session_state.latest_audio_content

# 텍스트 입력
prompt = st.chat_input("답변을 입력하세요...")

if prompt:
    prev_question = st.session_state.pending_question or "면접 질문"
    st.session_state.messages.append({"role": "user", "content": prompt, "score": None})

    with st.spinner("답변을 분석하고 꼬리질문을 준비 중입니다..."):
        db_qs = st.session_state.get("db_questions", [])
        idx = st.session_state.get("current_q_idx", 0)
        next_q = db_qs[idx + 1] if idx + 1 < len(db_qs) else None

        eval_res = evaluate_and_respond(
            question=prev_question,
            answer=prompt,
            job_role=job_role,
            difficulty=difficulty,
            persona_style=persona_style,
            user_id=st.session_state.user_id,
            resume_text=resume_text,
            next_main_question=next_q,
            followup_count=st.session_state.current_followup_count,
        )

        score = eval_res["score"]
        feedback = eval_res["feedback"]
        ai_reply = eval_res["reply_text"]
        is_followup = eval_res["is_followup"]

        st.session_state.db_scores.append(score)
        st.session_state.messages[-1]["score"] = score

        if st.session_state.db_session_id:
            try:
                save_detail(
                    st.session_state.db_session_id,
                    st.session_state.turn_index,
                    prev_question,
                    prompt,
                    st.session_state.current_is_followup,
                    score,
                    feedback,
                )
                st.session_state.turn_index += 1
            except Exception as e:
                print(f"DB save error: {e}")

        if is_followup:
            st.session_state.current_followup_count += 1
        else:
            st.session_state.current_followup_count = 0

        if "[INTERVIEW_END]" in ai_reply:
            st.session_state.interview_ended = True
            ai_reply = ai_reply.replace("[INTERVIEW_END]", "").strip()
        if "[NEXT_MAIN]" in ai_reply:
            st.session_state.current_q_idx += 1
            ai_reply = ai_reply.replace("[NEXT_MAIN]", "").strip()

        st.session_state.current_is_followup = is_followup
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
        st.session_state.pending_question = ai_reply

    st.rerun()

if st.session_state.db_scores:
    avg = sum(st.session_state.db_scores) / len(st.session_state.db_scores)
    st.caption(f"현재 평균: **{avg:.1f} / 10** ({len(st.session_state.db_scores)}문항)")

# 종료 버튼
st.markdown("<br>", unsafe_allow_html=True)
if st.button("면접 종료하기", use_container_width=True):
    st.session_state.interview_ended = True
    st.rerun()
