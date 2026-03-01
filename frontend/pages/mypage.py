"""
File: pages/mypage.py
Author: 김지우
Created: 2026-02-24
Description: 면접 기록 조회 페이지

Modification History:
- 2026-02-24 (김지우): 초기 틀 생성
- 2026-02-24 (김지우): 세션 클릭 시 질문-답변 상세 + 개별 점수 확인
- 2026-02-28 (김지우): 만능 문지기(require_login) 적용 및 로직 최적화
- 2026-03-01 (김지우): 와이드 레이아웃, 오리지널 카드 디자인 복구, 모달 알림 고도화, 엠프티 스테이트 UI 적용
"""

import os
import sys
import time

current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
backend_dir = os.path.join(root_dir, "backend")

if root_dir not in sys.path:
    sys.path.append(root_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

import streamlit as st
from dotenv import load_dotenv
from utils.api_utils import api_get_interview_sessions, api_get_interview_session_details, api_delete_interview_session
from utils.function import inject_custom_header, require_login

load_dotenv()
# 넓은 화면을 위해 layout="wide"로 설정
st.set_page_config(page_title="AIWORK", page_icon="👾", layout="wide")

user_id = require_login()
inject_custom_header()

# ─── CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap');
* { font-family: 'Pretendard', sans-serif !important; box-sizing: border-box; }

/* 스크롤 완벽 차단 및 화면 고정 */
html, body, [data-testid="stAppViewContainer"], .main {
    overflow: hidden !important; height: 100vh !important; touch-action: none !important;
}
::-webkit-scrollbar { width: 6px; height: 6px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 10px; }
::-webkit-scrollbar-thumb:hover { background: #9ca3af; }

[data-testid="stAppViewContainer"] { background-color: #f5f5f5 !important; }
[data-testid="stHeader"] { display: none; }

/* 전체 폭을 1024px로 확장 */
.block-container { max-width: 1024px !important; padding: 2rem 2rem 4rem !important; margin: 0 auto; }

/* 버튼 통합 디자인 */
button[data-testid="baseButton-primary"] {
    background-color: #bb38d0 !important; border-color: #bb38d0 !important; color: #ffffff !important;
    border-radius: 12px !important; font-weight: 700 !important; padding: 6px 16px !important; 
}
button[data-testid="baseButton-primary"]:hover { 
    background-color: #a028b5 !important; border-color: #a028b5 !important; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(187,56,208,0.2) !important;
}
button[data-testid="baseButton-secondary"] {
    background-color: #ffffff !important; border: 1px solid #bb38d0 !important; color: #bb38d0 !important;
    border-radius: 12px !important; font-weight: 700 !important; padding: 6px 16px !important; 
}
button[data-testid="baseButton-secondary"]:hover { 
    background-color: #fdf4ff !important; transform: translateY(-2px); box-shadow: 0 4px 12px rgba(187,56,208,0.15) !important;
}

/* 커스텀 알림 메시지 디자인 (모달용) */
.status-msg {
    font-size: 14px; text-align: center; margin: 16px 0 0 0; font-weight: 700; 
    padding: 16px 20px; border-radius: 12px; transition: all 0.3s ease;
}
.text-success { color: #bb38d0; background-color: #fdf4ff; border: 1px solid #fae8ff; box-shadow: 0 4px 16px rgba(187,56,208,0.12); }
.text-error   { color: #e74c3c; background-color: #fef2f2; border: 1px solid #fecaca; box-shadow: 0 4px 16px rgba(231,76,60,0.12); }

/* 타이틀 디자인 */
.hero-title { font-size: 38px; font-weight: 800; color: #000; letter-spacing: -0.5px; margin-bottom: 12px; margin-top: 10px; }
.hero-title span { color: #bb38d0; }
.hero-subtitle { font-size: 16px; color: #666; margin-bottom: 30px; font-weight: 500; }

/* 오리지널 예쁜 카드 디자인 복구 마법 */
div[data-testid="stVerticalBlock"]:has(> div:first-child [id^="card-wrap-"]) {
    background-color: #ffffff !important;
    border-radius: 16px !important;
    box-shadow: 0 4px 20px rgba(0,0,0,0.06) !important;
    border-left: 6px solid #bb38d0 !important;
    padding: 20px 24px !important;
    margin-bottom: 14px !important;
}

.score-badge {
    display: inline-flex; align-items: center; justify-content: center; background: #bb38d0; color: #fff !important; 
    font-size: 15px; font-weight: 800; padding: 6px 18px; border-radius: 20px; width: 100%; height: 100%;
}
.no-score { background: #f5f5f5; color: #888 !important; }

/* 엠프티 스테이트 디자인 */
.empty-state-box {
    background-color: #ffffff; border-radius: 20px; box-shadow: 0 4px 20px rgba(0,0,0,0.04);
    padding: 60px 20px; text-align: center; margin-top: 20px;
}
.empty-state-icon {
    font-size: 48px; color: #d1d5db; margin-bottom: 16px;
}
.empty-state-title {
    font-size: 18px; font-weight: 700; color: #374151; margin-bottom: 8px;
}
.empty-state-desc {
    font-size: 14px; color: #9ca3af; margin-bottom: 24px; font-weight: 500;
}

/* 상세 카드 */
.detail-card {
    background: #ffffff; border-radius: 16px; border: none; box-shadow: 0 4px 24px rgba(0,0,0,0.07);
    padding: 20px 24px; margin-bottom: 14px;
}
.q-label { font-size: 12px; font-weight: 700; color: #bb38d0 !important; margin-bottom: 6px; }
.q-text  { font-size: 15px; color: #000 !important; line-height: 1.6; margin-bottom: 12px; }
.a-label { font-size: 12px; font-weight: 700; color: #666 !important; margin-bottom: 6px; }
.a-text  { font-size: 15px; color: #000 !important; line-height: 1.6; margin-bottom: 12px; }
.feedback-box {
    background: #ffffff; border-radius: 16px; border: none; padding: 16px 20px; margin-bottom: 10px; font-size: 14px; color: #000 !important;
    border-left: 4px solid #bb38d0; margin-top: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.06);
}
.followup-tag {
    display: inline-block; background: #fff5e6; color: #d97706 !important; font-size: 12px; font-weight: 700; padding: 4px 10px;
    border-radius: 16px; margin-bottom: 8px;
}
</style>
""", unsafe_allow_html=True)

# ─── 삭제 모달 함수 ────────────────────────────────────
@st.dialog("면접 기록 삭제")
def delete_session_dialog(session_id):
    st.markdown(f"""
    <div style="text-align:center; padding:10px 0 20px;">
        <div style="font-size:48px; margin-bottom:12px;">⚠️</div>
        <p style="font-size:15px; color:#111; line-height:1.6; margin-bottom:0;">
            <b>세션 #{session_id}</b> 기록을 삭제하면 복구할 수 없습니다.<br>정말 삭제하시겠습니까?
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("취소", use_container_width=True, key=f"cancel_btn_{session_id}"):
            st.rerun()
            
    with col2:
        delete_clicked = st.button("삭제", type="primary", use_container_width=True, key=f"confirm_btn_{session_id}")

    msg_ph = st.empty()

    if delete_clicked:
        with st.spinner("안전하게 삭제 처리 중..."):
            ok, msg = api_delete_interview_session(session_id)
            if ok:
                if st.session_state.get("selected_session_id") == session_id:
                    st.session_state.selected_session_id = None
                msg_ph.markdown('''
                <div class="status-msg text-success">
                    <b>삭제 완료!</b> 면접 기록이 깔끔하게 지워졌습니다.
                </div>
                ''', unsafe_allow_html=True)
                time.sleep(1.0) 
                st.rerun()
            else:
                msg_ph.markdown(f'''
                <div class="status-msg text-error">
                    <b>삭제 실패</b><br><span style="font-size:12px; font-weight:500;">{msg}</span>
                </div>
                ''', unsafe_allow_html=True)


st.markdown("<br><br>", unsafe_allow_html=True)

# ─── 타이틀 ───────────────────────────────────────────────────
st.markdown("<div class='hero-title'>내 <span>면접 기록</span></div>", unsafe_allow_html=True)
st.markdown("<div class='hero-subtitle'>지금까지 진행한 모의 면접 결과를 확인하세요.</div>", unsafe_allow_html=True)
st.markdown("<hr style='border:0; height:1px; background:#e5e7eb; margin-bottom:24px;'>", unsafe_allow_html=True)

# ─── 세션 상태 초기화 ─────────────────────────────────────────
if "selected_session_id" not in st.session_state:
    st.session_state.selected_session_id = None

# ─── 세션 목록 조회 ───────────────────────────────────────────
try:
    ok, result = api_get_interview_sessions(user_id)
    if not ok:
        raise RuntimeError(result)
    sessions = result.get("items", [])
except Exception as e:
    st.error(f"DB 연결 오류: {e}")
    st.stop()

# ─── 데이터가 없을 경우 (엠프티 스테이트 렌더링) ─────────────────
if not sessions:
    st.markdown("""
    <div class="empty-state-box">
        <div class="empty-state-icon">👾</div>
        <div class="empty-state-title">아직 면접 기록이 없습니다.</div>
        <div class="empty-state-desc">첫 번째 AI 모의면접을 시작하고 실력을 점검해보세요!</div>
    </div>
    """, unsafe_allow_html=True)
    
    # 예쁜 버튼을 박스 중앙 하단에 배치하기 위해 컬럼 사용
    emp_col1, emp_col2, emp_col3 = st.columns([3, 2, 3])
    with emp_col2:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("새 면접 시작하기", type="primary", use_container_width=True):
            st.switch_page("pages/interview.py")
    st.stop()

# ─── 목록 헤더 ────────────────────────────────────────────────
col_count, col_empty, col_new = st.columns([2, 6, 2])
with col_count:
    st.markdown(f"<div style='font-size:18px; font-weight:800; margin-top:8px;'>총 {len(sessions)}회 면접 기록</div>", unsafe_allow_html=True)
with col_new:
    if st.button("➕ 새 면접 시작", type="primary", use_container_width=True):
        st.switch_page("pages/interview.py")

st.markdown("<br>", unsafe_allow_html=True)

# ─── 세션 카드 목록 ─────────────────────────────────────────
with st.container(height=580, border=False):
    for s in sessions:
        if s["total_score"] is not None:
            raw = float(s["total_score"])
            display_score = raw if raw > 10 else round(raw * 10, 1)
            score_html = f'<div class="score-badge">{display_score:.1f}점 / 100</div>'
        else:
            score_html = '<div class="score-badge no-score">채점 중</div>'

        resume_tag = "· 이력서 사용" if s["resume_used"] else ""
        ended_raw  = s["ended_at"]
        ended = (
            ended_raw[:16].replace("-", ".").replace("T", " ")
            if isinstance(ended_raw, str)
            else (ended_raw.strftime("%Y.%m.%d %H:%M") if ended_raw else "진행 중")
        )

        with st.container(border=False):
            st.markdown(f'<div id="card-wrap-{s["id"]}" style="display:none;"></div>', unsafe_allow_html=True)
            
            c1, c2, c3, c4 = st.columns([5.5, 2, 1.2, 1.2], vertical_alignment="center")
            
            with c1:
                st.markdown(f"""
                <div style="margin-left: 4px;">
                    <div style="font-size: 18px; font-weight: 800; color: #000; margin-bottom: 6px; letter-spacing: -0.3px;">
                        {s['job_role']} <span style="font-size: 14px; color: #a1a1aa; font-weight: 500;">· {s['persona']}</span>
                    </div>
                    <div style="font-size: 13px; color: #71717a; font-weight: 500;">
                        {s['difficulty']} · {ended} · 세션 #{s['id']} {resume_tag}
                    </div>
                </div>
                """, unsafe_allow_html=True)
            
            with c2:
                st.markdown(score_html, unsafe_allow_html=True)
                
            with c3:
                if st.button("상세 보기", key=f"detail_{s['id']}", use_container_width=True):
                    st.session_state.selected_session_id = s["id"]
                    st.rerun()
                    
            with c4:
                if st.button("삭제", key=f"del_modal_btn_{s['id']}", use_container_width=True):
                    delete_session_dialog(s["id"])


# ─── 상세 보기 (하단 렌더링) ──────────────────────────────────────────
if st.session_state.selected_session_id:
    sid = st.session_state.selected_session_id
    st.markdown("<br><hr style='border:0; height:2px; background:#bb38d0; margin-bottom:30px;'>", unsafe_allow_html=True)

    # 상세 헤더
    detail_col1, detail_col2 = st.columns([8, 2])
    with detail_col1:
        st.markdown(f"<h3 style='margin:0;'>세션 #{sid} 상세 기록</h3>", unsafe_allow_html=True)
    with detail_col2:
        if st.button("↑ 목록 닫기", use_container_width=True):
            st.session_state.selected_session_id = None
            st.rerun()

    try:
        ok, result = api_get_interview_session_details(sid)
        if not ok:
            raise RuntimeError(result)
        details = result.get("items", [])
    except Exception as e:
        st.error(f"상세 데이터 로드 실패: {e}")
        st.stop()

    if not details:
        st.info("이 세션에 저장된 상세 기록이 없습니다.")
    else:
        scored = [d for d in details if d["score"] is not None]
        if scored:
            avg_10   = sum(d["score"] for d in scored) / len(scored)
            avg_100  = round(avg_10 * 10, 1)
            high_count = sum(1 for d in scored if d["score"] >= 7)
            low_count  = sum(1 for d in scored if d["score"] < 5)

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("🏆 종합 점수", f"{avg_100:.1f}점")
            col2.metric("📝 총 답변",   f"{len(details)}개")
            col3.metric("✅ 우수 답변", f"{high_count}개")
            col4.metric("⚠️ 보완 필요", f"{low_count}개")

            st.markdown("<br>", unsafe_allow_html=True)

        for d in details:
            followup_tag = '<div class="followup-tag">꼬리질문</div>' if d["is_followup"] else ""
            if d["score"] is not None:
                sc = float(d["score"])
                score_color = "#16a34a" if sc >= 7 else ("#d97706" if sc >= 5 else "#dc2626")
                score_str = f'<span style="color:{score_color}; font-weight:800; font-size:14px; margin-left:8px;">✦ {sc:.1f}/10</span>'
            else:
                score_str = ""
            feedback_html = (
                f'<div class="feedback-box">💡 <b>피드백</b><br><div style="margin-top:6px;">{d["feedback"]}</div></div>'
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

    st.markdown("<br>", unsafe_allow_html=True)
    col_close1, col_close2, col_close3 = st.columns([4, 2, 4])
    with col_close2:
        if st.button("목록 닫기", use_container_width=True, key="back_btn_bottom"):
            st.session_state.selected_session_id = None
            st.rerun()