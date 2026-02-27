"""
File: pages/interview.py
Description: AI 면접 페이지 (텍스트 + Python 음성 모드)
"""

import base64
import hashlib
import io
import json
import os
import sys

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv
from openai import OpenAI
from utils.webcam_box import webcam_box
from utils.config import API_BASE_URL
from utils.function import require_login, inject_custom_header  # 👈 문지기 함수 임포트!


# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
backend_dir = os.path.join(root_dir, "backend")
if backend_dir not in sys.path:
    sys.path.append(backend_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

load_dotenv()

from db.database import (
    create_session,
    end_session,
    get_common_questions,
    get_questions_by_role,
    init_db,
    save_detail,
)
from services.llm_service import (
    evaluate_and_respond,
    extract_keywords_from_resume,
    generate_evaluation,
)
from services.rag_service import clear_resume_for_session, store_resume


# ─── 페이지 기본 설정 및 로그인 검증 ─────────────────────────
st.set_page_config(page_title="AIWORK", page_icon="👾", layout="centered")




def get_image_base64(image_path: str) -> str:
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


def inject_custom_header() -> None:
    image_path = os.path.join(root_dir, "frontend", "assets", "AIWORK.jpg")
    try:
        img_src = f"data:image/jpeg;base64,{get_image_base64(image_path)}"
    except Exception:
        img_src = ""

    st.markdown(
        f"""
        <style>
        .block-container {{
            padding-top: 100px !important;
            max-width: 720px !important;
            padding-bottom: 5rem !important;
        }}
        .custom-header {{
            position: fixed; top: 0; left: 0; right: 0; height: 72px;
            background-color: #ffffff; display: flex; align-items: center; justify-content: space-between;
            padding: 0 40px; border-bottom: 1px solid #e2e8f0; z-index: 999999;
            font-family: 'Pretendard', sans-serif;
        }}
        .header-logo {{ display: flex; align-items: center; text-decoration: none; }}
        .header-logo img {{ height: 28px; width: auto; object-fit: contain; }}
        .header-menu {{ display: flex; gap: 40px; position: absolute; left: 50%; transform: translateX(-50%); }}
        .header-menu a {{ text-decoration: none; color: #111111; font-size: 16px; font-weight: 600; transition: color 0.2s; }}
        .header-menu a:hover {{ color: #bb38d0; }}
        .header-utils {{ display: flex; align-items: center; }}
        .icon-group {{ display: flex; font-size: 24px; }}
        .icon-group a {{ text-decoration: none; color: #333333; transition: transform 0.2s; display: flex; align-items: center; justify-content: center; }}
        .icon-group a:hover {{ transform: scale(1.1); }}
        </style>
        <div class="custom-header">
            <a href="/home" target="_self" class="header-logo"><img src="{img_src}" alt="AIWORK 로고"></a>
            <div class="header-menu">
                <a href="/interview" target="_self">AI면접</a>
                <a href="/resume" target="_self">이력서</a>
                <a href="/mypage" target="_self">내 기록</a>
                <a href="/my_info" target="_self">마이페이지</a>
            </div>
            <div class="header-utils">
                <div class="icon-group"><a href="/my_info" target="_self" title="마이페이지">👤</a></div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

inject_custom_header()


def extract_resume_text(uploaded_file) -> str:
    try:
        import fitz

        return "".join(
            page.get_text()
            for page in fitz.open(stream=uploaded_file.read(), filetype="pdf")
        ).strip()
    except Exception:
        try:
            return uploaded_file.read().decode("utf-8", errors="ignore")
        except Exception:
            return ""


def render_message(
    role: str, content: str, is_followup: bool = False, score: float | None = None
) -> None:
    if role == "user":
        score_badge = (
            f'<div class="score-mini">✦ {score:.1f}/10</div>' if score is not None else ""
        )
        st.markdown(
            f'<div style="display:flex;justify-content:flex-end;flex-direction:column;align-items:flex-end;margin-bottom:4px;">'
            f'<div class="user-bubble">{content}</div>{score_badge}</div>',
            unsafe_allow_html=True,
        )
    else:
        followup_badge = (
            '<div class="followup-badge">💡 꼬리질문 포함</div>' if is_followup else ""
        )
        st.markdown(
            f'<div style="display:flex;justify-content:flex-start;margin-bottom:4px;">'
            f'<div style="display:flex;flex-direction:column;">'
            f'<div class="sender-label">AI 면접관</div>{followup_badge}<div class="ai-bubble">{content}</div>'
            f"</div></div>",
            unsafe_allow_html=True,
        )


def transcribe_audio(audio_bytes: bytes) -> str:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if api_key:
        try:
            client = OpenAI(api_key=api_key)
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
        except Exception:
            pass

    try:
        from backend.services.local_inference import local_stt

        text = local_stt(audio_bytes, language="ko")
        if text and text.strip():
            return text.strip()
    except Exception:
        pass
    return ""


def generate_tts(text: str) -> bytes | None:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return None
    try:
        client = OpenAI(api_key=api_key)
        tts_response = client.audio.speech.create(model="tts-1", voice="echo", input=text)
        return tts_response.content
    except Exception:
        return None


def save_turn_to_db(
    session_id: int | None,
    turn_index: int,
    question: str,
    answer: str,
    is_followup: bool,
    score: float,
    feedback: str,
) -> int:
    if not session_id:
        return turn_index
    save_detail(session_id, turn_index, question, answer, is_followup, score, feedback)
    return turn_index + 1


def process_answer(answer_text: str) -> None:
    prev_question = st.session_state.pending_question or "면접 질문"
    st.session_state.messages.append({"role": "user", "content": answer_text, "score": None})

    db_qs = st.session_state.get("db_questions", [])
    idx = st.session_state.get("current_q_idx", 0)
    next_q = db_qs[idx + 1] if idx + 1 < len(db_qs) else None

    eval_res = evaluate_and_respond(
        question=prev_question,
        answer=answer_text,
        job_role=st.session_state.job_role,
        difficulty=st.session_state.difficulty,
        persona_style=st.session_state.persona_style,
        user_id=st.session_state.user_id, # 🔥 이제 여기에 안전한 진짜 숫자 ID가 들어갑니다!
        resume_text=st.session_state.resume_text,
        next_main_question=next_q,
        followup_count=st.session_state.current_followup_count,
    )

    score = float(eval_res.get("score", 5.0))
    feedback = eval_res.get("feedback", "")
    ai_reply = eval_res.get("reply_text", "")
    is_followup = bool(eval_res.get("is_followup", False))

    st.session_state.db_scores.append(score)
    st.session_state.messages[-1]["score"] = score

    st.session_state.turn_index = save_turn_to_db(
        st.session_state.db_session_id,
        st.session_state.turn_index,
        prev_question,
        answer_text,
        st.session_state.current_is_followup,
        score,
        feedback,
    )

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


try:
    init_db()
except Exception as e:
    st.warning(f"DB 초기화 실패: {e}")

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700&display=swap');
    * { font-family: 'Pretendard', sans-serif !important; box-sizing: border-box; }
    html, body, .stApp { background-color: #f5f5f5 !important; }
    [data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer { display: none !important; visibility: hidden; }
    .setup-card { background: #fff; border-radius: 20px; box-shadow: 0 4px 24px rgba(0,0,0,0.07); padding: 36px 32px; margin-bottom: 24px; }
    .page-title { font-size: 26px; font-weight: 700; color: #bb38d0 !important; text-align: center; margin-bottom: 6px; }
    .page-subtitle { font-size: 14px; color: #888 !important; text-align: center; margin-bottom: 0; }
    .persona-badge { display: inline-block; background: linear-gradient(135deg, #bb38d0, #7b2cb1); color: white !important; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; margin-left: 8px; }
    .chat-header { display: flex; align-items: center; gap: 12px; background: #fff; border-radius: 14px; box-shadow: 0 1px 8px rgba(0,0,0,0.06); padding: 14px 20px; margin-bottom: 16px; }
    .chat-header-icon { width: 44px; height: 44px; border-radius: 12px; background: linear-gradient(135deg, #bb38d0, #7b2cb1); display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }
    .chat-header-name { font-size: 16px; font-weight: 700; color: #333 !important; }
    .chat-header-info { font-size: 12px; color: #999 !important; }
    .ai-bubble { background: #fff; border: 1px solid #eee; border-radius: 16px; border-top-left-radius: 4px; padding: 14px 18px; max-width: 82%; color: #333 !important; font-size: 15px; line-height: 1.8; margin-bottom: 10px; white-space: pre-wrap; }
    .user-bubble { background: linear-gradient(135deg, #bb38d0, #8b1faa); border-radius: 16px; border-top-right-radius: 4px; padding: 14px 18px; max-width: 82%; color: #fff !important; font-size: 15px; line-height: 1.8; margin-bottom: 10px; white-space: pre-wrap; }
    .sender-label { font-size: 11px; color: #bb38d0 !important; font-weight: 700; margin-bottom: 4px; }
    .followup-badge { display: inline-block; background: #fff3e0; color: #e67e22 !important; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 6px; margin-bottom: 6px; }
    .score-mini { display: inline-block; background: #f0fdf4; color: #16a34a !important; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 6px; margin-top: 4px; }
    [data-testid="stButton"] > button[kind="primary"],
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #bb38d0, #8b1faa) !important;
        color: #fff !important;
        border: none !important;
        border-radius: 10px !important;
        height: 50px !important;
        font-size: 16px !important;
        font-weight: 700 !important;
    }
    [data-testid="stButton"] > button:not([kind="primary"]),
    .stButton > button:not([kind="primary"]) {
        background: #fff !important;
        color: #555 !important;
        border: 1px solid #ddd !important;
        border-radius: 10px !important;
        height: 50px !important;
        font-size: 16px !important;
        font-weight: 600 !important;
    }
    .result-card { background: #fff; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.07); padding: 28px 24px; margin-bottom: 20px; }
    .result-title { font-size: 22px; font-weight: 700; color: #bb38d0 !important; text-align: center; margin-bottom: 20px; }
    .score-circle { width: 120px; height: 120px; border-radius: 50%; background: linear-gradient(135deg, #bb38d0, #7b2cb1); display: flex; flex-direction: column; align-items: center; justify-content: center; margin: 0 auto 20px auto; }
    .score-number { font-size: 32px; font-weight: 800; color: #fff !important; }
    .score-label { font-size: 11px; color: rgba(255,255,255,0.85) !important; font-weight: 600; }
    .realtime-guide { background: #fff; border-radius: 12px; border: 1px solid #eaeaea; padding: 12px 14px; margin-bottom: 12px; color:#555 !important; font-size: 13px; line-height: 1.5; }
    .chat-box-title { font-size: 13px; font-weight: 700; color: #666 !important; margin: 6px 0 8px 2px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# require_login()  # 로그인 안 된 사용자는 여기서 튕겨냅니다.

if "user" in st.session_state and st.session_state.user:
    current_user_id = st.session_state.user.get("id")
else:
    current_user_id = None


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
    "user_id": current_user_id, # 🔥 문지기 함수에서 받아온 진짜 ID를 기본값으로 세팅!
    "latest_audio_content": None,
    "last_voice_hash": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

@st.dialog("면접 결과 리포트")
def evaluation_modal():
    scores = st.session_state.db_scores
    total_score = round((sum(scores) / len(scores)) * 10, 1) if scores else 0.0
    st.markdown(
        f'<div class="score-circle"><span class="score-number">{total_score}</span><span class="score-label">/ 100</span></div>',
        unsafe_allow_html=True,
    )

    if not st.session_state.get("resume_used", False):
        st.warning("이력서를 연동하지 않은 자율 면접이므로, 직무/이력서 매칭률 점수 및 이력서 기반 포트폴리오 평가는 제공되지 않습니다.")
        eval_resume_text = None
    else:
        eval_resume_text = st.session_state.get("resume_text")

    if st.session_state.evaluation_result is None:
        with st.spinner("AI가 분석 중입니다..."):
            st.session_state.evaluation_result = generate_evaluation(
                st.session_state.messages,
                st.session_state.get("job_role"),
                st.session_state.get("difficulty"),
                eval_resume_text,
            )

    st.markdown(st.session_state.evaluation_result)
    
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


if not st.session_state.chatbot_started:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        '<div class="setup-card"><div class="page-title">🎯 AI 모의면접</div><div class="page-subtitle">실전과 동일한 환경에서 기술 면접을 연습하세요</div></div>',
        unsafe_allow_html=True,
    )

    mode = st.radio("면접 방식", ["💬 텍스트 면접", "🎙️ 음성 면접(Python STT)"], index=0)
    persona_style = st.radio(
        "면접관 스타일",
        ["깐깐한 기술팀장", "부드러운 인사담당자", "스타트업 CTO"],
    )

    col1, col2 = st.columns(2)
    with col1:
        job_role = st.selectbox(
            "직무 선택",
            [
                "Python 백엔드 개발자",
                "Java 백엔드 개발자",
                "AI/ML 엔지니어",
                "데이터 엔지니어",
                "프론트엔드 개발자",
                "풀스택 개발자",
            ],
        )
    with col2:
        difficulty = st.selectbox("난이도 선택", ["상", "중", "하"], index=1)
    q_count = st.slider("질문 수", 3, 10, 5)

    has_saved_resume = bool(st.session_state.get("resume_id"))
    saved_resume_title = st.session_state.get("resume_title", "이력서")
    
    manual_tech_stack = None
    uploaded_resume = None

    if has_saved_resume:
        st.info(f"선택하신 '{saved_resume_title}' 이력서를 기반으로 면접이 진행됩니다.")
        if st.button("선택 해제하고 직접 입력하기", use_container_width=False):
            st.session_state.resume_id = None
            st.session_state.resume_text = None
            st.session_state.resume_title = None
            st.rerun()
    else:
        input_method = st.radio("데이터 입력 방식", ["직접 입력", "이력서 첨부"], horizontal=True)
        
        if input_method == "직접 입력":
            st.markdown("**📄 보유 기술 스택 및 핵심 프로젝트 경험**", unsafe_allow_html=True)
            manual_tech_stack = st.text_area("예: Spring Boot, JPA, React 경험이 있습니다.", placeholder="면접에서 어필할 핵심 기술이나 프로젝트 경험을 적어주세요.", height=120)
            disable_start = not bool(manual_tech_stack and manual_tech_stack.strip())
        else:
            st.markdown("**📄 이력서 새로 업로드 <span style='color:#e53e3e;font-size:13px;'>(필수)</span>**", unsafe_allow_html=True)
            uploaded_resume = st.file_uploader("PDF/TXT 이력서를 올려주세요", type=["pdf", "txt"], label_visibility="collapsed")
            disable_start = not bool(uploaded_resume)

    st.markdown("<br>", unsafe_allow_html=True)
    col_start, col_back = st.columns([3, 1])
    with col_start:
        if st.button(
            "면접 시작하기",
            type="primary",
            use_container_width=True,
            disabled=disable_start,
        ):
            # 1. 텍스트 세팅 및 사용 여부 판단
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
                is_resume_used = False # 텍스트 입력은 이력서로 취급 안함

            # 2. DB 세션 생성
            try:
                db_session_id = create_session(
                    user_id=st.session_state["user_id"],
                    job_role=job_role,
                    difficulty=difficulty,
                    persona=persona_style,
                    resume_used=is_resume_used,
                )
            except Exception as e:
                st.error(f"세션 생성 오류: {e}")
                db_session_id = None

            # 3. RAG 벡터 DB에 저장 (이력서 모드일 때만 수행)
            if final_resume_text and db_session_id and is_resume_used:
                with st.spinner("이력서 저장 중..."):
                    store_resume(final_resume_text, user_id=str(db_session_id))

            # 4. 질문 생성 로직 (첫 질문 자기소개 고정)
            try:
                fixed_first_q = "간단하게 자기소개를 부탁드립니다."
                
                if final_resume_text:
                    if is_resume_used:
                        keywords = extract_keywords_from_resume(final_resume_text)
                    else:
                        keywords = extract_keywords_from_text_input(final_resume_text)
                        
                    tech_qs = get_questions_by_resume_keywords(
                        job_role, difficulty, keywords, limit=q_count - 1
                    )
                else:
                    tech_qs = get_questions_by_role(job_role, difficulty, limit=q_count - 1)
                
                db_questions = [fixed_first_q] + [q["question"] for q in tech_qs]
                
                if len(db_questions) == 1:
                    raise ValueError("질문 없음")
                    
            except Exception:
                db_questions = ["간단하게 자기소개를 부탁드립니다."] + [
                    f"{job_role} 관련 핵심 기술을 설명해주세요." for _ in range(q_count - 1)
                ]

            # 5. 첫 인사말 및 세션 업데이트
            first_q = db_questions[0]
            greeting = (
                f"안녕하세요! 오늘 {job_role} 면접을 진행할 면접관입니다. "
                f"총 {q_count}개의 질문을 드리겠습니다.\n\n첫 번째 질문입니다.\n**{first_q}**"
            )
            
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
                    "last_voice_hash": None,
                }
            )
            st.rerun()
    with col_back:
        if st.button("홈", use_container_width=True):
            st.switch_page("app.py")
    st.stop()


if st.session_state.interview_ended:
    st.markdown("<br><div class='result-card'><div class='result-title'>📋 면접 결과 리포트</div></div>", unsafe_allow_html=True)
    scores = st.session_state.db_scores
    total_score = round((sum(scores) / len(scores)) * 10, 1) if scores else 0.0
    st.markdown(
        f'<div class="score-circle"><span class="score-number">{total_score}</span><span class="score-label">/ 100점</span></div>',
        unsafe_allow_html=True,
    )

    if st.session_state.db_session_id:
        try:
            end_session(st.session_state.db_session_id, total_score)
            clear_resume_for_session(str(st.session_state.db_session_id))
        except Exception:
            pass

    if st.session_state.evaluation_result is None:
        with st.spinner("AI가 분석 중입니다..."):
            st.session_state.evaluation_result = generate_evaluation(
                st.session_state.messages,
                st.session_state.get("job_role"),
                st.session_state.get("difficulty"),
                st.session_state.get("resume_text"),
            )

    st.markdown(st.session_state.evaluation_result)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 다시 시작", type="primary", use_container_width=True):
            for k, v in defaults.items():
                st.session_state[k] = v
            st.rerun()
    with col2:
        if st.button("내 기록 보러가기 ➔", use_container_width=True):
            st.switch_page("pages/mypage.py")
    st.stop()


st.markdown(
    f"""
    <div class="chat-header">
        <div class="chat-header-icon">{'🎙️' if st.session_state.interview_mode == 'voice' else '🎯'}</div>
        <div>
            <div class="chat-header-name">AI 면접관 <span class="persona-badge">{st.session_state.persona_style}</span></div>
            <div class="chat-header-info">{st.session_state.job_role} · {st.session_state.difficulty} · {st.session_state.q_count}문항 · {'음성' if st.session_state.interview_mode == 'voice' else '텍스트'}</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

if st.session_state.interview_mode == "voice":
    st.markdown(
        """
        <div class="realtime-guide">
            <strong>사용 방법</strong><br>
            시작 버튼을 누른 뒤 답변 후 제출해주세요.<br>
            음성이 STT로 변환된 뒤 텍스트 기반으로 면접관이 답변합니다.
        </div>
        """,
        unsafe_allow_html=True,
    )

if st.session_state.interview_mode == "text":
    st.markdown('<div class="chat-box-title">대화창</div>', unsafe_allow_html=True)
    with st.container(height=360, border=True):
        for message in st.session_state.messages:
            render_message(
                message["role"],
                message["content"],
                is_followup="💡" in message.get("content", ""),
                score=message.get("score"),
            )

if st.session_state.latest_audio_content:
    st.audio(st.session_state.latest_audio_content, format="audio/mp3", autoplay=True)
    st.session_state.latest_audio_content = None


if st.session_state.interview_mode == "text":
    prompt = st.chat_input("답변을 입력하세요...")
    if prompt:
        with st.spinner("답변을 분석 중입니다..."):
            process_answer(prompt)
        st.rerun()
else:
    st.markdown("#### 음성 답변 (Realtime STT)")
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        st.error("OPENAI_API_KEY 환경변수가 필요합니다.")
        st.stop()

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

    const listenBtn = document.createElement("button");
    listenBtn.textContent = "다시듣기";
    listenBtn.style.padding = "4px 8px";
    listenBtn.style.border = "1px solid #ddd";
    listenBtn.style.borderRadius = "6px";
    listenBtn.style.background = "#fff";
    listenBtn.style.cursor = "pointer";
    listenBtn.addEventListener("click", async () => {
      try {
        const a = new Audio(clip.url);
        await a.play();
      } catch (_) {}
    });

    const downloadBtn = document.createElement("button");
    downloadBtn.textContent = "음성 다운로드";
    downloadBtn.style.padding = "4px 8px";
    downloadBtn.style.border = "1px solid #ddd";
    downloadBtn.style.borderRadius = "6px";
    downloadBtn.style.background = "#fff";
    downloadBtn.style.cursor = "pointer";
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

  async function evaluateTurn(answerText) {
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
      followup_count: followupCount
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

    setStatus("답변 평가 중...");
    try {
      const evalRes = await evaluateTurn(transcript.trim());
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

      const assistantText = `${reply}${Number.isFinite(score) ? `\n\n(점수: ${score.toFixed(1)}/10)` : ""}`;
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
        setStatus("모든 질문이 종료되었습니다. 종료 버튼을 눌러주세요.");
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

      pc = new RTCPeerConnection();
      pc.addTrack(micTrack, stream);
      dc = pc.createDataChannel("oai-events");

      dc.onopen = async () => {
        connected = true;
        setStatus("연결 완료. 시작 버튼을 눌러 발화하세요.");
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
        setStatus("연결이 종료되었습니다.");
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
    setStatus("녹음 중... 중지를 눌러 제출하세요.");
    setButtons();
  }

  function stopTurn() {
    if (!connected || !micTrack || !recording || committing || ended) return;
    micTrack.enabled = false;
    recording = false;
    if (mediaRecorder && mediaRecorder.state === "recording") {
      mediaRecorder.stop();
    }
    committing = true;
    setStatus("제출 중...");
    pendingUserBubble = appendBubble("user", "(음성 제출 중...)");
    setButtons();
    setTimeout(() => {
      const ok = sendEvent({ type: "input_audio_buffer.commit" });
      if (!ok) {
        committing = false;
        setStatus("제출 실패: 연결 상태를 확인해주세요.");
        setButtons();
      }
    }, 250);
  }

  function endSession() {
    try {
      ended = true;
      if (micTrack) micTrack.enabled = false;
      if (dc) dc.close();
      if (pc) pc.close();
      if (stream) stream.getTracks().forEach(t => t.stop());
    } catch (_) {}
    connected = false;
    recording = false;
    committing = false;
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
        .replace("__MODEL__", json.dumps(os.getenv("OPENAI_REALTIME_MODEL", "gpt-4o-realtime-preview")))
        .replace("__BACKEND_BASE__", json.dumps(API_BASE_URL.rstrip("/")))
        .replace("__QUESTIONS__", json.dumps(st.session_state.get("db_questions", []), ensure_ascii=False))
        .replace("__JOB_ROLE__", json.dumps(st.session_state.get("job_role", "Python 백엔드 개발자"), ensure_ascii=False))
        .replace("__DIFFICULTY__", json.dumps(st.session_state.get("difficulty", "미들"), ensure_ascii=False))
        .replace("__PERSONA__", json.dumps(st.session_state.get("persona_style", "깐깐한 기술팀장"), ensure_ascii=False))
        .replace("__USER_ID__", json.dumps(str(st.session_state.get("user_id", "guest")), ensure_ascii=False))
        .replace("__RESUME_TEXT__", json.dumps(st.session_state.get("resume_text", "") or "", ensure_ascii=False))
        .replace("__FIRST_ASSISTANT__", json.dumps((st.session_state.get("messages") or [{}])[0].get("content", ""), ensure_ascii=False))
        .replace("__CURRENT_Q__", json.dumps(st.session_state.get("pending_question", "면접 질문"), ensure_ascii=False))
        .replace("__Q_IDX__", json.dumps(int(st.session_state.get("current_q_idx", 0))))
        .replace("__FOLLOWUP_COUNT__", json.dumps(int(st.session_state.get("current_followup_count", 0))))
    )
    components.html(html, height=520, scrolling=False)
    st.markdown("<br>", unsafe_allow_html=True)
    webcam_box(height=520)


if st.session_state.db_scores:
    avg = sum(st.session_state.db_scores) / len(st.session_state.db_scores)
    st.caption(f"현재 평균: **{avg:.1f} / 10** ({len(st.session_state.db_scores)}문항)")

st.markdown("<br>", unsafe_allow_html=True)
if st.button("면접 종료 및 평가받기 📊", use_container_width=True):
    st.session_state.interview_ended = True
    st.rerun()