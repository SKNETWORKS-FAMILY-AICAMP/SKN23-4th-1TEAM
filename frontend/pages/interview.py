"""
File: pages/interview.py
Description: AI 면접 페이지
"""

import base64
import io
import json
import os
import time
import requests

import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI

# 백엔드 모듈 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
backend_dir = os.path.join(root_dir, "backend")
import sys

if root_dir not in sys.path:
    sys.path.append(root_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from utils.api_utils import (
    api_end_interview,
    api_get_question_pool,
    api_start_interview,
    api_stt_bytes,
)
from utils.webcam_box import webcam_box
from utils.config import API_BASE_URL
from utils.function import require_login, inject_custom_header

from services.llm_service import generate_evaluation, analyze_resume_comprehensive
from services.rag_service import store_resume

# 페이지 기본 설정
st.set_page_config(page_title="AIWORK", page_icon="👾", layout="wide")

# 문지기 출동
user_id = require_login()
inject_custom_header()


# CSS 스타일
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap');
    :root { color-scheme: light !important; }
    * { font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important; box-sizing: border-box; color-scheme: light !important; color: #111 !important; }
    html, body, .stApp { background-color: #f8f9fa !important; color: #111 !important; color-scheme: light !important; }
    [data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main { background-color: #f8f9fa !important; color-scheme: light !important; }
    [data-testid="stHeader"], [data-testid="stToolbar"], footer { visibility: hidden; color-scheme: light !important; }
    p, span, div, label, h1, h2, h3, h4, h5, h6, li, a, td, th, small, strong, b, i, em { color: #111 !important; }

    /* === Streamlit 내부 컴포넌트 다크모드 완전 차단 === */
    [data-testid="stVerticalBlock"],
    [data-testid="stHorizontalBlock"],
    [data-testid="stColumn"],
    [data-testid="stForm"],
    [data-testid="stMarkdownContainer"],
    [data-testid="stRadio"],
    [data-testid="stRadio"] > div,
    [data-testid="stSelectbox"],
    [data-testid="stSelectbox"] > div,
    [data-testid="stChatMessage"],
    [data-testid="stChatMessage"] > div { color: #111 !important; }

    /* Dialog / Modal - 면접 설정 모달 */
    [data-testid="stDialog"] > div > div,
    [data-testid="stDialog"] [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stDialog"] [data-testid="stVerticalBlock"],
    [data-testid="stDialog"] [data-testid="stHorizontalBlock"],
    [data-testid="stDialog"] [data-testid="stColumn"],
    section[data-testid="stDialog"] { background-color: #ffffff !important; color: #111 !important; }

    /* Baseweb 입력/선택 컴포넌트 */
    [data-baseweb="input"], [data-baseweb="input"] > div,
    [data-baseweb="select"], [data-baseweb="select"] > div,
    [data-baseweb="textarea"],
    [data-baseweb="popover"] > div,
    [data-baseweb="menu"], [data-baseweb="menu"] li { background-color: #ffffff !important; color: #111 !important; }
    [data-baseweb="radio"] > div > div > div { color: #111 !important; }

    /* 채팅 메시지 버블 */
    [data-testid="stChatMessage"] { background-color: #ffffff !important; }
    .stChatMessage { background-color: #ffffff !important; }

    /* === 모든 Streamlit 버튼 배경 강제 === */
    [data-testid="stButton"] > button,
    [data-testid="stLinkButton"] > a,
    [data-testid="stFormSubmitButton"] > button {
        background-color: #ffffff !important; color: #111 !important; border: 1px solid #ddd !important;
    }
    [data-testid="stButton"] > button p, [data-testid="stLinkButton"] > a p { color: #111 !important; }
    button[kind="primary"], [data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(135deg, #bb38d0 0%, #872a96 100%) !important;
        border: none !important; color: white !important;
    }
    button[kind="primary"] p, button[kind="primary"] span,
    [data-testid="stButton"] > button[kind="primary"] p { color: #fff !important; }

    /* === 테이블/데이터프레임 === */
    [data-testid="stDataFrame"], [data-testid="stDataFrame"] > div, [data-testid="stDataFrame"] iframe,
    [data-testid="stTable"], [data-testid="stTable"] table,
    [data-testid="stTable"] th, [data-testid="stTable"] td { background-color: #ffffff !important; color: #111 !important; }

    /* === 컨테이너 내부 === */
    [data-testid="stVerticalBlockBorderWrapper"] > div { background-color: transparent !important; }
    
    /* 결과 모달 관련 스타일 */
    .result-card { background: #ffffff; border-radius: 16px; padding: 32px 24px; text-align: center; border: none; box-shadow: 0 4px 24px rgba(0,0,0,0.07); margin-bottom: 24px; }
    .result-title { font-size: 22px; font-weight: 800; color: #000; margin-bottom: 16px; }
    .score-circle { width: 140px; height: 140px; border-radius: 50%; background: #ffffff; display: flex; flex-direction: column; align-items: center; justify-content: center; margin: 0 auto; box-shadow: 0 4px 24px rgba(0,0,0,0.07); border: 4px solid #bb38d0; }
    .score-number { font-size: 40px; font-weight: 900; color: #bb38d0; line-height: 1; }
    .score-label { font-size: 14px; color: #666; font-weight: 600; margin-top: 4px; }

    /* 채팅 입력창 */
    div[data-testid="stChatInput"] { 
        border-radius: 24px !important; 
        border: 2px solid #fae8ff !important; 
        background: #ffffff !important; 
        padding: 4px 10px !important; 
        margin-bottom: 20px !important; 
        transition: all 0.3s ease !important; 
        box-shadow: 0 4px 20px rgba(187, 56, 208, 0.05) !important;
    }
    div[data-testid="stChatInput"]:focus-within { 
        border-color: #bb38d0 !important; 
        box-shadow: 0 8px 30px rgba(187, 56, 208, 0.15) !important; 
    }
    div[data-testid="stChatInput"] > div, 
    div[data-testid="stChatInput"] div[data-baseweb="textarea"], 
    div[data-testid="stChatInput"] div[data-baseweb="base-input"] { 
        background-color: transparent !important; 
        border: none !important; 
    }
    div[data-testid="stChatInput"] textarea { 
        background-color: transparent !important; 
        color: #111111 !important; 
        font-size: 15px !important; 
        font-weight: 500 !important; 
        caret-color: #bb38d0 !important; 
    }
    div[data-testid="stChatInput"] textarea::placeholder { 
        color: #adb5bd !important; 
    }
    
    /* 전송 버튼 */
    button[data-testid="stChatInputSubmitButton"], 
    div[data-testid="stChatInputSubmitButton"] { 
        background: linear-gradient(135deg, #bb38d0 0%, #872a96 100%) !important; 
        color: white !important; 
        border-radius: 50% !important; 
        width: 36px !important; 
        height: 36px !important; 
        min-width: 36px !important; 
        display: flex !important; 
        align-items: center !important; 
        justify-content: center !important; 
        transition: all 0.2s ease !important; 
        margin-top: 2px !important; 
        margin-bottom: 2px !important; 
        box-shadow: 0 4px 10px rgba(187, 56, 208, 0.3) !important;
    }
    button[data-testid="stChatInputSubmitButton"]:hover, 
    div[data-testid="stChatInputSubmitButton"]:hover { 
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 15px rgba(187, 56, 208, 0.4) !important;
        filter: brightness(1.1);
    }
    button[data-testid="stChatInputSubmitButton"]:active, 
    div[data-testid="stChatInputSubmitButton"]:active { 
        transform: scale(0.9) translateY(0) !important; 
    }
    button[data-testid="stChatInputSubmitButton"] svg, 
    div[data-testid="stChatInputSubmitButton"] svg { 
        fill: #ffffff !important; 
        color: #ffffff !important; 
        width: 18px !important; 
        height: 18px !important; 
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# 헬퍼 함수 모음
def extract_resume_text(uploaded_file) -> str:
    file_bytes = uploaded_file.getvalue()
    try:
        import fitz

        return "".join(
            page.get_text() for page in fitz.open(stream=file_bytes, filetype="pdf")
        ).strip()
    except Exception:
        try:
            return file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return ""


def generate_tts(text: str) -> bytes | None:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        client = OpenAI(api_key=api_key)
        tts_response = client.audio.speech.create(
            model="tts-1", voice="echo", input=text
        )
        return tts_response.content
    except Exception:
        return None


def create_session(
    user_id,
    job_role,
    difficulty,
    persona,
    resume_used,
    resume_id=None,
    manual_tech_stack=None,
):
    success, result = api_start_interview(
        job_role=job_role,
        difficulty=difficulty,
        persona=persona,
        resume_used=resume_used,
        resume_id=resume_id,
        manual_tech_stack=manual_tech_stack,
    )
    if not success:
        raise RuntimeError(result)
    return result.get("session_id")


def get_questions_by_role(job_role, difficulty, limit=3):
    success, result = api_get_question_pool(job_role, difficulty, limit)
    if not success:
        return []
    return result.get("items", [])


def process_answer(answer_text: str) -> bool:
    print(f"[DEBUG] process_answer triggered with: {answer_text}")
    prev_question = st.session_state.pending_question or "면접 질문"
    st.session_state.messages.append(
        {"role": "user", "content": answer_text, "score": None}
    )

    q_idx = st.session_state.get("current_q_idx", 0)
    db_qs = st.session_state.get("db_questions", [])
    next_q = db_qs[q_idx + 1] if q_idx + 1 < len(db_qs) else None

    target_user_id = str(st.session_state.get("db_session_id", "guest"))

    payload = {
        "question": prev_question,
        "answer": answer_text,
        "job_role": st.session_state.job_role,
        "difficulty": st.session_state.difficulty,
        "persona_style": st.session_state.get("persona_style", "깐깐한 기술팀장"),
        "user_id": target_user_id,
        "resume_text": st.session_state.get("resume_text", ""),
        "next_main_question": next_q,
        "followup_count": st.session_state.get("current_followup_count", 0),
        "attitude": None,
    }

    try:
        res = requests.post(
            f"{API_BASE_URL.rstrip('/')}/infer/evaluate-turn", json=payload, timeout=30
        )

        if res.status_code == 200:
            result = res.json()
            success = True
        else:
            success = False
            result = f"서버 에러 ({res.status_code}): {res.text}"

    except Exception as e:
        success = False
        result = str(e)

    if not success:
        st.session_state.messages.pop()
        st.error(f"답변 처리 실패 (서버 로그를 확인하세요): {result}")
        return False

    score = float(result.get("score", 5.0))
    ai_reply = result.get("reply_text") or result.get("answer", "")
    is_followup = result.get("is_followup", False)
    feedback_text = result.get("feedback", "")

    st.session_state.db_scores.append(score)
    st.session_state.messages[-1]["score"] = score
    st.session_state.turn_index += 1

    try:
        access_token = st.session_state.get("token")
        detail_payload = {
            "session_id": st.session_state.db_session_id,
            "turn_index": st.session_state.turn_index,
            "question": prev_question,
            "answer": answer_text,
            "is_followup": is_followup,
            "score": score,
            "feedback": feedback_text,
        }
        requests.post(
            f"{API_BASE_URL.rstrip('/')}/interview/details",
            json=detail_payload,
            headers={"Authorization": f"Bearer {access_token}"} if access_token else {},
            timeout=10,
        )
    except Exception as e:
        print(f"상세 기록 DB 저장 실패: {e}")

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

    tts = generate_tts(ai_reply)
    if tts:
        st.session_state.latest_audio_content = tts

    return True  


# 상태 초기화
defaults = {
    "messages": [],
    "interview_ended": False,
    "interview_mode": None,
    "chatbot_started": False,
    "evaluation_result": None,
    "resume_text": None,
    "persona_style": None,
    "db_session_id": None,
    "turn_index": 0,
    "pending_question": None,
    "db_scores": [],
    "current_followup_count": 0,
    "current_is_followup": False,
    "db_questions": [],
    "current_q_idx": 0,
    "user_id": user_id,
    "latest_audio_content": None,
    "last_voice_hash": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


# 팝업(모달) 선언
@st.dialog("면접 결과 리포트", width="large")
def evaluation_modal():
    scores = st.session_state.db_scores
    total_score = round((sum(scores) / len(scores)) * 10, 1) if scores else 0.0

    if not st.session_state.get("is_db_ended") and st.session_state.db_session_id:
        try:
            access_token = st.session_state.get("token")
            requests.put(
                f"{API_BASE_URL.rstrip('/')}/interview/sessions/{st.session_state.db_session_id}",
                json={"total_score": total_score, "status": "COMPLETED"},
                headers=(
                    {"Authorization": f"Bearer {access_token}"} if access_token else {}
                ),
                timeout=10,
            )
        except Exception as e:
            print(f"세션 종료 DB 업데이트 실패: {e}")
        st.session_state.is_db_ended = True

    st.markdown(
        f'<div class="score-circle"><span class="score-number">{total_score}</span><span class="score-label">/ 100</span></div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.get("resume_used", False):
        st.warning(
            "이력서를 연동하지 않은 자율 면접이므로, 직무/이력서 매칭률 점수 및 이력서 기반 포트폴리오 평가는 제공되지 않습니다."
        )
        eval_resume_text = None
    else:
        eval_resume_text = st.session_state.get("resume_text")

    if st.session_state.evaluation_result is None:
        with st.spinner("AI가 분석 중입니다..."):
            raw_eval = generate_evaluation(
                st.session_state.messages,
                st.session_state.get("job_role"),
                st.session_state.get("difficulty"),
                eval_resume_text,
            )
            import re
            st.session_state.evaluation_result = re.sub(
                r"\*\*[\d\.]+\s*/\s*100점\*\*", f"**{total_score} / 100점**", raw_eval
            )

    st.markdown(st.session_state.evaluation_result)

    st.markdown("<br>", unsafe_allow_html=True)
    st.download_button(
        label="📄 결과 리포트 저장 (TXT)",
        data=st.session_state.evaluation_result,
        file_name=f"interview_report.txt",
        mime="text/plain",
        use_container_width=True
    )

    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("다시 시작", type="primary", use_container_width=True):
            for k, v in defaults.items():
                st.session_state[k] = v
            st.rerun()
    with col2:
        if st.button("내 기록 보러가기", use_container_width=True):
            st.switch_page("pages/mypage.py")


@st.dialog("AI 모의면접 환경 설정", width="large")
def interview_setup_modal():
    st.markdown(
        """
    <style>
    div[data-testid="stDialog"] > div[role="dialog"] {
        background: linear-gradient(160deg, #f4e8f9 0%, #ffffff 40%, #fdf4ff 100%) !important;
        border-radius: 24px !important; border: 1px solid #e8cceb !important; box-shadow: 0 24px 80px rgba(187, 56, 208, 0.2) !important;
        padding: 30px !important; min-height: 760px !important; display: flex; flex-direction: column;
    }
    div[data-testid="stDialog"] h2 {
        background: linear-gradient(135deg, #a62eb8 0%, #872a96 100%);
        -webkit-background-clip: text; -webkit-text-fill-color: transparent;
        font-weight: 900 !important; font-size: 28px !important; text-align: center;
        padding-bottom: 5px !important; margin-bottom: 5px !important; border-bottom: none !important;
    }
    .modal-subtitle-custom { text-align: center; color: #713f7a; font-size: 14px; font-weight: 600; margin-top: -30px; margin-bottom: 35px; letter-spacing: -0.3px; }
    .premium-label {
        font-size: 15px; font-weight: 800; color: #111111; background: transparent; 
        padding: 2px 0 2px 10px; border-left: 4px solid #bb38d0; border-radius: 0; 
        display: block; margin-bottom: 16px; margin-top: 24px; box-shadow: none; letter-spacing: -0.3px;
    }
    div[role="radiogroup"] { gap: 12px !important; }
    div[role="radiogroup"] label {
        background-color: #ffffff !important; border: 2px solid #e8cceb !important; border-radius: 12px !important; padding: 12px 18px !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.02) !important; transition: all 0.2s cubic-bezier(0.2, 0.8, 0.2, 1) !important; cursor: pointer !important;
    }
    div[role="radiogroup"] label:hover { border-color: #bb38d0 !important; background-color: #fcf0fc !important; transform: translateY(-2px); box-shadow: 0 8px 20px rgba(187, 56, 208, 0.15) !important; }
    div[role="radiogroup"] label p { font-weight: 700 !important; color: #4a0e4e !important; font-size: 14px !important; }
    div[data-baseweb="select"] > div, textarea, [data-testid="stFileUploaderDropzone"] {
        border: 2px solid #e8cceb !important; border-radius: 14px !important; background-color: #fdf7fe !important; color: #333333 !important; transition: all 0.2s ease !important;
    }
    div[data-baseweb="select"] > div:focus-within, textarea:focus { border-color: #bb38d0 !important; background-color: #ffffff !important; box-shadow: 0 0 0 4px rgba(187, 56, 208, 0.2) !important; }
    [data-testid="stFileUploaderDropzone"] { background: linear-gradient(135deg, #fdf7fe 0%, #ffffff 100%) !important; border: 2px dashed #bb38d0 !important; }
    [data-testid="stFileUploaderDropzone"]:hover { background: #f8e5fa !important; }
    button[kind="primary"] {
        background: linear-gradient(135deg, #bb38d0 0%, #872a96 100%) !important; color: white !important; font-size: 18px !important; font-weight: 800 !important;
        border-radius: 16px !important; height: 60px !important; letter-spacing: 1px !important; border: none !important; box-shadow: 0 10px 25px rgba(187, 56, 208, 0.4) !important;
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important; margin-top: auto !important; 
    }
    button[kind="primary"]:hover { transform: translateY(-3px) !important; box-shadow: 0 15px 35px rgba(187, 56, 208, 0.5) !important; filter: brightness(1.1); }
    button[kind="primary"]:active { transform: translateY(0px) !important; box-shadow: 0 6px 15px rgba(187, 56, 208, 0.4) !important; }
    button[kind="primary"]:disabled { background: #e5e7eb !important; color: #9ca3af !important; box-shadow: none !important; transform: none !important; }
    .stTextArea textarea { min-height: 120px !important; }
    </style>
    """,
        unsafe_allow_html=True,
    )

    st.markdown(
        '<div class="modal-subtitle-custom">지원자님의 역량을 최대한 발휘할 수 있도록 면접 환경을 설정해주세요.</div>',
        unsafe_allow_html=True,
    )

    col_mode, col_persona = st.columns([1, 1.5])
    with col_mode:
        st.markdown(
            '<div class="premium-label">진행 방식</div>', unsafe_allow_html=True
        )
        mode = st.radio(
            "면접 방식",
            ["텍스트 면접", "음성 면접"],
            horizontal=True,
            label_visibility="collapsed",
        )
    with col_persona:
        st.markdown(
            '<div class="premium-label">면접관 스타일</div>', unsafe_allow_html=True
        )
        persona_style = st.radio(
            "면접관 스타일",
            ["깐깐한 기술팀장", "부드러운 인사담당자", "스타트업 CTO"],
            horizontal=True,
            label_visibility="collapsed",
        )

    st.markdown(
        '<div class="premium-label">세부 면접 설정</div>', unsafe_allow_html=True
    )
    col_role, col_diff, col_count = st.columns([2, 1, 1.5])
    with col_role:
        job_role = st.selectbox(
            "지원 직무",
            [
                "Python 백엔드 개발자",
                "Java 백엔드 개발자",
                "AI/ML 엔지니어",
                "데이터 엔지니어",
                "프론트엔드 개발자",
                "풀스택 개발자",
            ],
        )
    with col_diff:
        difficulty = st.selectbox("난이도", ["상", "중", "하"], index=1)
    with col_count:
        q_count = st.slider("질문 수 설정 (개)", 3, 10, 5)

    has_saved_resume = bool(st.session_state.get("resume_id"))
    saved_resume_title = st.session_state.get("resume_title", "등록된 이력서")

    manual_tech_stack = None
    uploaded_resume = None
    disable_start = False

    st.markdown(
        '<div class="premium-label">이력서 및 경험 연동</div>', unsafe_allow_html=True
    )

    if has_saved_resume:
        st.success(
            f"저장된 '{saved_resume_title}' 문서를 기반으로 맞춤형 질문이 생성됩니다."
        )
        if st.button("기존 이력서 선택 해제하기", use_container_width=True):
            st.session_state.resume_id = None
            st.session_state.resume_text = None
            st.session_state.resume_title = None
            st.rerun()
    else:
        input_method = st.radio(
            "데이터 입력 방식",
            ["이력서 파일 첨부", "직접 입력"],
            horizontal=True,
            label_visibility="collapsed",
        )

        if input_method == "이력서 파일 첨부":
            st.markdown(
                "<span style='font-size:13px; color:#713f7a; font-weight:700;'>이력서 업로드 (PDF/TXT 포맷 권장)</span>",
                unsafe_allow_html=True,
            )
            uploaded_resume = st.file_uploader(
                "파일을 이곳으로 드래그하거나 클릭하여 업로드하세요.",
                type=["pdf", "txt"],
                label_visibility="collapsed",
            )
            disable_start = not bool(uploaded_resume)
        else:
            manual_tech_stack = st.text_area(
                "보유 기술 스택 및 핵심 프로젝트 경험",
                placeholder="어필하고 싶은 기술 스택이나 프로젝트 경험을 간략히 적어주세요. (예: Spring Boot와 JPA를 활용한 트래픽 최적화 경험)",
                height=120,
            )
            disable_start = not bool(manual_tech_stack and manual_tech_stack.strip())

    if st.button(
        "설정완료", type="primary", use_container_width=True, disabled=disable_start
    ):
        final_resume_text = None
        is_resume_used = False

        if has_saved_resume:
            final_resume_text = st.session_state.get("resume_text")
            is_resume_used = True
        elif uploaded_resume:
            final_resume_text = extract_resume_text(uploaded_resume)
            is_resume_used = True
        elif manual_tech_stack:
            final_resume_text = manual_tech_stack
            is_resume_used = False

        try:
            db_session_id = create_session(
                user_id=user_id,
                job_role=job_role,
                difficulty=difficulty,
                persona=persona_style,
                resume_used=is_resume_used,
                resume_id=(
                    st.session_state.get("resume_id") if has_saved_resume else None
                ),
                manual_tech_stack=(
                    manual_tech_stack
                    if not has_saved_resume and not uploaded_resume
                    else None
                ),
            )
        except Exception as e:
            st.error(f"세션 생성 오류: {e}")
            db_session_id = None

        if final_resume_text and db_session_id and is_resume_used:
            with st.spinner("이력서를 벡터 DB에 안전하게 저장 중입니다..."):
                chunk_count = store_resume(
                    final_resume_text, user_id=str(db_session_id)
                )
                time.sleep(0.5)

            if chunk_count > 0:
                st.toast(
                    f"이력서가 {chunk_count}개의 청크로 분할되어 벡터 DB에 저장되었습니다!",
                    icon="📄",
                )
                time.sleep(0.5)

        try:
            fixed_first_q = "<b>간단하게 자기소개를 부탁드립니다.</b>"

            if final_resume_text:
                with st.spinner(
                    "지원자님의 경험을 바탕으로 날카로운 실무 질문을 생성 중입니다..."
                ):
                    analysis_result = analyze_resume_comprehensive(
                        final_resume_text, job_role
                    )
                    expected_qs = analysis_result.get("expected_questions", [])

                    if expected_qs and len(expected_qs) > 0:
                        remain_count = q_count - 1

                        tech_count = remain_count // 2
                        resume_count = remain_count - tech_count

                        resume_qs_subset = expected_qs[:resume_count]

                        tech_qs_data = get_questions_by_role(
                            job_role, difficulty, limit=tech_count
                        )
                        tech_qs = [
                            q["question"] for q in tech_qs_data if "question" in q
                        ]

                        if len(tech_qs) < tech_count:
                            shortfall = tech_count - len(tech_qs)
                            resume_qs_subset = expected_qs[: resume_count + shortfall]

                        db_questions = [fixed_first_q] + resume_qs_subset + tech_qs
                    else:
                        tech_qs = get_questions_by_role(
                            job_role, difficulty, limit=q_count - 1
                        )
                        db_questions = [fixed_first_q] + [
                            q["question"] for q in tech_qs if "question" in q
                        ]
            else:
                tech_qs = get_questions_by_role(job_role, difficulty, limit=q_count - 1)
                db_questions = [fixed_first_q] + [q["question"] for q in tech_qs]

            if len(db_questions) == 1:
                raise ValueError("질문이 생성되지 않았습니다.")

        except Exception:
            db_questions = ["간단하게 자기소개를 부탁드립니다."] + [
                f"{job_role} 관련 핵심 기술을 설명해주세요." for _ in range(q_count - 1)
            ]

        first_q = db_questions[0]
        greeting = f"안녕하세요. 오늘 {job_role} 직무 면접을 진행할 면접관입니다. 총 {q_count}개의 질문을 드릴 예정입니다.\n\n첫 번째 질문입니다.\n**{first_q}**"

        st.session_state.update(
            {
                "interview_mode": "voice" if "음성" in mode else "text",
                "chatbot_started": True,
                "job_role": job_role,
                "difficulty": difficulty,
                "q_count": q_count,
                "persona_style": persona_style,
                "resume_text": final_resume_text,
                "db_session_id": db_session_id,
                "db_questions": db_questions,
                "current_q_idx": 0,
                "messages": [{"role": "assistant", "content": greeting}],
                "pending_question": first_q,
                "resume_used": is_resume_used,
            }
        )
        st.rerun()


# 메인 로직 시작

if not st.session_state.chatbot_started:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown(
        "<h3 style='text-align:center; color:#888;'>면접 환경을 설정 중입니다.<br>팝업창에서 옵션을 선택해 주세요.</h3>",
        unsafe_allow_html=True,
    )
    interview_setup_modal()
    st.stop()

# 모달 호출은 여기서 대기 (이후 로직이 멈춤)
if st.session_state.interview_ended:
    evaluation_modal()
    st.stop()


# 🎯 100% 무조건 작동하는 Native Streamlit 헤더 레이아웃
col_h1, col_h2 = st.columns([5, 1], vertical_alignment="center")

with col_h1:
    st.markdown(
        f"""
        <div style="background: linear-gradient(135deg, #ffffff 0%, #fdf4ff 100%); border: 1px solid #fae8ff; border-radius: 20px; padding: 16px 24px; box-shadow: 0 10px 30px rgba(187, 56, 208, 0.08); display: flex; align-items: center; gap: 16px; margin-top: 10px; margin-bottom: 10px;">
            <div style="font-size: 28px; background: #ffffff; width: 52px; height: 52px; border-radius: 16px; display: flex; align-items: center; justify-content: center; box-shadow: 0 4px 15px rgba(187, 56, 208, 0.15);">👾</div>
            <div style="display: flex; flex-direction: column;">
                <div style="font-size: 18px; font-weight: 800; color: #111; display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">AI 면접관 <span style="font-size: 12px; background: #bb38d0; color: #fff; padding: 3px 10px; border-radius: 12px; font-weight: 700;">{st.session_state.persona_style}</span></div>
                <div style="font-size: 13px; color: #666; font-weight: 600;">{st.session_state.job_role} · 난이도 {st.session_state.difficulty} · {st.session_state.q_count}문항</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with col_h2:
    st.markdown(
        """
        <style>
        /* 🎯 네이티브 버튼을 헤더 높이에 맞게 크고 예쁘게 튜닝 */
        div[data-testid="stColumn"]:nth-child(2) button {
            height: 64px !important;
            font-size: 15px !important;
            margin-top: 10px !important;
        }
        </style>
        """, 
        unsafe_allow_html=True
    )
    if st.button("면접 종료", type="primary", use_container_width=True):
        st.session_state.interview_ended = True
        st.rerun()


# 텍스트 모드
if st.session_state.interview_mode == "text":
    st.markdown(
        """
        <div style="background:#ffffff; border-radius:16px; border:1px solid #fae8ff; padding:16px 20px; margin-bottom:16px; box-shadow:0 4px 15px rgba(187,56,208,0.05); font-size:14px; color:#444; line-height:1.6;">
            <strong style="color:#bb38d0;">텍스트 면접 모드 가이드</strong><br>
            하단의 입력창에 답변을 타이핑하여 제출해 주세요. 카메라는 사용되지 않으며, 채팅창을 넓게 사용합니다.
        </div>
        """,
        unsafe_allow_html=True,
    )

    chat_html = """
    <style>
    * { font-family: 'Pretendard', -apple-system, sans-serif; box-sizing: border-box; margin: 0; padding: 0; }
    @keyframes msg-pop { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    .ai-bubble { 
        background: #ffffff; border-radius: 6px 20px 20px 20px; border: 1px solid #fae8ff;
        padding: 12px 22px; color: #111; font-size: 15px; line-height: 1.6; white-space: pre-wrap;
        animation: msg-pop 0.3s ease-out both; display: inline-block; max-width: 700px;
        box-shadow: 0 4px 20px rgba(187, 56, 208, 0.05);
    }
    .user-bubble { 
        background: linear-gradient(135deg, #bb38d0 0%, #872a96 100%); border-radius: 20px 6px 20px 20px;
        padding: 12px 20px; color: #ffffff; font-size: 15px; line-height: 1.6; white-space: pre-wrap;
        animation: msg-pop 0.3s ease-out both; display: inline-block; max-width: 82%;
        box-shadow: 0 8px 25px rgba(187, 56, 208, 0.3); 
    }
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #e8cceb; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #d09cd6; }
    </style>
    <div style="background:linear-gradient(135deg, #ffffff 0%, #fdf4ff 100%);border:2px solid #fae8ff;border-radius:24px;padding:24px;box-shadow:0 10px 40px rgba(187,56,208,0.05); margin-bottom: 4px; display: flex; flex-direction: column;">
        <div style="font-size:14px;font-weight:800;color:#333;margin:0 0 12px 0;">텍스트 대화창</div>
        <div id="chat-container" style="height: 600px; overflow-y:auto; overflow-x:hidden; background:#ffffff;border:1px solid #fae8ff;border-radius:16px;padding:20px;box-shadow:inset 0 2px 10px rgba(0,0,0,0.02); display: flex; flex-direction: column;">
    """

    for message in st.session_state.messages:
        role = message.get("role")
        content = message.get("content", "")
        score = message.get("score")

        content_str = (
            content.get("content", "") if isinstance(content, dict) else str(content)
        )
        is_followup = "꼬리질문" in content_str

        if role == "user":
            score_badge = (
                f'<div style="font-size: 11px; font-weight: 600; color: #888; margin-top: 6px; margin-right: 4px;">AI 평가 점수: {score:.1f} / 10</div>'
                if score is not None
                else ""
            )
            chat_html += f"""
            <div style="display:flex; justify-content:flex-end; margin-bottom:16px; flex-direction:column; align-items:flex-end; width: 100%;">
                <div class="user-bubble">{content_str}</div>
                {score_badge}
            </div>
            """
        else:
            followup_badge = (
                '<span style="background: #fff0f0; color: #e03131; font-size: 10px; padding: 2px 6px; border-radius: 8px; margin-left: 6px; font-weight:700;">꼬리질문</span>'
                if is_followup
                else ""
            )
            chat_html += f"""
            <div style="display:flex; align-items:flex-start; gap:10px; justify-content:flex-start; margin-bottom:16px; width: 100%;">
                <div style="font-size: 32px; line-height: 1; flex-shrink: 0;">👾</div>
                <div style="flex: 1; min-width: 0;">
                <div style="font-size: 12px; font-weight: 600; color: #bb38d0; margin-bottom: 4px; margin-left: 4px; display: flex; align-items: center;">AI 면접관 {followup_badge}</div>
                <div class="ai-bubble">{content_str}</div>
                </div>
            </div>
            """

    chat_html += """
        </div>
        <script>
            var chatDiv = document.getElementById("chat-container");
            if (chatDiv) {
                chatDiv.scrollTop = chatDiv.scrollHeight;
                setTimeout(() => { chatDiv.scrollTo({ top: chatDiv.scrollHeight, behavior: 'smooth' }); }, 100);
            }
        </script>
    </div>
    """

    components.html(chat_html, height=700, scrolling=False)

    if st.session_state.latest_audio_content:
        st.audio(
            st.session_state.latest_audio_content, format="audio/mp3", autoplay=True
        )
        st.session_state.latest_audio_content = None

    prompt = st.chat_input("메시지를 입력하세요")
    if prompt:
        with st.spinner("답변을 분석 중입니다..."):
            is_success = process_answer(prompt)

        if is_success:
            st.rerun()

# 음성 모드
else:
    st.markdown(
        """
        <div style="background:#ffffff; border-radius:16px; border:1px solid #fae8ff; padding:16px 20px; margin-bottom:16px; box-shadow:0 4px 15px rgba(187,56,208,0.05); font-size:14px; color:#444; line-height:1.6;">
            <strong style="color:#bb38d0;">음성 인식 모드 가이드</strong><br>
            하단의 시작 버튼을 누른 뒤 마이크에 답변을 말씀해 주세요. 카메라를 통해 시선 처리 등의 태도가 함께 분석됩니다.
        </div>
        """,
        unsafe_allow_html=True,
    )

    col_chat, col_cam = st.columns([1.1, 0.9])

    with col_chat:
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key:
            st.error("OPENAI_API_KEY 환경변수가 필요합니다.")
            st.stop()

        html = """
  <style>
  @keyframes msg-pop { 
      from { opacity: 0; transform: translateY(10px); } 
      to { opacity: 1; transform: translateY(0); } 
  }
  </style>
  <div style="background:linear-gradient(135deg, #ffffff 0%, #fdf4ff 100%);border:2px solid #fae8ff;border-radius:24px;padding:24px;box-shadow:0 10px 40px rgba(187,56,208,0.05);">
    <div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px;">
      <button id="btnConnect" style="padding:12px 18px;border-radius:12px;border:1px solid #e8cceb;background:#fff;cursor:pointer;font-weight:700;color:#555;">마이크 연결</button>
      <button id="btnStart" style="padding:12px 18px;border-radius:12px;border:none;background:linear-gradient(135deg, #bb38d0, #872a96);color:#fff;cursor:pointer;font-weight:700;box-shadow:0 4px 10px rgba(187,56,208,0.3);" disabled>녹음 시작</button>
      <button id="btnStop" style="padding:12px 18px;border-radius:12px;border:none;background:#333;color:#fff;cursor:pointer;font-weight:700;" disabled>녹음 중지 및 제출</button>
      <button id="btnEnd" style="padding:12px 18px;border-radius:12px;border:1px solid #e8cceb;background:#fff;cursor:pointer;font-weight:700;color:#555;" disabled>세션 종료</button>
      <button id="btnDownload" style="padding:12px 18px;border-radius:12px;border:1px solid #e8cceb;background:#fff;cursor:pointer;font-weight:700;color:#555;" disabled>스크립트 다운로드</button>
    </div>
    <div id="status" style="font-size:14px;font-weight:600;color:#bb38d0;margin-bottom:12px;background:#fcf0fc;padding:10px 16px;border-radius:10px;display:inline-block;">시스템 대기 중...</div>
    <div style="font-size:14px;font-weight:800;color:#333;margin:12px 0 8px 0;">음성 인식 대화창</div>
    <div id="chat" style="height:360px;overflow:auto;background:#ffffff;border:1px solid #fae8ff;border-radius:16px;padding:20px;box-shadow:inset 0 2px 10px rgba(0,0,0,0.02);"></div>
  </div>
  <script>
  (function () {
    const API_KEY = __API_KEY__;
    const MODEL = __MODEL__;
    const BACKEND_BASE = __BACKEND_BASE__;
    const QUESTIONS = __QUESTIONS__;
    const JOB_ROLE = __JOB_ROLE__;
    const DIFFICULTY = __DIFFICULTY__;
    const PERSONA = __PERSONA__;
    const USER_ID = __USER_ID__;
    const RESUME_TEXT = __RESUME_TEXT__;
    const FIRST_ASSISTANT = __FIRST_ASSISTANT__;
    let currentQuestion = __CURRENT_Q__;
    let qIdx = __Q_IDX__;
    let followupCount = __FOLLOWUP_COUNT__;

    const btnConnect = document.getElementById("btnConnect");
    const btnStart = document.getElementById("btnStart");
    const btnStop = document.getElementById("btnStop");
    const btnEnd = document.getElementById("btnEnd");
    const btnDownload = document.getElementById("btnDownload");
    const statusEl = document.getElementById("status");
    const chatEl = document.getElementById("chat");

    let pc = null;
    let dc = null;
    let stream = null;
    let camStream = null;
    let micTrack = null;
    let connected = false;
    let recording = false;
    let committing = false;
    let recorderMime = "";
    let mediaRecorder = null;
    let currentChunks = [];
    let ended = false;
    const lines = [];
    let pendingUserBubble = null;
    const userAudioClips = [];
    const assistantAudioClips = [];
    let attFrames = [];
    let attTimer = null;
    let lastAttitude = null;
    let pendingAttitudePromise = null;
    let attVideoEl = null;
    let attCanvasEl = null;

    function setStatus(text) { statusEl.textContent = text; }
    function setButtons() {
      btnConnect.disabled = connected || ended;
      btnStart.disabled = !connected || recording || committing || ended;
      btnStop.disabled = !connected || !recording || ended;
      btnEnd.disabled = !connected;
      btnDownload.disabled = lines.length === 0;
    }
    function appendBubble(role, text) {
      const row = document.createElement("div");
      row.style.margin = "12px 0 16px 0";
      let bubbleContainer;
      
      if (role === "user") {
        row.style.display = "flex";
        row.style.justifyContent = "flex-end";
        row.style.flexDirection = "column";
        row.style.alignItems = "flex-end";
        
        const bubble = document.createElement("div");
        bubble.style.maxWidth = "82%";
        bubble.style.padding = "12px 20px";
        bubble.style.borderRadius = "20px 6px 20px 20px";
        bubble.style.whiteSpace = "pre-wrap";
        bubble.style.fontSize = "15px";
        bubble.style.lineHeight = "1.6";
        bubble.style.fontWeight = "500";
        bubble.style.background = "linear-gradient(135deg, #bb38d0 0%, #872a96 100%)";
        bubble.style.color = "#ffffff";
        bubble.style.boxShadow = "0 8px 25px rgba(187, 56, 208, 0.3)";
        bubble.style.animation = "msg-pop 0.3s ease-out both";
        
        const textEl = document.createElement("span");
        textEl.textContent = text;
        bubble.appendChild(textEl);
        bubble._textEl = textEl;
        row.appendChild(bubble);
        bubbleContainer = bubble;
      } else {
        row.style.display = "flex";
        row.style.alignItems = "flex-start";
        row.style.gap = "10px";
        row.style.justifyContent = "flex-start";
        
        const iconDiv = document.createElement("div");
        iconDiv.style.fontSize = "32px";
        iconDiv.style.lineHeight = "1";
        iconDiv.textContent = "👾";
        
        const contentWrapper = document.createElement("div");
        
        const nameDiv = document.createElement("div");
        nameDiv.style.fontSize = "12px";
        nameDiv.style.fontWeight = "600";
        nameDiv.style.color = "#bb38d0";
        nameDiv.style.marginBottom = "4px";
        nameDiv.style.marginLeft = "4px";
        nameDiv.textContent = "AI 면접관";
        
        const bubble = document.createElement("div");
        bubble.style.maxWidth = "500px";
        bubble.style.padding = "12px 22px";
        bubble.style.borderRadius = "6px 20px 20px 20px";
        bubble.style.whiteSpace = "pre-wrap";
        bubble.style.fontSize = "15px";
        bubble.style.lineHeight = "1.6";
        bubble.style.fontWeight = "500";
        bubble.style.background = "#ffffff";
        bubble.style.border = "1px solid #fae8ff";
        bubble.style.color = "#111111";
        bubble.style.boxShadow = "0 4px 20px rgba(187, 56, 208, 0.05)";
        bubble.style.animation = "msg-pop 0.3s ease-out both";
        
        const textEl = document.createElement("span");
        textEl.textContent = text;
        bubble.appendChild(textEl);
        bubble._textEl = textEl;
        
        contentWrapper.appendChild(nameDiv);
        contentWrapper.appendChild(bubble);
        
        row.appendChild(iconDiv);
        row.appendChild(contentWrapper);
        bubbleContainer = bubble;
      }
      
      chatEl.appendChild(row);
      chatEl.scrollTop = chatEl.scrollHeight;
      lines.push(`[${role === "user" ? "지원자" : "AI 면접관"}] ${text}`);
      setButtons();
      return bubbleContainer;
    }

    function attachAudioControls(targetBubble, clip) {
      if (!targetBubble) return;
      const wrap = document.createElement("div");
      wrap.style.marginTop = "8px";
      wrap.style.display = "flex";
      wrap.style.gap = "8px";
      wrap.style.alignItems = "center";
      wrap.style.flexWrap = "wrap";

      const listenBtn = document.createElement("button");
      listenBtn.textContent = "다시듣기";
      listenBtn.style.padding = "6px 10px";
      listenBtn.style.border = "1px solid #e8cceb";
      listenBtn.style.borderRadius = "8px";
      listenBtn.style.background = "#fff";
      listenBtn.style.cursor = "pointer";
      listenBtn.style.fontSize = "12px";
      listenBtn.style.fontWeight = "700";
      listenBtn.style.color = "#555";
      listenBtn.addEventListener("click", async () => {
        try {
          const a = new Audio(clip.url);
          await a.play();
        } catch (_) {}
      });

      const downloadBtn = document.createElement("button");
      downloadBtn.textContent = "음성 다운로드";
      downloadBtn.style.padding = "6px 10px";
      downloadBtn.style.border = "1px solid #e8cceb";
      downloadBtn.style.borderRadius = "8px";
      downloadBtn.style.background = "#fff";
      downloadBtn.style.cursor = "pointer";
      downloadBtn.style.fontSize = "12px";
      downloadBtn.style.fontWeight = "700";
      downloadBtn.style.color = "#555";
      downloadBtn.addEventListener("click", () => {
        const a = document.createElement("a");
        a.href = clip.url;
        a.download = clip.filename;
        a.click();
      });

      wrap.appendChild(listenBtn);
      wrap.appendChild(downloadBtn);
      targetBubble.appendChild(wrap);
    }

    async function createAssistantClipFromText(text) {
      const pureText = (text || "").trim();
      if (!pureText) return null;
      const res = await fetch(`${BACKEND_BASE}/infer/tts`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: pureText }),
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(`TTS 생성 실패: ${res.status} ${t}`);
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const ts = new Date();
      const clip = {
        url,
        filename: `assistant_tts_${ts.toISOString().replace(/[:.]/g, "-")}.mp3`,
      };
      assistantAudioClips.push(clip);
      return clip;
    }

    async function ensureAssistantClipFromText(targetBubble) {
      if (!targetBubble) return null;
      if (targetBubble._assistantClip) return targetBubble._assistantClip;
      const text = (targetBubble._textEl ? targetBubble._textEl.textContent : targetBubble.textContent || "").trim();
      const clip = await createAssistantClipFromText(text);
      targetBubble._assistantClip = clip;
      return clip;
    }

    async function attachAssistantControls(targetBubble, autoPlay = false) {
      if (!targetBubble || targetBubble._assistantControlsAttached) return;
      targetBubble._assistantControlsAttached = true;
      try {
        const clip = await ensureAssistantClipFromText(targetBubble);
        if (!clip) return;
        attachAudioControls(targetBubble, clip);
        if (autoPlay) {
          try {
            const a = new Audio(clip.url);
            await a.play();
          } catch (_) {
            setStatus("자동 재생이 차단되었습니다. '다시듣기' 버튼을 눌러 재생해 주세요.");
          }
        }
      } catch (e) {
        setStatus(`면접관 음성 생성 오류: ${e.message || e}`);
      }
    }

    async function evaluateTurn(answerText, attitude) {
      const nextQ = (qIdx + 1 < QUESTIONS.length) ? QUESTIONS[qIdx + 1] : null;
      const payload = {
        question: currentQuestion || "면접 질문",
        answer: answerText,
        job_role: JOB_ROLE,
        difficulty: DIFFICULTY,
        persona_style: PERSONA,
        user_id: USER_ID,
        resume_text: RESUME_TEXT,
        next_main_question: nextQ,
        followup_count: followupCount,
        attitude: attitude
      };

      const res = await fetch(`${BACKEND_BASE}/infer/evaluate-turn`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const t = await res.text();
        throw new Error(`평가 API 오류: ${res.status} ${t}`);
      }
      return await res.json();
    }

    async function handleTranscript(transcript) {
      if (!transcript || !transcript.trim()) {
        setStatus("음성을 인식하지 못했습니다. 다시 시도해 주세요.");
        return;
      }

      if (pendingUserBubble) {
        if (pendingUserBubble._textEl) {
          pendingUserBubble._textEl.textContent = transcript.trim();
        } else {
          pendingUserBubble.textContent = transcript.trim();
        }
        lines.pop();
        lines.push(`[지원자] ${transcript.trim()}`);
        pendingUserBubble = null;
      } else {
        appendBubble("user", transcript.trim());
      }

      setStatus("답변 분석 및 평가 진행 중...");
      try {
        let attitudeResult = lastAttitude;
        if (pendingAttitudePromise) {
          try {
            attitudeResult = await pendingAttitudePromise;
          } catch (_) {
            attitudeResult = null;
          }
          pendingAttitudePromise = null;
        }

        const evalRes = await evaluateTurn(transcript.trim(), attitudeResult);
        let reply = (evalRes.reply_text || "").trim();
        const isFollowup = !!evalRes.is_followup;
        const score = Number(evalRes.score || 0);

        if (reply.includes("[INTERVIEW_END]")) {
          ended = true;
          reply = reply.replace("[INTERVIEW_END]", "").trim();
        }
        if (reply.includes("[NEXT_MAIN]")) {
          qIdx += 1;
          reply = reply.replace("[NEXT_MAIN]", "").trim();
        }
        followupCount = isFollowup ? followupCount + 1 : 0;
        currentQuestion = reply || currentQuestion;

        const assistantText = `${reply}${Number.isFinite(score) ? `\\n\\n(AI 평가 점수: ${score.toFixed(1)}/10)` : ""}`;
        let prebuiltClip = null;
        try {
          setStatus("면접관 음성 생성 중...");
          prebuiltClip = await createAssistantClipFromText(assistantText);
          const audio = new Audio(prebuiltClip.url);
          await audio.play();
        } catch (_) {
          setStatus("자동 재생이 차단되었습니다. '다시듣기' 버튼을 눌러 재생해 주세요.");
        }

        const assistantBubble = appendBubble("assistant", assistantText);
        if (prebuiltClip) {
          assistantBubble._assistantClip = prebuiltClip;
          attachAudioControls(assistantBubble, prebuiltClip);
        } else {
          await attachAssistantControls(assistantBubble, false);
        }
        if (ended) {
          setStatus("모든 질문이 종료되었습니다. 상단의 [면접 종료] 버튼을 눌러주세요.");
        } else {
          setStatus("응답 완료. 다음 발화를 시작하세요.");
        }
      } catch (e) {
        setStatus(`평가 실패: ${e.message || e}`);
      } finally {
        committing = false;
        setButtons();
      }
    }

    function sendEvent(evt) {
      if (!(dc && dc.readyState === "open")) return false;
      dc.send(JSON.stringify(evt));
      return true;
    }

    function startAttitudeCapture() {
      if (!attVideoEl || !attCanvasEl) return;
      attFrames = [];
      const ctx = attCanvasEl.getContext("2d");
      const startTs = performance.now();

      stopAttitudeCapture();
      attTimer = setInterval(() => {
        try {
          if (attVideoEl.readyState < 2 || !attVideoEl.videoWidth) return;
          const w = 320;
          const h = Math.round((attVideoEl.videoHeight / attVideoEl.videoWidth) * w);
          attCanvasEl.width = w;
          attCanvasEl.height = h;
          ctx.drawImage(attVideoEl, 0, 0, w, h);
          const dataUrl = attCanvasEl.toDataURL("image/jpeg", 0.6);
          attFrames.push({
            t_ms: Math.round(performance.now() - startTs),
            image_b64: dataUrl.split(",")[1],
          });
        } catch (_) {}
      }, 500);
    }

    function stopAttitudeCapture() {
      if (attTimer) clearInterval(attTimer);
      attTimer = null;
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
        const audioOnlyStream = new MediaStream([micTrack]);
        mediaRecorder = new MediaRecorder(audioOnlyStream, recorderMime ? { mimeType: recorderMime } : undefined);
        mediaRecorder.ondataavailable = (e) => {
          if (e.data && e.data.size > 0) currentChunks.push(e.data);
        };
        mediaRecorder.onstop = () => {
          const blob = new Blob(currentChunks, { type: mediaRecorder.mimeType || "audio/webm" });
          currentChunks = [];
          if (blob.size <= 0) return;
          const url = URL.createObjectURL(blob);
          const ts = new Date();
          const clip = {
            url,
            filename: `user_turn_${ts.toISOString().replace(/[:.]/g, "-")}.webm`,
          };
          userAudioClips.push(clip);
          if (pendingUserBubble) {
            attachAudioControls(pendingUserBubble, clip);
          }
        };

        if (!attVideoEl) {
          attVideoEl = document.createElement("video");
          attVideoEl.autoplay = true;
          attVideoEl.muted = true;
          attVideoEl.playsInline = true;
          attVideoEl.style.display = "none";
          document.body.appendChild(attVideoEl);
        }
        camStream = await navigator.mediaDevices.getUserMedia({ video: true });
        attVideoEl.srcObject = camStream;
        try {
          await attVideoEl.play();
        } catch (_) {}

        if (!attCanvasEl) {
          attCanvasEl = document.createElement("canvas");
          attCanvasEl.style.display = "none";
          document.body.appendChild(attCanvasEl);
        }

        pc = new RTCPeerConnection();
        pc.addTrack(micTrack, stream);
        dc = pc.createDataChannel("oai-events");

        dc.onopen = async () => {
          connected = true;
          setStatus("연결 완료. [녹음 시작] 버튼을 눌러 발화하세요.");
          setButtons();
          sendEvent({
            type: "session.update",
            session: {
              modalities: ["audio", "text"],
              turn_detection: null,
              input_audio_transcription: { model: "whisper-1" }
            }
          });
          const firstText = (FIRST_ASSISTANT && FIRST_ASSISTANT.trim())
            ? FIRST_ASSISTANT.trim()
            : "안녕하세요. 시작 버튼을 누르고 답변 후 중지 버튼을 눌러 제출해 주세요.";
          let firstClip = null;
          try {
            setStatus("첫 질문 음성 생성 중...");
            firstClip = await createAssistantClipFromText(firstText);
            const audio = new Audio(firstClip.url);
            await audio.play();
          } catch (_) {
            setStatus("자동 재생이 차단되었습니다. '다시듣기' 버튼을 눌러 재생해 주세요.");
          }
          const firstBubble = appendBubble("assistant", firstText);
          if (firstClip) {
            firstBubble._assistantClip = firstClip;
            attachAudioControls(firstBubble, firstClip);
          } else {
            attachAssistantControls(firstBubble, false);
          }
        };

        dc.onclose = () => {
          connected = false;
          recording = false;
          committing = false;
          setStatus("서버와의 연결이 종료되었습니다.");
          setButtons();
        };

        dc.onmessage = async (event) => {
          let data = null;
          try { data = JSON.parse(event.data); } catch (_) { return; }
          if (!data || !data.type) return;

          if (data.type === "conversation.item.input_audio_transcription.failed") {
            committing = false;
            setStatus("음성 인식 실패. 다시 시도해 주세요.");
            setButtons();
            return;
          }
          if (data.type === "conversation.item.input_audio_transcription.completed") {
            await handleTranscript((data.transcript || "").trim());
            return;
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
      } catch (err) {
        setStatus("연결 오류: " + (err?.message || err));
      }
    }

    function startTurn() {
      if (!connected || !micTrack || committing || ended) return;
      micTrack.enabled = true;
      recording = true;
      if (mediaRecorder && mediaRecorder.state === "inactive") {
        currentChunks = [];
        mediaRecorder.start(1000);
      }
      sendEvent({ type: "input_audio_buffer.clear" });
      setStatus("녹음 중... 답변 후 [제출]을 눌러주세요.");
      setButtons();
      startAttitudeCapture();
    }

    function stopTurn() {
      if (!connected || !micTrack || !recording || committing || ended) return;
      micTrack.enabled = false;
      recording = false;
      if (mediaRecorder && mediaRecorder.state === "recording") {
        mediaRecorder.stop();
      }
      committing = true;
      setStatus("음성을 텍스트로 변환하여 서버에 제출 중...");
      pendingUserBubble = appendBubble("user", "(음성 분석 및 제출 중...)");
      setButtons();
      stopAttitudeCapture();
      lastAttitude = null;
      setTimeout(() => {
        const ok = sendEvent({ type: "input_audio_buffer.commit" });
        if (!ok) {
          committing = false;
          setStatus("제출 실패: 네트워크 연결을 확인해주세요.");
          setButtons();
        }
      }, 250);
      pendingAttitudePromise = fetch(`${BACKEND_BASE}/infer/attitude`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ frames: attFrames.slice(0, 40) }),
      })
        .then((res) => res.ok ? res.json() : null)
        .then((data) => {
          lastAttitude = data;
          return data;
        })
        .catch(() => null);
    }

    function endSession() {
      try {
        ended = true;
        if (micTrack) micTrack.enabled = false;
        if (dc) dc.close();
        if (pc) pc.close();
        if (stream) stream.getTracks().forEach(t => t.stop());
        if (camStream) camStream.getTracks().forEach(t => t.stop());
      } catch (_) {}
      connected = false;
      recording = false;
      committing = false;
      setStatus("세션이 종료되었습니다.");
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
            .replace(
                "__MODEL__",
                json.dumps(
                    os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview")
                ),
            )
            .replace("__BACKEND_BASE__", json.dumps(API_BASE_URL.rstrip("/")))
            .replace(
                "__QUESTIONS__",
                json.dumps(
                    st.session_state.get("db_questions", []), ensure_ascii=False
                ),
            )
            .replace(
                "__JOB_ROLE__",
                json.dumps(
                    st.session_state.get("job_role", "Python 백엔드 개발자"),
                    ensure_ascii=False,
                ),
            )
            .replace(
                "__DIFFICULTY__",
                json.dumps(
                    st.session_state.get("difficulty", "미들"), ensure_ascii=False
                ),
            )
            .replace(
                "__PERSONA__",
                json.dumps(
                    st.session_state.get("persona_style", "깐깐한 기술팀장"),
                    ensure_ascii=False,
                ),
            )
            .replace(
                "__USER_ID__",
                json.dumps(
                    str(st.session_state.get("db_session_id", "guest")),
                    ensure_ascii=False,
                ),
            )
            .replace(
                "__RESUME_TEXT__",
                json.dumps(
                    st.session_state.get("resume_text", "") or "", ensure_ascii=False
                ),
            )
            .replace(
                "__FIRST_ASSISTANT__",
                json.dumps(
                    (st.session_state.get("messages") or [{}])[0].get("content", ""),
                    ensure_ascii=False,
                ),
            )
            .replace(
                "__CURRENT_Q__",
                json.dumps(
                    st.session_state.get("pending_question", "면접 질문"),
                    ensure_ascii=False,
                ),
            )
            .replace(
                "__Q_IDX__", json.dumps(int(st.session_state.get("current_q_idx", 0)))
            )
            .replace(
                "__FOLLOWUP_COUNT__",
                json.dumps(int(st.session_state.get("current_followup_count", 0))),
            )
        )
        components.html(html, height=680, scrolling=False)
        st.markdown("<br>", unsafe_allow_html=True)

    with col_cam:
        webcam_box(height=606)