"""
File: pages/interview.py
Author: 김지우, 김다빈
Created: 2026-02-23
Description: AI 면접 챗봇 (텍스트 + 실시간 음성 모드)
             - 사이드바 유저 ID 설정 (DB 연동용) 추가 완료!
"""
import streamlit as st
import base64
import os
import sys
from dotenv import load_dotenv

import json
import streamlit.components.v1 as components
from utils.webcam_box import webcam_box

# ─── 1. 커스텀 헤더 주입 함수 ───
def get_image_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

def inject_custom_header():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir) 
    image_path = os.path.join(project_root, "data", "AIWORK.jpg")
    
    try:
        img_base64 = get_image_base64(image_path)
        img_src = f"data:image/jpeg;base64,{img_base64}"
    except FileNotFoundError:
        img_src = "" 

    header_html = f"""
    <style>
    .block-container {{ padding-top: 100px !important; }}
    .custom-header {{
        position: fixed; top: 0; left: 0; right: 0; height: 72px;
        background-color: #ffffff; display: flex; align-items: center; justify-content: space-between;
        padding: 0 40px; border-bottom: 1px solid #e2e8f0; z-index: 999999; font-family: 'Pretendard', sans-serif;
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
    """
    st.markdown(header_html, unsafe_allow_html=True)


# ─── 2. 경로 및 모듈 설정 ───
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
backend_dir = os.path.join(root_dir, "backend")
if backend_dir not in sys.path: sys.path.append(backend_dir)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_EXT_PKG_PATH = "/tmp/fw_pkg"
if os.path.isdir(_EXT_PKG_PATH) and _EXT_PKG_PATH not in sys.path: sys.path.insert(0, _EXT_PKG_PATH)

load_dotenv()

from db.database import init_db, create_session, end_session, save_detail, get_questions_by_role, get_common_questions
from services.rag_service import store_resume, clear_resume_for_session
from services.llm_service import get_ai_response, score_answer, generate_evaluation

try:
    from st_realtime_audio import realtime_audio_conversation
    _REALTIME_AVAILABLE = True
except ImportError:
    _REALTIME_AVAILABLE = False


# ─── 3. 페이지 초기화 및 CSS ───
st.set_page_config(page_title="AIWORK", page_icon="👾", layout="centered")
inject_custom_header()

