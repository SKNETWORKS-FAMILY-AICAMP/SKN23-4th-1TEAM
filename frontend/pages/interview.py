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