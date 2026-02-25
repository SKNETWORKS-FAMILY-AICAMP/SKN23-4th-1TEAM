"""
File: pages/interview.py
Author: 김지우, 김다빈
Created: 2026-02-23
Description: AI 면접 챗봇 (텍스트 + 실시간 음성 모드)
             - ChromaDB RAG 기반 이력서 맞춤 꼬리질문
             - MySQL 세션/상세 기록 자동 저장
             - question_pool DB에서 직무별 메인 질문 가져오기
             - 답변별 점수 자동 채점 및 저장
"""

import os
import sys

# 프로젝트 루트(SKN23-3rd-1TEAM) 기준으로 backend 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
backend_dir = os.path.join(root_dir, "backend")
if backend_dir not in sys.path:
    sys.path.append(backend_dir)
# 기존 상대경로 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_EXT_PKG_PATH = "/tmp/fw_pkg"
if os.path.isdir(_EXT_PKG_PATH) and _EXT_PKG_PATH not in sys.path:
    sys.path.insert(0, _EXT_PKG_PATH)

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

# ─── 내부 모듈 ────────────────────────────────────────────────
from db.database import (
    init_db, create_session, end_session,
    save_detail, get_questions_by_role, get_common_questions,
)
from services.rag_service import store_resume, clear_resume_for_session
from services.llm_service import get_ai_response, score_answer, generate_evaluation

# ─── Realtime Audio (선택) ────────────────────────────────────
try:
    from st_realtime_audio import realtime_audio_conversation
    _REALTIME_AVAILABLE = True
except ImportError:
    _REALTIME_AVAILABLE = False

# ─── 페이지 설정 ──────────────────────────────────────────────
st.set_page_config(page_title="AIWORK", page_icon="👾", layout="centered")

# DB 초기화 (최초 1회)
try:
    init_db()
except Exception as e:
    st.warning(f"DB 초기화 실패 (MySQL 연결을 확인하세요): {e}")

# ============================================================
# CSS
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700&display=swap');
* { font-family: 'Pretendard', sans-serif !important; box-sizing: border-box; }

html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main {
    background-color: #f5f5f5 !important;
}
[data-testid="stHeader"] { background: transparent !important; }
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

