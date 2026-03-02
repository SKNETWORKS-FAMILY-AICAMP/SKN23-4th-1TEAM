"""
File: pages/resume.py
Description: 내 이력서 보관함 및 AI 분석 대시보드
"""

import os
import sys
import time
import streamlit as st
from datetime import datetime

# 백엔드 모듈 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
backend_dir = os.path.join(root_dir, "backend")
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from utils.api_utils import api_create_resume, api_list_resumes, api_delete_resume
from utils.function import inject_custom_header, require_login

st.set_page_config(page_title="AIWORK", page_icon="👾", layout="centered")

user_id = require_login()
inject_custom_header()


# CSS 스타일링
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700;800&display=swap');
:root { color-scheme: light !important; }
html, body, .stApp, p, div, h1, h2, h3, h4, h5, h6, span, label, li, a, td, th, small, strong, b, i, em { font-family: 'Pretendard', sans-serif; color: #111 !important; color-scheme: light !important; }
* { color: #111 !important; }
.stApp { background-color: #f5f5f5 !important; background-image: none !important; }
[data-testid="stAppViewContainer"], [data-testid="stAppViewContainer"] > .main { background-color: #f5f5f5 !important; color-scheme: light !important; }
[data-testid="stHeader"], [data-testid="stToolbar"], footer { visibility: hidden; color-scheme: light !important; }

/* === Streamlit 내부 컴포넌트 다크모드 차단 === */
[data-testid="stVerticalBlock"], [data-testid="stHorizontalBlock"],
[data-testid="stColumn"], [data-testid="stForm"],
[data-testid="stMarkdownContainer"] { color: #111 !important; }
[data-testid="stDialog"] > div > div,
[data-testid="stDialog"] [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stDialog"] [data-testid="stVerticalBlock"],
section[data-testid="stDialog"] { background-color: #ffffff !important; color: #111 !important; }
[data-baseweb="input"], [data-baseweb="input"] > div,
[data-baseweb="select"], [data-baseweb="select"] > div,
[data-baseweb="textarea"],
[data-baseweb="popover"] > div,
[data-baseweb="menu"], [data-baseweb="menu"] li { background-color: #ffffff !important; color: #111 !important; }
/* === 모든 Streamlit 버튼 배경 강제 === */
[data-testid="stButton"] > button, [data-testid="stLinkButton"] > a,
[data-testid="stFormSubmitButton"] > button { background-color: #ffffff !important; color: #111 !important; border: 1px solid #ddd !important; }
[data-testid="stButton"] > button p, [data-testid="stLinkButton"] > a p { color: #111 !important; }
button[kind="primary"], [data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #bb38d0 0%, #872a96 100%) !important; border: none !important; color: white !important;
}
button[kind="primary"] p, button[kind="primary"] span { color: #fff !important; }
[data-testid="stDataFrame"], [data-testid="stDataFrame"] > div, [data-testid="stDataFrame"] iframe,
[data-testid="stTable"], [data-testid="stTable"] table, [data-testid="stTable"] th,
[data-testid="stTable"] td { background-color: #ffffff !important; color: #111 !important; }
[data-testid="stVerticalBlockBorderWrapper"] > div { background-color: transparent !important; }
.block-container { max-width: 1050px !important; padding-top: 4rem !important; padding-bottom: 5rem !important; }

.hero-title { font-size: 38px; font-weight: 800; color: #000; letter-spacing: -0.5px; margin-bottom: 12px; margin-top: 10px; }
.hero-title span { color: #bb38d0; }
.hero-subtitle { font-size: 16px; color: #666; margin-bottom: 40px; font-weight: 500; }

/* ─── 내 이력서 리스트 카드 ─── */
.resume-card {
    background: #ffffff; border-radius: 16px; padding: 24px;
    border: none; border-left: 5px solid #bb38d0;
    box-shadow: 0 4px 24px rgba(0,0,0,0.07); transition: all 0.2s;
    height: 100%; display: flex; flex-direction: column; justify-content: space-between;
}
.resume-card:hover { transform: translateY(-4px); box-shadow: 0 8px 30px rgba(0, 0, 0, 0.1); border-color: #d8b4e2; }
.r-title { font-size: 18px; font-weight: 800; color: #000; margin-bottom: 6px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.r-role { display: inline-block; background: #fdf4ff; color: #bb38d0; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 16px; margin-bottom: 12px; }
.r-date { font-size: 13px; color: #666; margin-bottom: 16px; }

/* ─── 새 이력서 추가 카드 ─── */
.new-resume-card {
    background: transparent; border-radius: 16px; padding: 24px;
    border: 2px dashed #bb38d0; display: flex; flex-direction: column;
    align-items: center; justify-content: center; height: 100%; min-height: 200px;
    cursor: pointer; transition: all 0.2s; text-align: center;
}
.new-resume-card:hover { border-color: #872a96; background: rgba(253, 244, 255, 0.5); }
.new-icon { font-size: 30px; margin-bottom: 10px; }
.new-text { font-size: 16px; font-weight: 700; color: #666; }

/* 대시보드 컴포넌트들 */
.premium-card { background: #ffffff; border-radius: 16px; padding: 30px; box-shadow: 0 4px 24px rgba(0, 0, 0, 0.07); border: none; margin-bottom: 24px; }
.card-header { font-size: 20px; font-weight: 800; color: #000; margin-bottom: 24px; display: flex; align-items: center; gap: 10px; }
.badge-container { display: flex; flex-wrap: wrap; gap: 10px; }
.tech-badge { background: #f5f5f5; color: #000; padding: 10px 20px; border-radius: 16px; font-size: 14.5px; font-weight: 700; border: none; }
.progress-bg { background-color: #f5f5f5; border-radius: 16px; height: 16px; width: 100%; overflow: hidden; position: relative; margin-top: 10px; }
.progress-fill { background: #bb38d0; height: 100%; border-radius: 16px; transition: width 1s ease-in-out; }
.match-header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 8px; }
.match-score { font-size: 34px; font-weight: 800; color: #bb38d0; line-height: 1; }
.match-feedback { margin-top: 24px; font-size: 15px; color: #666; line-height: 1.6; background: #ffffff; padding: 18px 20px; border-radius: 16px; border-left: 5px solid #bb38d0; font-weight: 500; box-shadow: 0 4px 24px rgba(0, 0, 0, 0.07); }
.q-box { background: #ffffff; border: none; border-radius: 16px; padding: 20px; margin-bottom: 16px; box-shadow: 0 4px 24px rgba(0, 0, 0, 0.07); }
.q-num { display: inline-block; background: #bb38d0; color: white; font-size: 12px; font-weight: 800; padding: 5px 12px; border-radius: 16px; margin-bottom: 12px; }
.q-text { font-size: 16px; color: #000; font-weight: 600; line-height: 1.6; }

[data-testid="stButton"] > button[kind="primary"] { background: #bb38d0 !important; color: white !important; font-weight: 800 !important; font-size: 18px !important; border: none !important; border-radius: 16px !important; height: 58px !important; transition: all 0.2s; }
[data-testid="stButton"] > button[kind="primary"]:hover { transform: translateY(-3px); box-shadow: 0 4px 24px rgba(0, 0, 0, 0.07) !important; }
[data-testid="stExpander"] { background-color: #ffffff; border-radius: 16px; border: none; box-shadow: 0 4px 24px rgba(0,0,0,0.07); }
[data-testid="stExpander"] summary p { font-weight: 700; color: #000; font-size: 15px; }
hr { border-color: #e2e8f0 !important; margin: 2rem 0 !important; border-width: 2px !important; }

/* 휴지통 버튼 투명화 */
.delete-btn-wrapper button { background: transparent !important; border: none !important; box-shadow: none !important; padding: 0 !important; font-size: 18px !important; }
.delete-btn-wrapper button:hover { transform: scale(1.1); color: #ef4444 !important; }
@media (max-width: 768px) {
    .block-container { padding-top: 2rem !important; padding-bottom: 3rem !important; }
    .hero-title { font-size: 28px; }
    .resume-card { padding: 18px; }
    .premium-card { padding: 20px; }
}
</style>
""",
    unsafe_allow_html=True,
)


# ─── 헬퍼 함수 ───
def extract_resume_text(uploaded_file) -> str:
    file_bytes = uploaded_file.getvalue()  # read() 대신 getvalue() 사용 권장
    try:
        import fitz

        doc = fitz.open(stream=file_bytes, filetype="pdf")
        return "".join(page.get_text() for page in doc).strip()
    except Exception:
        try:
            return file_bytes.decode("utf-8", errors="ignore").strip()
        except:
            return ""


# 상태 관리
if "selected_resume" not in st.session_state:
    st.session_state.selected_resume = None


# 팝업 모달: 새 이력서 등록
@st.dialog("새 이력서 등록 및 AI 분석", width="large")
def setup_modal():
    st.markdown(
        "<p style='color:#64748b; font-size:15px; margin-bottom:20px;'>이력서를 업로드하면 AI가 분석하여 보관함에 영구 저장합니다.</p>",
        unsafe_allow_html=True,
    )

    selected_role = st.selectbox(
        "이 이력서는 어떤 직무용인가요?",
        [
            "Python 백엔드 개발자",
            "Java 백엔드 개발자",
            "AI/ML 엔지니어",
            "데이터 엔지니어",
            "프론트엔드 개발자",
        ],
    )

    with st.form("resume_upload_form"):
        uploaded_file = st.file_uploader("PDF 이력서를 올려주세요", type=["pdf", "txt"])
        submit_btn = st.form_submit_button(
            "분석하기", type="primary", use_container_width=True
        )

        if submit_btn:
            if not uploaded_file:
                st.warning("이력서 파일을 업로드해주세요!")
            else:
                with st.spinner("이력서 분석중입니다..."):
                    resume_text = extract_resume_text(uploaded_file)

                    if not resume_text:
                        st.error(
                            "이력서에서 텍스트를 추출할 수 없습니다. 정상적인 PDF/TXT 파일인지 확인해주세요."
                        )
                        time.sleep(2)
                        st.rerun()

                    ok, result = api_create_resume(
                        user_id=user_id,
                        title=uploaded_file.name,
                        job_role=selected_role,
                        resume_text=resume_text,
                    )
                    if not ok:
                        st.error(result)
                        time.sleep(2)
                        st.rerun()

                    st.success("분석 완료! 이력서가 보관함에 안전하게 저장되었습니다.")
                    time.sleep(1.5)
                    st.rerun()


# 화면 UI 구현
# ─── 상태 1: 이력서 보관함 (리스트 뷰) ───
if st.session_state.selected_resume is None:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(
        "<div class='hero-title'>내 이력서 <span>보관함</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div class='hero-subtitle'>저장된 이력서를 선택하여 AI 딥섹션 결과를 확인하고 모의면접을 시작하세요.</div>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    # API에서 내 이력서 목록 가져오기
    ok, result = api_list_resumes(user_id)
    if not ok:
        st.error(result)
        st.stop()
    saved_resumes = result.get("items", [])

    cols = st.columns(3, gap="medium")

    # [1] 첫 번째 칸: "새 이력서 등록" 버튼 (모달 호출)
    with cols[0]:
        st.markdown("<div class='new-resume-card'>", unsafe_allow_html=True)
        if st.button("＋이력서 추가", use_container_width=True, key="btn_new_resume"):
            setup_modal()
        st.markdown("</div>", unsafe_allow_html=True)

    # [2] 저장된 이력서들 렌더링 (col_idx를 1부터 시작하여 밀림 방지)
    for i, r in enumerate(saved_resumes):
        col_idx = (i + 1) % 3
        with cols[col_idx]:
            created_at = r["created_at"]
            date_str = (
                created_at[:10].replace("-", ".")
                if isinstance(created_at, str)
                else created_at.strftime("%Y.%m.%d")
            )
            match_rate = (
                r["analysis_result"].get("match_rate", 0) if r["analysis_result"] else 0
            )

            # 카드 HTML 컨테이너
            st.markdown(
                f"""
            <div class='resume-card'>
                <div>
                    <div class='r-role'>{r['job_role']}</div>
                    <div class='r-title' title='{r['title']}'>{r['title']}</div>
                    <div class='r-date'>등록일: {date_str} &nbsp;|&nbsp; 적합도: <b>{match_rate}%</b></div>
                </div>
            </div>
            """,
                unsafe_allow_html=True,
            )

            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown("<div style='margin-top:-60px;'>", unsafe_allow_html=True)
                if st.button(
                    "대시보드", key=f"view_{r['id']}", use_container_width=True
                ):
                    st.session_state.selected_resume = r
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)
            with c2:
                st.markdown(
                    "<div class='delete-btn-wrapper' style='margin-top:-60px;'>",
                    unsafe_allow_html=True,
                )
                if st.button("삭제", key=f"del_{r['id']}", help="이력서 삭제"):
                    api_delete_resume(r["id"])
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)


# ─── 상태 2: 이력서 상세 대시보드 뷰 ───
else:
    r = st.session_state.selected_resume
    data = r.get("analysis_result", {})
    target_role = r.get("job_role", "직무 미상")

    st.markdown("<br><br>", unsafe_allow_html=True)

    # 상단 내비게이션 (뒤로 가기)
    col_back, col_title = st.columns([1, 6])
    with col_back:
        if st.button("보관함으로", use_container_width=True):
            st.session_state.selected_resume = None
            st.rerun()

    st.markdown(
        f"<div class='hero-title'>AI 이력서 <span>Deep Analysis</span></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div class='hero-subtitle'><b>{r['title']}</b> ({target_role}) 분석 결과입니다.</div>",
        unsafe_allow_html=True,
    )
    st.markdown("---")

    col_l, col_r = st.columns([1, 1.2], gap="large")

    # [왼쪽 열] 키워드 & 직무 매칭률
    with col_l:
        keywords = data.get("keywords", [])
        badges_html = "".join([f"<div class='tech-badge'>#{k}</div>" for k in keywords])
        no_keywords_html = "<div style='color:#94a3b8;'>추출된 키워드가 없습니다.</div>"
        st.markdown(
            f"<div class='premium-card'><div class='card-header'>AI 추출 핵심 기술 스택</div><div class='badge-container'>{badges_html if badges_html else no_keywords_html}</div></div>",
            unsafe_allow_html=True,
        )

        match_rate = data.get("match_rate", 0)
        feedback = data.get("match_feedback", "분석 코멘트가 없습니다.")
        st.markdown(
            f"<div class='premium-card'><div class='card-header'>📈 {target_role} 매칭 적합도</div><div><div class='match-header'><span style='font-size:15px; font-weight:700; color:#64748b;'>종합 매칭 스코어</span><span class='match-score'>{match_rate}%</span></div><div class='progress-bg'><div class='progress-fill' style='width: {match_rate}%;'></div></div></div><div class='match-feedback'><b>💡 AI 코멘트</b><br>{feedback}</div></div>",
            unsafe_allow_html=True,
        )

    # [오른쪽 열] 예상 압박 질문 & 원본 보기
    with col_r:
        questions = data.get("expected_questions", [])
        q_boxes_html = "".join(
            [
                f"<div class='q-box'><div class='q-num'>Point {i+1}</div><div class='q-text'>{q}</div></div>"
                for i, q in enumerate(questions)
            ]
        )
        no_questions_html = (
            "<div style='color:#94a3b8;'>질문을 생성하지 못했습니다.</div>"
        )

        st.markdown(
            f"<div class='premium-card' style='border-left: 5px solid #bb38d0;'><div class='card-header'>면접관의 예상 압박 포인트 TOP</div>{q_boxes_html if q_boxes_html else no_questions_html}</div>",
            unsafe_allow_html=True,
        )

        if st.button(
            "이 이력서로 모의면접 바로 시작하기",
            type="primary",
            use_container_width=True,
        ):
            # 면접 페이지에서 사용할 수 있도록 세션 세팅
            st.session_state.job_role = target_role
            st.session_state.resume_text = r["resume_text"]
            st.session_state.resume_id = r["id"]
            st.session_state.resume_title = r["title"]
            st.switch_page("pages/interview.py")

        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("추출된 이력서 텍스트 원본 확인"):
            st.text_area(
                "수정이 불가능한 읽기 전용 텍스트입니다.",
                r["resume_text"],
                height=200,
                disabled=True,
            )