try: init_db()
except Exception as e: st.warning(f"DB 초기화 실패: {e}")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700&display=swap');
* { font-family: 'Pretendard', sans-serif !important; box-sizing: border-box; }
html, body, .stApp { background-color: #f5f5f5 !important; }
[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer { display: none !important; visibility: hidden; }
.block-container { max-width: 720px !important; padding-bottom: 5rem !important; }
.setup-card { background: #fff; border-radius: 20px; box-shadow: 0 4px 24px rgba(0,0,0,0.07); padding: 36px 32px; margin-bottom: 24px; }
.page-title { font-size: 26px; font-weight: 700; color: #bb38d0 !important; text-align: center; margin-bottom: 6px; }
.page-subtitle { font-size: 14px; color: #888 !important; text-align: center; margin-bottom: 0; }
.persona-badge { display: inline-block; background: linear-gradient(135deg, #bb38d0, #7b2cb1); color: white !important; padding: 4px 12px; border-radius: 20px; font-size: 12px; font-weight: 700; margin-left: 8px; box-shadow: 0 2px 8px rgba(187,56,208,0.3); }
.chat-header { display: flex; align-items: center; gap: 12px; background: #fff; border-radius: 14px; box-shadow: 0 1px 8px rgba(0,0,0,0.06); padding: 14px 20px; margin-bottom: 16px; }
.chat-header-icon { width: 44px; height: 44px; border-radius: 12px; background: linear-gradient(135deg, #bb38d0, #7b2cb1); display: flex; align-items: center; justify-content: center; font-size: 20px; flex-shrink: 0; }
.chat-header-name { font-size: 16px; font-weight: 700; color: #333 !important; }
.chat-header-info { font-size: 12px; color: #999 !important; }
.ai-bubble { background: #fff; border: 1px solid #eee; border-radius: 16px; border-top-left-radius: 4px; padding: 14px 18px; max-width: 82%; color: #333 !important; font-size: 15px; line-height: 1.8; margin-bottom: 10px; box-shadow: 0 1px 4px rgba(0,0,0,0.04); white-space: pre-wrap; }
.user-bubble { background: linear-gradient(135deg, #bb38d0, #8b1faa); border-radius: 16px; border-top-right-radius: 4px; padding: 14px 18px; max-width: 82%; color: #fff !important; font-size: 15px; line-height: 1.8; margin-bottom: 10px; box-shadow: 0 2px 10px rgba(187,56,208,0.25); white-space: pre-wrap; }
.sender-label { font-size: 11px; color: #bb38d0 !important; font-weight: 700; margin-bottom: 4px; }
.followup-badge { display: inline-block; background: #fff3e0; color: #e67e22 !important; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 6px; margin-bottom: 6px; }
.score-mini { display: inline-block; background: #f0fdf4; color: #16a34a !important; font-size: 11px; font-weight: 700; padding: 2px 8px; border-radius: 6px; margin-top: 4px; }
[data-testid="stButton"] > button[kind="primary"] { background: linear-gradient(135deg, #bb38d0, #8b1faa) !important; color: #fff !important; border: none !important; border-radius: 10px !important; height: 50px !important; font-size: 16px !important; font-weight: 700 !important; }
[data-testid="stButton"] > button:not([kind="primary"]) { background: #fff !important; color: #555 !important; border: 1px solid #ddd !important; border-radius: 10px !important; font-weight: 600 !important; }
.result-card { background: #fff; border-radius: 16px; box-shadow: 0 4px 20px rgba(0,0,0,0.07); padding: 28px 24px; margin-bottom: 20px; }
.result-title { font-size: 22px; font-weight: 700; color: #bb38d0 !important; text-align: center; margin-bottom: 20px; }
.score-circle { width: 120px; height: 120px; border-radius: 50%; background: linear-gradient(135deg, #bb38d0, #7b2cb1); display: flex; flex-direction: column; align-items: center; justify-content: center; margin: 0 auto 20px auto; box-shadow: 0 4px 20px rgba(187,56,208,0.3); }
.score-number { font-size: 32px; font-weight: 800; color: #fff !important; }
.score-label { font-size: 11px; color: rgba(255,255,255,0.85) !important; font-weight: 600; }
</style>
""", unsafe_allow_html=True)


# ─── 4. 세션 상태 관리 및 사이드바 임시 로그인 ───
defaults = {
    "messages": [], "interview_ended": False, "interview_mode": None, "chatbot_started": False,
    "evaluation_result": None, "resume_text": None, "persona_style": None, "followup_count": 0,
    "db_session_id": None, "turn_index": 0, "pending_question": None, "db_scores": [],
    "current_followup_count": 0, "current_is_followup": False, "db_questions": [], "current_q_idx": 0,
    "user_id": "jiwoo_kim" # 기본값 세팅
}
for k, v in defaults.items():
    if k not in st.session_state: st.session_state[k] = v

# 🔥 DB에 기록할 유저 ID를 사이드바에서 설정
st.sidebar.markdown("### 👤 내 정보 설정")
input_id = st.sidebar.text_input("사용자 ID (이름)", value=st.session_state["user_id"])
if input_id:
    st.session_state["user_id"] = input_id
    st.sidebar.success(f"현재 접속자: {input_id}님 🟢")
else:
    st.sidebar.warning("ID를 입력해주세요!")


# ─── 5. 헬퍼 함수 ───
def extract_resume_text(uploaded_file) -> str:
    try:
        import fitz
        return "".join(page.get_text() for page in fitz.open(stream=uploaded_file.read(), filetype="pdf")).strip()
    except:
        try: return uploaded_file.read().decode("utf-8", errors="ignore")
        except: return ""

def render_message(role: str, content: str, is_followup: bool = False, score: float | None = None):
    if role == "user":
        score_badge = f'<div class="score-mini">✦ {score:.1f}/10</div>' if score is not None else ""
        st.markdown(f'<div style="display:flex;justify-content:flex-end;flex-direction:column;align-items:flex-end;margin-bottom:4px;"><div class="user-bubble">{content}</div>{score_badge}</div>', unsafe_allow_html=True)
    else:
        followup_badge = '<div class="followup-badge">💡 꼬리질문 포함</div>' if is_followup else ""
        st.markdown(f'<div style="display:flex;justify-content:flex-start;margin-bottom:4px;"><div style="display:flex;flex-direction:column;"><div class="sender-label">AI 면접관</div>{followup_badge}<div class="ai-bubble">{content}</div></div></div>', unsafe_allow_html=True)

def save_turn_to_db(question: str, answer: str, is_followup: bool, score: float, feedback: str):
    if not st.session_state.db_session_id: return
    save_detail(st.session_state.db_session_id, st.session_state.turn_index, question, answer, is_followup, score, feedback)
    st.session_state.turn_index += 1


# ─── 6. ⚙️ 면접 설정 화면 ───
if not st.session_state.chatbot_started:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="setup-card"><div class="page-title">🎯 AI 모의면접</div><div class="page-subtitle">실전과 동일한 환경에서 기술 면접을 연습하세요</div></div>', unsafe_allow_html=True)

    mode_options, mode_captions = ["💬 텍스트 면접"], ["타이핑으로 답변합니다."]
    if _REALTIME_AVAILABLE:
        mode_options.append("실시간 음성 면접")
        mode_captions.append("OpenAI Realtime API 기반 실시간 대화")
    mode = st.radio("면접 방식", mode_options, captions=mode_captions, index=0)
    st.markdown("---")
    
    st.markdown("**면접관 스타일**")
    persona_style = st.radio("면접관 스타일", ["깐깐한 기술팀장", "부드러운 인사담당자", "스타트업 CTO"], label_visibility="collapsed")
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1: job_role = st.selectbox("직무 선택", ["Python 백엔드 개발자", "Java 백엔드 개발자", "AI/ML 엔지니어", "데이터 엔지니어", "프론트엔드 개발자", "풀스택 개발자"])
    with col2: difficulty = st.selectbox("난이도 선택", ["주니어", "미들", "시니어"], index=1)
    q_count = st.slider("질문 수", 3, 10, 5)

    st.markdown("---")
    st.markdown("**📄 이력서 업로드 <span style='color:#e53e3e;font-size:13px;'>(필수)</span>**", unsafe_allow_html=True)
    uploaded_resume = st.file_uploader("PDF/TXT 이력서", type=["pdf", "txt"], label_visibility="collapsed")
    if uploaded_resume: st.success(f"'{uploaded_resume.name}' 업로드 완료 ✅")
    else: st.warning("⚠️ 이력서를 업로드해야 면접을 시작할 수 있습니다.")

    st.markdown("<br>", unsafe_allow_html=True)

    col_start, col_back = st.columns([3, 1])
    with col_start:
        if st.button("면접 시작하기 🚀", type="primary", use_container_width=True, disabled=not bool(uploaded_resume)):
            resume_text = extract_resume_text(uploaded_resume) if uploaded_resume else None

            # 🔥 사이드바에서 입력받은 user_id가 여기서 DB로 넘어갑니다!
            try:
                db_session_id = create_session(
                    user_id=st.session_state["user_id"], 
                    job_role=job_role, difficulty=difficulty, persona=persona_style, resume_used=bool(resume_text)
                )
            except Exception as e:
                st.warning(f"DB 연결 실패: {e}")
                db_session_id = None

            if resume_text and db_session_id:
                with st.spinner("이력서 저장 중..."): store_resume(resume_text, user_id=str(db_session_id))


            try:
                common_qs = get_common_questions(limit=1)
                if resume_text:
                    from services.llm_service import extract_keywords_from_resume
                    from db.database import get_questions_by_resume_keywords
                    resume_keywords = extract_keywords_from_resume(resume_text)
                    tech_qs = get_questions_by_resume_keywords(job_role, difficulty, resume_keywords, limit=q_count - 1)
                else:
                    tech_qs = get_questions_by_role(job_role, difficulty, limit=q_count - 1)
                
                db_questions = [q["question"] for q in common_qs] + [q["question"] for q in tech_qs]
                
                # 🔥 핵심 방어 코드: DB 조회는 성공했지만 데이터가 0개인 경우 에러를 발생시켜 기본 질문으로 넘깁니다!
                if not db_questions:
                    raise ValueError("DB에 해당 직무/난이도의 질문 데이터가 없습니다.")
                    
            except Exception as e:
                # 에러가 나거나 데이터가 없을 때 앱이 터지지 않고 기본 질문 생성
                print(f"⚠️ 임시 질문 대체: {e}")
                db_questions = ["간단하게 자기소개를 부탁드립니다."] + [f"{job_role} 관련 핵심 기술을 설명해주세요." for _ in range(q_count - 1)]

            # 세션에 정보 저장
            st.session_state.update({
                "interview_mode": "realtime" if "실시간" in mode else "text", 
                "chatbot_started": True,
                "job_role": job_role, 
                "difficulty": difficulty, 
                "q_count": q_count,
                "persona_style": persona_style, 
                "resume_text": resume_text,
                "db_session_id": db_session_id, 
                "db_questions": db_questions, # 빈 리스트가 들어갈 일이 절대 없어짐!
                "current_q_idx": 0,
            })

            if st.session_state.interview_mode == "text":
                # 이제 무조건 첫 번째 질문이 존재하므로 안심하고 [0]을 씁니다.
                first_q = st.session_state.db_questions[0]
                greeting = f"안녕하세요! 오늘 {job_role} 면접을 진행할 면접관입니다. 총 {q_count}개의 질문을 드리겠습니다.\n\n첫 번째 질문입니다.\n**{first_q}**"
                st.session_state.messages.append({"role": "assistant", "content": greeting})
                st.session_state.pending_question = first_q

            st.rerun()

    with col_back:
        if st.button("홈", use_container_width=True): st.switch_page("app.py")
    st.stop()


# ─── 7. 🏁 면접 종료 및 리포트 ───
if st.session_state.interview_ended:
    st.markdown("<br><div class='result-card'><div class='result-title'>📋 면접 결과 리포트</div></div>", unsafe_allow_html=True)
    scores = st.session_state.db_scores
    total_score = round((sum(scores) / len(scores)) * 10, 1) if scores else 0.0

    st.markdown(f'<div class="score-circle"><span class="score-number">{total_score}</span><span class="score-label">/ 100점</span></div>', unsafe_allow_html=True)

    if st.session_state.db_session_id:
        try:
            end_session(st.session_state.db_session_id, total_score)
            clear_resume_for_session(str(st.session_state.db_session_id))
        except: pass

    if st.session_state.evaluation_result is None:
        with st.spinner("AI가 분석 중입니다..."):
            st.session_state.evaluation_result = generate_evaluation(st.session_state.messages, st.session_state.get("job_role"), st.session_state.get("difficulty"), st.session_state.get("resume_text"))

    st.markdown(st.session_state.evaluation_result)
    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 다시 시작", type="primary", use_container_width=True):
            for k, v in defaults.items(): st.session_state[k] = v
            st.rerun()
    with col2:
        if st.button("내 기록 보러가기 ➔", use_container_width=True):
            st.switch_page("pages/history.py") # '내 기록' 페이지 이름에 맞게 수정하세요
    st.stop()


# ─── 8. 💬 텍스트 면접 진행 화면 ───
if st.session_state.interview_mode == "text":
    st.markdown(f"""
    <div class="chat-header">
        <div class="chat-header-icon">🎯</div>
        <div>
            <div class="chat-header-name">AI 면접관 <span class="persona-badge">{st.session_state.persona_style}</span></div>
            <div class="chat-header-info">{st.session_state.job_role} · {st.session_state.difficulty} · {st.session_state.q_count}문항</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    for message in st.session_state.messages:
        render_message(message["role"], message["content"], is_followup="💡" in message.get("content", ""), score=message.get("score"))

    prompt = st.chat_input("답변을 입력하세요...")
    if prompt:
        prev_question = st.session_state.pending_question or "면접 질문"
        st.session_state.messages.append({"role": "user", "content": prompt, "score": None})

        with st.spinner("답변을 분석하고 꼬리질문을 준비 중입니다..."):
            score, feedback = score_answer(prev_question, prompt, st.session_state.job_role)
            st.session_state.db_scores.append(score)
            st.session_state.messages[-1]["score"] = score
            
            save_turn_to_db(prev_question, prompt, st.session_state.current_is_followup, score, feedback)

            if st.session_state.current_is_followup: st.session_state.current_followup_count += 1
            else: st.session_state.current_followup_count = 0

            db_qs = st.session_state.get("db_questions", [])
            idx = st.session_state.get("current_q_idx", 0)
            next_q = db_qs[idx + 1] if idx + 1 < len(db_qs) else None

            ai_reply = get_ai_response(
                st.session_state.messages, st.session_state.job_role, st.session_state.difficulty, 
                st.session_state.q_count, st.session_state.persona_style, st.session_state.resume_text,
                str(st.session_state.db_session_id), score, st.session_state.current_followup_count, next_q
            )

            if "[INTERVIEW_END]" in ai_reply:
                st.session_state.interview_ended = True
                ai_reply = ai_reply.replace("[INTERVIEW_END]", "").strip()
            if "[NEXT_MAIN]" in ai_reply:
                st.session_state.current_q_idx += 1
                ai_reply = ai_reply.replace("[NEXT_MAIN]", "").strip()

            st.session_state.current_is_followup = "💡 추가 질문:" in ai_reply
            if st.session_state.current_is_followup: st.session_state.followup_count += 1

            st.session_state.messages.append({"role": "assistant", "content": ai_reply})
            st.session_state.pending_question = ai_reply

        st.rerun()

    if st.session_state.db_scores:
        avg = sum(st.session_state.db_scores) / len(st.session_state.db_scores)
        st.caption(f"현재 평균: **{avg:.1f} / 10** ({len(st.session_state.db_scores)}문항)")

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("면접 종료 및 평가받기 📊", use_container_width=True):
        st.session_state.interview_ended = True
        st.rerun()
        
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