.block-container {
    max-width: 720px !important;
    padding-top: 1.5rem !important;
    padding-bottom: 5rem !important;
}
h1, h2, h3, p, div, span, label { color: #333 !important; }

/* ─── 설정 카드 ─── */
.setup-card {
    background: #fff;
    border-radius: 20px;
    box-shadow: 0 4px 24px rgba(0,0,0,0.07);
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

/* ─── 페르소나 배지 ─── */
.persona-badge {
    display: inline-block;
    background: linear-gradient(135deg, #bb38d0, #7b2cb1);
    color: white !important; padding: 4px 12px; border-radius: 20px;
    font-size: 12px; font-weight: 700; margin-left: 8px;
    box-shadow: 0 2px 8px rgba(187,56,208,0.3);
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
    width: 44px; height: 44px; border-radius: 12px;
    background: linear-gradient(135deg, #bb38d0, #7b2cb1);
    display: flex; align-items: center; justify-content: center;
    font-size: 20px; flex-shrink: 0;
}
.chat-header-name { font-size: 16px; font-weight: 700; color: #333 !important; }
.chat-header-info { font-size: 12px; color: #999 !important; }

/* ─── 메시지 버블 ─── */
.ai-bubble {
    background: #fff;
    border: 1px solid #eee;
    border-radius: 16px; border-top-left-radius: 4px;
    padding: 14px 18px;
    max-width: 82%;
    color: #333 !important;
    font-size: 15px; line-height: 1.8;
    margin-bottom: 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    white-space: pre-wrap;
}
.user-bubble {
    background: linear-gradient(135deg, #bb38d0, #8b1faa);
    border-radius: 16px; border-top-right-radius: 4px;
    padding: 14px 18px;
    max-width: 82%;
    color: #fff !important;
    font-size: 15px; line-height: 1.8;
    margin-bottom: 10px;
    box-shadow: 0 2px 10px rgba(187,56,208,0.25);
    white-space: pre-wrap;
}
.sender-label {
    font-size: 11px; color: #bb38d0 !important;
    font-weight: 700; margin-bottom: 4px;
}

/* ─── 꼬리질문 배지 ─── */
.followup-badge {
    display: inline-block; background: #fff3e0; color: #e67e22 !important;
    font-size: 11px; font-weight: 700; padding: 2px 8px;
    border-radius: 6px; margin-bottom: 6px;
}

/* ─── 점수 미니 배지 ─── */
.score-mini {
    display: inline-block; background: #f0fdf4; color: #16a34a !important;
    font-size: 11px; font-weight: 700; padding: 2px 8px;
    border-radius: 6px; margin-top: 4px;
}

/* ─── 버튼 ─── */
[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #bb38d0, #8b1faa) !important;
    color: #fff !important; border: none !important;
    border-radius: 10px !important; height: 50px !important;
    font-size: 16px !important; font-weight: 700 !important;
}
[data-testid="stButton"] > button:not([kind="primary"]) {
    background: #fff !important; color: #555 !important;
    border: 1px solid #ddd !important; border-radius: 10px !important;
    font-weight: 600 !important;
}

/* ─── 결과 리포트 ─── */
.result-card {
    background: #fff; border-radius: 16px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.07);
    padding: 28px 24px; margin-bottom: 20px;
}
.result-title {
    font-size: 22px; font-weight: 700;
    color: #bb38d0 !important; text-align: center; margin-bottom: 20px;
}
.score-circle {
    width: 120px; height: 120px; border-radius: 50%;
    background: linear-gradient(135deg, #bb38d0, #7b2cb1);
    display: flex; flex-direction: column;
    align-items: center; justify-content: center;
    margin: 0 auto 20px auto;
    box-shadow: 0 4px 20px rgba(187,56,208,0.3);
}
.score-number { font-size: 32px; font-weight: 800; color: #fff !important; }
.score-label  { font-size: 11px; color: rgba(255,255,255,0.85) !important; font-weight: 600; }

hr { border-color: #eee !important; }

/* ─── 실시간 음성 ─── */
.realtime-guide {
    background: #fff; border: 1px solid #eee; border-radius: 12px;
    padding: 16px 20px; margin-bottom: 12px; font-size: 14px;
    color: #555; line-height: 1.6;
}
.realtime-guide strong { color: #bb38d0 !important; }
.realtime-status {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 8px 20px; border-radius: 24px;
    font-weight: 600; font-size: 14px; margin: 8px 0 16px 0;
}
.status-idle      { background: #f3f4f6; color: #6b7280; }
.status-connected { background: #f0fdf4; color: #16a34a; }
.status-recording { background: #fdf4ff; color: #bb38d0; }
.status-speaking  { background: #eff6ff; color: #2563eb; }
.pulse-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: currentColor; animation: pulse 1.2s infinite; display: inline-block;
}
@keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
</style>
""", unsafe_allow_html=True)

# ============================================================
# Session State 초기화
# ============================================================
defaults = {
    "messages":          [],       # 채팅 히스토리
    "interview_ended":   False,
    "interview_mode":    None,     # "text" | "realtime"
    "chatbot_started":   False,
    "evaluation_result": None,
    "resume_text":       None,
    "persona_style":     None,
    "followup_count":    0,
    "db_session_id":     None,     # MySQL interview_sessions.id
    "turn_index":        0,        # 현재 턴 번호
    "pending_question":  None,     # 직전 AI 질문 (채점용)
    "db_scores":         [],       # 각 답변 점수 리스트
    "user_id":           "demo_user",  # 실제 서비스: st.session_state.user["id"]
    "current_followup_count": 0,   # 현재 문항에 대한 꼬리질문 누적 횟수
    "current_is_followup": False,  # 가장 최근 한 질문이 꼬리질문이었는가 여부
    "db_questions":      [],       # DB에서 뽑아온 메인 질문 리스트
    "current_q_idx":     0,        # 현재 진행 중인 DB 질문 인덱스
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
        pdf_bytes = uploaded_file.read()
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        return "".join(page.get_text() for page in doc).strip()
    except ImportError:
        try:
            return uploaded_file.read().decode("utf-8", errors="ignore")
        except Exception:
            return ""
    except Exception:
        return ""


def render_message(role: str, content: str,
                   is_followup: bool = False,
                   score: float | None = None):
    """메시지 버블 렌더링 (꼬리질문 배지 + 점수 배지 포함)"""
    if role == "user":
        score_badge = f'<div class="score-mini">✦ {score:.1f}/10</div>' if score is not None else ""
        st.markdown(
            f'<div style="display:flex;justify-content:flex-end;flex-direction:column;align-items:flex-end;margin-bottom:4px;">'
            f'<div class="user-bubble">{content}</div>'
            f'{score_badge}'
            f'</div>',
            unsafe_allow_html=True,
        )
    else:
        followup_badge = '<div class="followup-badge">💡 꼬리질문 포함</div>' if is_followup else ""
        st.markdown(
            f'<div style="display:flex;justify-content:flex-start;margin-bottom:4px;">'
            f'<div style="display:flex;flex-direction:column;">'
            f'<div class="sender-label">AI 면접관</div>'
            f'{followup_badge}'
            f'<div class="ai-bubble">{content}</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )


def save_turn_to_db(question: str, answer: str, is_followup: bool, score: float, feedback: str):
    """
    미리 채점된 결과를 바탕으로 DB(interview_details)에 턴 정보를 저장합니다.
    """
    if not st.session_state.db_session_id:
        return

    save_detail(
        session_id=st.session_state.db_session_id,
        turn_index=st.session_state.turn_index,
        question=question,
        answer=answer,
        is_followup=is_followup,
        score=score,
        feedback=feedback,
    )

    st.session_state.turn_index += 1


# ============================================================
# ⚙️ 설정 화면
# ============================================================
if not st.session_state.chatbot_started:
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown("""
    <div class="setup-card">
        <div class="page-title">🎯 AI 모의면접</div>
        <div class="page-subtitle">실전과 동일한 환경에서 기술 면접을 연습하세요</div>
    </div>
    """, unsafe_allow_html=True)

    # 면접 방식 선택
    mode_options  = ["💬 텍스트 면접"]
    mode_captions = ["타이핑으로 답변합니다."]
    if _REALTIME_AVAILABLE:
        mode_options.append("실시간 음성 면접")
        mode_captions.append("OpenAI Realtime API 기반 실시간 음성 대화")
    else:
        mode_options.append("음성 면접")
        mode_captions.append("pip install streamlit-realtime-audio 필요")

    mode = st.radio("면접 방식", mode_options, captions=mode_captions, index=0)

    st.markdown("---")

    # 페르소나 선택
    st.markdown("**면접관 스타일 (페르소나)**")
    persona_style = st.radio(
        "면접관 스타일",
        ["깐깐한 기술팀장", "부드러운 인사담당자", "스타트업 CTO"],
        captions=[
            "기술적 모순을 날카롭게 파고드는 압박 스타일",
            "동기·경험·성장을 공감하며 파고드는 인성 스타일",
            "비즈니스 임팩트와 결과물을 중시하는 실용 스타일",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        job_role = st.selectbox("직무 선택", [
            "Python 백엔드 개발자",
            "Java 백엔드 개발자",
            "AI/ML 엔지니어",
            "데이터 엔지니어",
            "프론트엔드 개발자",
            "풀스택 개발자",
        ])
    with col2:
        difficulty = st.selectbox("난이도 선택", ["주니어", "미들", "시니어"], index=1)

    q_count = st.slider("질문 수", 3, 10, 5)

    # 이력서 업로드
    st.markdown("---")
    st.markdown("**📄 이력서 업로드 <span style='color:#e53e3e;font-size:13px;'>(필수)</span>**", unsafe_allow_html=True)
    st.caption("면접을 시작하려면 이력서(PDF/TXT)를 먼저 업로드해야 합니다. AI가 이력서를 분석해 맞춤 꼬리질문을 생성합니다.")
    uploaded_resume = st.file_uploader(
        "PDF/TXT 이력서 업로드",
        type=["pdf", "txt"],
        label_visibility="collapsed",
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

    col_start, col_back = st.columns([3, 1])
    with col_start:
        if st.button("면접 시작하기 🚀", type="primary", use_container_width=True,
                     disabled=not bool(uploaded_resume)):
            resume_text = None
            if uploaded_resume:
                with st.spinner("🔍 이력서 텍스트 추출 중..."):
                    resume_text = extract_resume_text(uploaded_resume)

            # MySQL 세션 생성
            try:
                db_session_id = create_session(
                    user_id=st.session_state.user_id,
                    job_role=job_role,
                    difficulty=difficulty,
                    persona=persona_style,
                    resume_used=bool(resume_text),
                )
            except Exception as e:
                st.warning(f"DB 세션 생성 실패 (기록은 저장되지 않습니다): {e}")
                db_session_id = None

            if resume_text and db_session_id:
                with st.spinner("🔍 이력서 분석 중 (ChromaDB 저장)..."):
                    chunk_count = store_resume(
                        resume_text,
                        user_id=str(db_session_id),
                    )
                    st.toast(f"이력서 {chunk_count}개 청크로 분할 저장 완료!", icon="📄")

            # 🔥 DB에서 메인 질문 리스트 가져오기 (이력서 맞춤 검색 융합!)
            try:
                common_qs = get_common_questions(limit=1)
                
                # 이력서가 있다면 키워드 추출 후 맞춤 DB 검색, 없으면 일반 검색
                if resume_text:
                    from services.llm_service import extract_keywords_from_resume
                    from db.database import get_questions_by_resume_keywords
                    
                    with st.spinner("🧠 이력서를 분석하여 맞춤형 질문을 DB에서 찾고 있습니다..."):
                        resume_keywords = extract_keywords_from_resume(resume_text)
                        tech_qs = get_questions_by_resume_keywords(job_role, difficulty, resume_keywords, limit=q_count - 1)
                else:
                    tech_qs = get_questions_by_role(job_role, difficulty, limit=q_count - 1)
                
                common_q_list = [q["question"] for q in common_qs] if common_qs else ["간단하게 자기소개를 부탁드립니다."]
                db_questions = common_q_list + [q["question"] for q in tech_qs]
                
                # 에러 감지: 빈 리스트가 나왔다는 건 DB 마이그레이션이 안 되었다는 뜻!
                if not tech_qs:
                    raise ValueError("DB에 'Python 백엔드 개발자' 질문이 존재하지 않습니다. 마이그레이션을 확인하세요!")
                    
            except Exception as e:
                st.error(f"⚠️ DB 오류 (임시 질문으로 대체됩니다): {e}")
                db_questions = ["간단하게 자기소개를 부탁드립니다."] + [f"{job_role} 관련 기술을 설명해주세요." for _ in range(q_count - 1)]

            st.session_state.update({
                "interview_mode":   "realtime" if is_realtime else "text",
                "chatbot_started":  True,
                "job_role":         job_role,
                "difficulty":       difficulty,
                "q_count":          q_count,
                "persona_style":    persona_style,
                "resume_text":      resume_text,
                "db_session_id":    db_session_id,
                "db_questions":     db_questions,
                "current_q_idx":    0,
            })

            if not is_realtime:
                # 시작하자마자 첫 질문 던지기
                first_q = st.session_state.db_questions[0]
                greeting = (
                    f"안녕하세요, 반갑습니다! "
                    f"저는 오늘 {job_role} 포지션 면접을 진행하게 된 AI 면접관입니다. "
                    f"총 {q_count}개의 질문으로 진행할 예정이니 편하게 답변해 주세요.\n\n"
                    f"첫 번째 질문입니다.\n**{first_q}**"
                )
                st.session_state.messages.append({"role": "assistant", "content": greeting})
                st.session_state.pending_question = first_q

            st.rerun()
    with col_back:
        if st.button("← 홈", use_container_width=True):
            st.switch_page("app.py")

    st.stop()


# ============================================================
# 🏁 면접 종료 — 리포트 + DB 저장
# ============================================================
if st.session_state.interview_ended:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("""
    <div class="result-card">
        <div class="result-title">📋 면접 결과 리포트</div>
    </div>
    """, unsafe_allow_html=True)

    # 총점 계산
    scores = st.session_state.db_scores
    total_score = round((sum(scores) / len(scores)) * 10, 1) if scores else 0.0

    st.markdown(f"""
    <div class="score-circle">
        <span class="score-number">{total_score}</span>
        <span class="score-label">/ 100점</span>
    </div>
    """, unsafe_allow_html=True)

    # DB 저장 및 ChromaDB 정리
    if st.session_state.db_session_id:
        try:
            end_session(st.session_state.db_session_id, total_score)
            st.caption(f"✅ 면접 기록 저장 완료 (세션 ID: {st.session_state.db_session_id})")
            clear_resume_for_session(str(st.session_state.db_session_id))
        except Exception as e:
            st.warning(f"DB 저장 실패: {e}")

    # 리포트 생성
    if st.session_state.evaluation_result is None:
        with st.spinner("🧠AI가 면접 전체를 분석하고 있습니다..."):
            st.session_state.evaluation_result = generate_evaluation(
                st.session_state.messages,
                st.session_state.get("job_role", "개발자"),
                st.session_state.get("difficulty", "미들"),
                st.session_state.get("resume_text"),
            )

    st.markdown(st.session_state.evaluation_result)
    st.markdown("<br>", unsafe_allow_html=True)

    script_text = "\n".join([
        f"[{'면접관' if m['role'] == 'assistant' else '지원자'}] {m['content']}"
        for m in st.session_state.messages
    ])

    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button("📥 대화록 다운로드", script_text.encode("utf-8"), file_name="interview_script.txt", mime="text/plain", use_container_width=True)
    with col2:
        if st.session_state.evaluation_result:
            st.download_button("📊 리포트 다운로드", st.session_state.evaluation_result.encode("utf-8"), file_name="interview_report.md", mime="text/markdown", use_container_width=True)
    with col3:
        if st.button("🔄 다시 시작", type="primary", use_container_width=True):
            for k, v in defaults.items():
                st.session_state[k] = v
            st.rerun()
    st.stop()


# ============================================================
# 🎙️ 실시간 음성 모드
# ============================================================
if st.session_state.interview_mode == "realtime":
    # 실시간 모드는 기존 로직 유지
    job_role      = st.session_state.get("job_role",      "Python 백엔드 개발자")
    difficulty    = st.session_state.get("difficulty",    "미들")
    q_count       = st.session_state.get("q_count",       5)
    persona_style = st.session_state.get("persona_style", "깐깐한 기술팀장")

    st.markdown(f"""
    <div class="chat-header">
        <div class="chat-header-icon">🎙️</div>
        <div>
            <div class="chat-header-name">AI 면접관 · 실시간 음성
                <span class="persona-badge">{persona_style}</span>
            </div>
            <div class="chat-header-info">{job_role} · {difficulty} · {q_count}문항</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="realtime-guide">
        <strong>사용 방법</strong><br> 아래 <strong>Start</strong> 버튼을 누르면 연결됩니다.<br> 마이크가 활성화되면 자유롭게 말씀하세요.
    </div>
    """, unsafe_allow_html=True)

    persona_desc_map = {
        "깐깐한 기술팀장": "10년 경력의 깐깐한 기술팀장처럼 기술적 모순을 날카롭게 파고드세요.",
        "부드러운 인사담당자": "HR 매니저처럼 공감하되 동기와 경험을 깊게 파고드세요.",
        "스타트업 CTO": "스타트업 CTO처럼 비즈니스 임팩트와 결과를 중시하세요.",
    }
    instructions = (
        f"{persona_desc_map.get(persona_style, '')} "
        f"한국어로 {job_role} 기술 면접을 진행하세요. 난이도: {difficulty}. 총 {q_count}개 질문. "
        f"핵심 질문하나 할때마다 점수가 4점 이하 일때, 꼬리질문 필수 최대 2개. 자기소개부터 시작 → 꼬리질문 선택 → {q_count}개 완료 후 종합평가."
    )

    result = realtime_audio_conversation(api_key=os.getenv("OPENAI_API_KEY", ""), instructions=instructions, voice="echo", temperature=0.7, turn_detection_threshold=0.5, auto_start=False, key="interview_realtime")

    status = result.get("status", "idle") if result else "idle"
    status_map = {"idle": ("대기 중", "status-idle"), "connecting": ("연결 중...", "status-idle"), "connected": ("연결 완료", "status-connected"), "recording": ("듣는 중...", "status-recording"), "speaking": ("면접관이 말하는 중", "status-speaking")}
    label, css = status_map.get(status, ("알 수 없음", "status-idle"))
    st.markdown(f'<div class="realtime-status {css}"><span class="pulse-dot"></span> {label}</div>', unsafe_allow_html=True)

    transcript = result.get("transcript", []) if result else []
    if transcript:
        st.markdown("---")
        st.markdown("**대화 기록**")
        for msg in transcript:
            role    = "assistant" if msg.get("type") == "assistant" else "user"
            content = msg.get("content", "")
            if content:
                render_message(role, content, is_followup="💡" in content)

    st.markdown("---")
    col1, col2 = st.columns(2)
    with col1:
        if st.button("면접 종료하기", use_container_width=True):
            st.session_state.interview_ended = True
            st.session_state.messages = [{"role": "assistant" if m.get("type") == "assistant" else "user", "content": m.get("content", "")} for m in transcript if m.get("content")]
            st.rerun()
    with col2:
        if transcript:
            script = "\n".join([f"[{'AI 면접관' if m.get('type') == 'assistant' else '지원자'}] {m.get('content', '')}" for m in transcript if m.get("content")])
            st.download_button("스크립트 다운로드", script.encode("utf-8"), file_name="interview_realtime.txt", mime="text/plain", use_container_width=True)
    st.stop()


# ============================================================
# 💬 텍스트 면접 모드
# ============================================================
job_role      = st.session_state.get("job_role",      "Python 백엔드 개발자")
difficulty    = st.session_state.get("difficulty",    "미들")
q_count       = st.session_state.get("q_count",       5)
persona_style = st.session_state.get("persona_style", "깐깐한 기술팀장")
resume_text   = st.session_state.get("resume_text",   None)
user_id       = st.session_state.get("user_id",       "demo_user")

# 채팅 헤더
st.markdown(f"""
<div class="chat-header">
    <div class="chat-header-icon">🎯</div>
    <div>
        <div class="chat-header-name">AI 면접관
            <span class="persona-badge">{persona_style}</span>
        </div>
        <div class="chat-header-info">
            {job_role} · {difficulty} · {q_count}문항
            {'· 📄 이력서 RAG 활성' if resume_text else ''}
            {'· 💾 DB 연결됨' if st.session_state.db_session_id else ''}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# 메시지 렌더링
for i, message in enumerate(st.session_state.messages):
    is_followup = "💡 추가 질문:" in message.get("content", "")
    score = message.get("score")
    render_message(message["role"], message["content"], is_followup=is_followup, score=score)

# 사용자 입력
prompt = st.chat_input("답변을 입력하세요...")

if prompt:
    prev_question = st.session_state.pending_question or "면접 질문"
    st.session_state.messages.append({"role": "user", "content": prompt, "score": None})

    with st.spinner("면접관이 꼬리질문을 준비하고 있습니다..."):
        # 1. 지원자 답변 채점
        score, feedback = score_answer(prev_question, prompt, job_role)
        st.session_state.db_scores.append(score)
        st.session_state.messages[-1]["score"] = score
        
        # 2. DB 저장 (사용자 답변)
        save_turn_to_db(prev_question, prompt, st.session_state.current_is_followup, score, feedback)

        # 3. 꼬리질문 카운터 관리
        if st.session_state.current_is_followup:
            st.session_state.current_followup_count += 1
        else:
            st.session_state.current_followup_count = 0

        # 🔥 4. 다음 메인 질문 준비
        db_questions = st.session_state.get("db_questions", [])
        curr_idx = st.session_state.get("current_q_idx", 0)
        
        next_q = None
        if curr_idx + 1 < len(db_questions):
            next_q = db_questions[curr_idx + 1]

        # 5. AI 응답 생성 (next_main_question 전달)
        ai_reply = get_ai_response(
            messages=st.session_state.messages,
            job_role=job_role, difficulty=difficulty, q_count=q_count,
            persona_style=persona_style, resume_text=resume_text,
            user_id=str(st.session_state.db_session_id) if st.session_state.db_session_id else "anonymous",
            latest_score=score,
            followup_count=st.session_state.current_followup_count,
            next_main_question=next_q  # 🔥 핵심! AI에게 DB 다음 질문을 넘겨줌
        )

        # 6. 종료 / 다음 질문 태그 처리
        if "[INTERVIEW_END]" in ai_reply:
            st.session_state.interview_ended = True
            ai_reply = ai_reply.replace("[INTERVIEW_END]", "").strip()

        if "[NEXT_MAIN]" in ai_reply:
            st.session_state.current_q_idx += 1  # DB 질문 인덱스 이동
            ai_reply = ai_reply.replace("[NEXT_MAIN]", "").strip()

        # 7. 꼬리질문 여부 체크
        if "💡 추가 질문:" in ai_reply:
            st.session_state.followup_count += 1
            st.session_state.current_is_followup = True
        else:
            st.session_state.current_is_followup = False

        # 8. AI 메시지 추가
        st.session_state.messages.append({"role": "assistant", "content": ai_reply})
        st.session_state.pending_question = ai_reply

    st.rerun()

# 진행 상황 표시
if st.session_state.db_scores:
    avg = sum(st.session_state.db_scores) / len(st.session_state.db_scores)
    st.caption(f"현재 평균 점수: **{avg:.1f} / 10** ({len(st.session_state.db_scores)}개 답변 채점 완료)")

# 종료 버튼
st.markdown("<br>", unsafe_allow_html=True)
col_end, col_home = st.columns([3, 1])
with col_end:
    if st.button("면접 종료 및 리포트 받기 📊", use_container_width=True):
        st.session_state.interview_ended = True
        st.rerun()
with col_home:
    if st.button("← 홈", use_container_width=True):
        for k, v in defaults.items():
            st.session_state[k] = v
        st.switch_page("app.py")