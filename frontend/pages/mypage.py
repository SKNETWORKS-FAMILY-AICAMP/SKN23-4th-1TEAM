"""
File: pages/mypage.py
Description: 면접 기록 조회 페이지
             - 세션 목록 (최신순)
             - 세션 클릭 시 질문-답변 상세 + 개별 점수 확인
"""

import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
backend_dir = os.path.join(root_dir, "backend")

# sys.path에 경로 강제 주입 (tavily_service 등 백엔드 모듈 접근용)
if root_dir not in sys.path:
    sys.path.append(root_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

import streamlit as st
from dotenv import load_dotenv
from db.database import init_db, get_sessions_by_user, get_details_by_session
from utils.function import inject_custom_header, require_login

load_dotenv()
st.set_page_config(page_title="AIWORK", page_icon="👾", layout="centered")

# 1. 헤더 그리기
inject_custom_header()

# 🚨 2. 만능 문지기 출동! (알아서 쿠키 복구하고, 비로그인 유저는 튕겨냄)
user_id = require_login()

try:
    init_db()
except Exception:
    pass


# ============================================================
# 💅 CSS 스타일링
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700&display=swap');
* { font-family: 'Pretendard', sans-serif !important; box-sizing: border-box; }
html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main { background-color: #f5f5f5 !important; }
[data-testid="stHeader"] { background: transparent !important; }
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }
.block-container { max-width: 760px !important; padding-top: 1.5rem !important; padding-bottom: 4rem !important; }
h1, h2, h3, p, div, span, label { color: #333 !important; }

.hero-title { font-size: 38px; font-weight: 800; color: #0f172a; letter-spacing: -0.5px; margin-bottom: 12px; margin-top: 10px; }
.hero-title span { background: linear-gradient(135deg, #bb38d0, #8b1faa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.hero-subtitle { font-size: 16px; color: #64748b; margin-bottom: 40px; font-weight: 500; }

.page-title { font-size: 38px; font-weight: 800; color: #0f172a; letter-spacing: -0.5px; margin-bottom: 12px; margin-top: 10px; }
.page-titlespan { background: linear-gradient(135deg, #bb38d0, #8b1faa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.page-subtitle { font-size: 16px; color: #64748b; margin-bottom: 40px; font-weight: 500; }
.page-sub   { font-size: 13px; color: #888 !important; margin-bottom: 24px; }

/* ─── 세션 카드 ─── */
.session-card {
    background: #fff; border-radius: 14px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    padding: 18px 22px; margin-bottom: 12px;
    border-left: 4px solid #bb38d0;
}
.session-title { font-size: 15px; font-weight: 700; color: #333 !important; }
.session-meta  { font-size: 12px; color: #999 !important; margin-top: 2px; }
.score-badge {
    display: inline-block;
    background: linear-gradient(135deg, #bb38d0, #7b2cb1);
    color: #fff !important; font-size: 13px; font-weight: 700;
    padding: 3px 12px; border-radius: 20px;
}
.no-score { background: #eee; color: #aaa !important; }

/* ─── 상세 카드 ─── */
.detail-card {
    background: #fff; border-radius: 12px;
    box-shadow: 0 1px 8px rgba(0,0,0,0.05);
    padding: 16px 20px; margin-bottom: 10px;
}
.q-label { font-size: 11px; font-weight: 700; color: #bb38d0 !important; margin-bottom: 4px; }
.q-text  { font-size: 14px; color: #333 !important; line-height: 1.6; margin-bottom: 10px; }
.a-label { font-size: 11px; font-weight: 700; color: #555 !important; margin-bottom: 4px; }
.a-text  { font-size: 14px; color: #444 !important; line-height: 1.6; margin-bottom: 10px; }
.feedback-box {
    background: #f9f0ff; border-radius: 8px;
    padding: 8px 12px; font-size: 13px; color: #7b2cb1 !important;
    border-left: 3px solid #bb38d0; margin-top: 6px;
}
.followup-tag {
    display: inline-block; background: #fff3e0; color: #e67e22 !important;
    font-size: 11px; font-weight: 700; padding: 2px 8px;
    border-radius: 6px; margin-bottom: 6px;
}

[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #bb38d0, #8b1faa) !important;
    color: #fff !important; border: none !important;
    border-radius: 10px !important; font-weight: 700 !important;
}
[data-testid="stButton"] > button:not([kind="primary"]) {
    background: #fff !important; color: #555 !important;
    border: 1px solid #ddd !important; border-radius: 10px !important;
    font-weight: 600 !important;
}
hr { border-color: #eee !important; }
</style>
""", unsafe_allow_html=True)


st.markdown("<br><br><br>", unsafe_allow_html=True)

# ─── 타이틀 ───────────────────────────────────────────────────
st.markdown("<div class='hero-title'>내 <span>면접 기록</span></div>", unsafe_allow_html=True)
st.markdown("<div class='hero-subtitle'>지금까지 진행한 모의 면접 결과를 확인하세요.</div>", unsafe_allow_html=True)

st.markdown("---")

# ─── 세션 목록 조회 ───────────────────────────────────────────
try:
    # 🔥 방금 문지기한테 받은 진짜 user_id (정수) 로 DB를 조회합니다!
    sessions = get_sessions_by_user(user_id)
except Exception as e:
    st.error(f"DB 연결 오류: {e}")
    st.stop()

if not sessions:
    st.info("아직 면접 기록이 없습니다. AI 모의면접을 시작해보세요! 🚀")
    if st.button("면접 시작하기", type="primary"):
        st.switch_page("pages/interview.py")
    st.stop()

# ─── 세션 선택 (상세 보기용) ──────────────────────────────────
if "selected_session_id" not in st.session_state:
    st.session_state.selected_session_id = None

st.markdown(f"**총 {len(sessions)}회** 면접 기록")
st.markdown("<br>", unsafe_allow_html=True)

for s in sessions:
    # total_score는 interview.py에서 avg*10 하여 100점 만점으로 저장됨
    if s["total_score"] is not None:
        raw = float(s["total_score"])
        # 0~10 스케일로 저장된 경우(구버전)를 100점으로 환산
        display_score = raw if raw > 10 else round(raw * 10, 1)
        score_html = f'<span class="score-badge">{display_score:.1f}점 / 100</span>'
    else:
        score_html = '<span class="score-badge no-score">채점 중</span>'
    resume_tag = "이력서 사용" if s["resume_used"] else ""
    ended = s["ended_at"].strftime("%Y.%m.%d %H:%M") if s["ended_at"] else "진행 중"

    st.markdown(f"""
    <div class="session-card">
        <div style="display:flex;justify-content:space-between;align-items:center;">
            <div>
                <div class="session-title">{s['job_role']}
                    <span style="font-size:12px;color:#bbb;font-weight:400;">· {s['persona']}</span>
                </div>
                <div class="session-meta">
                    {s['difficulty']} · {ended} · 세션 #{s['id']} {resume_tag}
                </div>
            </div>
            <div>{score_html}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if st.button(f"상세 보기 →", key=f"detail_{s['id']}"):
        st.session_state.selected_session_id = s["id"]
        st.rerun()

# ─── 상세 보기 ────────────────────────────────────────────────
if st.session_state.selected_session_id:
    sid = st.session_state.selected_session_id
    st.markdown("---")
    st.markdown(f"### 세션 #{sid} 상세 기록")

    try:
        details = get_details_by_session(sid)
    except Exception as e:
        st.error(f"상세 데이터 로드 실패: {e}")
        st.stop()

    if not details:
        st.info("이 세션에 저장된 상세 기록이 없습니다.")
    else:
        # 점수 요약
        scored = [d for d in details if d["score"] is not None]
        if scored:
            # 개별 score는 0~10 스케일 (score_answer 반환값)
            avg_10 = sum(d["score"] for d in scored) / len(scored)
            avg_100 = round(avg_10 * 10, 1)  # 100점 만점으로 환산
            high_count = sum(1 for d in scored if d["score"] >= 7)  # 7점 이상 = 양호
            low_count  = sum(1 for d in scored if d["score"] < 5)   # 5점 미만 = 미흡

            col1, col2, col3 = st.columns(3)
            col1.metric("종합 점수 (100점)", f"{avg_100:.1f}점")
            col2.metric("총 답변 수",        f"{len(details)}개")
            col3.metric("꼬리질문 수",       f"{sum(1 for d in details if d['is_followup'])}개")

            # 점수 분포 정보
            st.markdown(
                f"<div style='font-size:12px;color:#888;margin:4px 0 12px;'>"
                f"✅ 양호(7점↑) {high_count}개 &nbsp;|&nbsp; "
                f"⚠️ 미흡(5점↓) {low_count}개 &nbsp;|&nbsp; "
                f"개별점수 기준: 0~10점"
                f"</div>",
                unsafe_allow_html=True
            )
            st.markdown("<br>", unsafe_allow_html=True)

        for d in details:
            followup_tag = '<div class="followup-tag">꼬리질문</div>' if d["is_followup"] else ""
            # 개별 점수: 0~10 스케일 그대로 표시
            if d["score"] is not None:
                sc = float(d["score"])
                if sc >= 7:
                    score_color = "#16a34a"  # 초록
                elif sc >= 5:
                    score_color = "#d97706"  # 주황
                else:
                    score_color = "#dc2626"  # 빨강
                score_str = f'<span style="color:{score_color};font-weight:700;">✦ {sc:.1f}/10</span>'
            else:
                score_str = ""
            feedback_html = (
                f'<div class="feedback-box">💬 {d["feedback"]}</div>'
                if d.get("feedback") else ""
            )

            st.markdown(f"""
            <div class="detail-card">
                {followup_tag}
                <div class="q-label">Q{d['turn_index'] + 1}. 면접관 질문 {score_str}</div>
                <div class="q-text">{d['question'] or '(질문 없음)'}</div>
                <div class="a-label">지원자 답변</div>
                <div class="a-text">{d['answer'] or '(답변 없음)'}</div>
                {feedback_html}
            </div>
            """, unsafe_allow_html=True)

    if st.button("목록으로 돌아가기"):
        st.session_state.selected_session_id = None
        st.rerun()