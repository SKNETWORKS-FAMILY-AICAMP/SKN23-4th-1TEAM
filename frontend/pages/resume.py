"""
File: pages/resume.py
Description: 내 이력서 보관함 및 AI 분석 대시보드
"""

import os
import sys
import streamlit as st
from datetime import datetime

# 백엔드 모듈 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(current_dir))
backend_dir = os.path.join(root_dir, "backend")
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

from services.llm_service import analyze_resume_comprehensive
from db.database import init_db, save_user_resume, get_user_resumes, delete_user_resume

st.set_page_config(page_title="내 이력서 보관함", page_icon="📄", layout="wide")

# DB 초기화 시도
try:
    init_db()
except:
    pass

# ============================================================
# 💅 CSS 스타일링
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700;800&display=swap');
html, body, p, div, h1, h2, h3, h4, h5, h6, span, label, li { font-family: 'Pretendard', sans-serif; }
.stApp { background-color: #f8fafc !important; background-image: radial-gradient(at 0% 0%, rgba(243, 232, 255, 0.7) 0px, transparent 40%), radial-gradient(at 100% 100%, rgba(243, 232, 255, 0.7) 0px, transparent 40%); }
.block-container { max-width: 1050px !important; padding-top: 4rem !important; padding-bottom: 5rem !important; }

.hero-title { font-size: 38px; font-weight: 800; color: #0f172a; letter-spacing: -0.5px; margin-bottom: 12px; margin-top: 10px; }
.hero-title span { background: linear-gradient(135deg, #bb38d0, #8b1faa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
.hero-subtitle { font-size: 16px; color: #64748b; margin-bottom: 40px; font-weight: 500; }

/* ─── 내 이력서 리스트 카드 ─── */
.resume-card {
    background: #ffffff; border-radius: 16px; padding: 24px;
    border: 1px solid #e2e8f0; border-left: 5px solid #bb38d0;
    box-shadow: 0 4px 15px rgba(0,0,0,0.03); transition: all 0.2s;
    height: 100%;
}
.resume-card:hover { transform: translateY(-4px); box-shadow: 0 10px 25px rgba(187, 56, 208, 0.1); border-color: #d8b4e2; }
.r-title { font-size: 18px; font-weight: 800; color: #1e293b; margin-bottom: 6px; }
.r-role { display: inline-block; background: #fdf4ff; color: #bb38d0; font-size: 12px; font-weight: 700; padding: 4px 10px; border-radius: 6px; margin-bottom: 12px; }
.r-date { font-size: 13px; color: #94a3b8; margin-bottom: 16px; }

/* ─── 새 이력서 추가 카드 ─── */
.new-resume-card {
    background: transparent; border-radius: 16px; padding: 24px;
    border: 2px dashed #cbd5e1; display: flex; flex-direction: column;
    align-items: center; justify-content: center; height: 100%;
    cursor: pointer; transition: all 0.2s; text-align: center; min-height: 180px;
}
.new-resume-card:hover { border-color: #bb38d0; background: rgba(253, 244, 255, 0.5); }
.new-icon { font-size: 30px; margin-bottom: 10px; }
.new-text { font-size: 16px; font-weight: 700; color: #64748b; }

/* 대시보드 컴포넌트들 */
.premium-card { background: rgba(255, 255, 255, 0.9); backdrop-filter: blur(10px); border-radius: 20px; padding: 30px; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.04); border: 1px solid rgba(255, 255, 255, 0.5); margin-bottom: 24px; }
.card-header { font-size: 20px; font-weight: 800; color: #1e293b; margin-bottom: 24px; display: flex; align-items: center; gap: 10px; }
.badge-container { display: flex; flex-wrap: wrap; gap: 10px; }
.tech-badge { background: linear-gradient(135deg, #ffffff, #fdf4ff); color: #9333ea; padding: 10px 20px; border-radius: 24px; font-size: 14.5px; font-weight: 700; border: 1px solid #f3e8ff; box-shadow: 0 2px 8px rgba(147, 51, 234, 0.05); }
.progress-bg { background-color: #f1f5f9; border-radius: 12px; height: 16px; width: 100%; overflow: hidden; position: relative; margin-top: 10px; }
.progress-fill { background: linear-gradient(90deg, #bb38d0, #8b1faa, #bb38d0); background-size: 200% 200%; animation: gradient-flow 3s ease infinite; height: 100%; border-radius: 12px; }
@keyframes gradient-flow { 0% {background-position: 0% 50%;} 50% {background-position: 100% 50%;} 100% {background-position: 0% 50%;} }
.match-header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 8px; }
.match-score { font-size: 34px; font-weight: 800; color: #bb38d0; line-height: 1; }
.match-feedback { margin-top: 24px; font-size: 15px; color: #475569; line-height: 1.6; background: #f8fafc; padding: 18px 20px; border-radius: 14px; border-left: 5px solid #bb38d0; font-weight: 500; }
.q-box { background: #ffffff; border: 1px solid #e2e8f0; border-radius: 16px; padding: 20px; margin-bottom: 16px; box-shadow: 0 2px 8px rgba(0,0,0,0.02); }
.q-num { display: inline-block; background: linear-gradient(135deg, #bb38d0, #8b1faa); color: white; font-size: 12px; font-weight: 800; padding: 5px 12px; border-radius: 8px; margin-bottom: 12px; }
.q-text { font-size: 16px; color: #1e293b; font-weight: 600; line-height: 1.6; }

[data-testid="stButton"] > button[kind="primary"] { background: linear-gradient(135deg, #bb38d0, #8b1faa) !important; color: white !important; font-weight: 800 !important; font-size: 18px !important; border: none !important; border-radius: 16px !important; height: 58px !important; box-shadow: 0 8px 25px rgba(187, 56, 208, 0.3) !important; transition: all 0.2s; }
[data-testid="stButton"] > button[kind="primary"]:hover { transform: translateY(-3px); box-shadow: 0 12px 30px rgba(187, 56, 208, 0.4) !important; }
[data-testid="stExpander"] { background-color: #ffffff; border-radius: 16px; border: 1px solid #e2e8f0; box-shadow: 0 2px 10px rgba(0,0,0,0.02); }
[data-testid="stExpander"] summary p { font-weight: 700; color: #1e293b; font-size: 15px; }
hr { border-color: #e2e8f0 !important; margin: 2rem 0 !important; border-width: 2px !important; }
</style>
""", unsafe_allow_html=True)

# ============================================================
# 헬퍼 함수
# ============================================================
def extract_resume_text(uploaded_file) -> str:
    try:
        import fitz
        doc = fitz.open(stream=uploaded_file.read(), filetype="pdf")
        return "".join(page.get_text() for page in doc).strip()
    except Exception:
        try:
            return uploaded_file.read().decode("utf-8", errors="ignore")
        except:
            return ""

# 상태 관리
user_id = st.session_state.get("user_id", "demo_user")
if "selected_resume" not in st.session_state:
    st.session_state.selected_resume = None

# ============================================================
# ⚙️ 팝업 모달: 새 이력서 등록
# ============================================================
@st.dialog("🚀 새 이력서 등록 및 AI 분석", width="large")
def setup_modal():
    st.markdown("<p style='color:#64748b; font-size:15px; margin-bottom:20px;'>이력서를 업로드하면 AI가 분석하여 보관함에 영구 저장합니다.</p>", unsafe_allow_html=True)
    
    selected_role = st.selectbox("🎯 이 이력서는 어떤 직무용인가요?", ["Python 백엔드 개발자", "Java 백엔드 개발자", "AI/ML 엔지니어", "데이터 엔지니어", "프론트엔드 개발자"])
    uploaded_file = st.file_uploader("📄 PDF 이력서를 올려주세요", type=["pdf", "txt"])
    
    if st.button("✨ 분석 시작 및 저장", type="primary", use_container_width=True):
        if not uploaded_file:
            st.warning("⚠️ 이력서 파일을 업로드해주세요!")
        else:
            with st.spinner("AI가 이력서를 분석하고 저장 중입니다... (약 10초)"):
                resume_text = extract_resume_text(uploaded_file)
                # AI 분석
                analysis_result = analyze_resume_comprehensive(resume_text, selected_role)
                # DB 저장 (분석 결과 JSON 포함!)
                resume_id = save_user_resume(
                    user_id=user_id, 
                    title=uploaded_file.name, 
                    job_role=selected_role, 
                    resume_text=resume_text, 
                    analysis_result=analysis_result
                )
                st.toast("이력서가 보관함에 저장되었습니다!", icon="🎉")
                st.rerun() # 모달 닫고 리스트 갱신

# ============================================================
# 화면 UI 구현
# ============================================================

# ─── 상태 1: 이력서 보관함 (리스트 뷰) ───
if st.session_state.selected_resume is None:
    st.markdown("<div class='hero-title'>내 이력서 <span>보관함</span></div>", unsafe_allow_html=True)
    st.markdown("<div class='hero-subtitle'>저장된 이력서를 선택하여 AI 딥섹션 결과를 확인하고 모의면접을 시작하세요.</div>", unsafe_allow_html=True)
    
    # DB에서 내 이력서 목록 가져오기
    saved_resumes = get_user_resumes(user_id)
    
    # Grid 레이아웃 (3열)
    cols = st.columns(3, gap="medium")
    
    # [1] 첫 번째 칸: "새 이력서 등록" 버튼 (모달 호출)
    with cols[0]:
        st.markdown("<div class='new-resume-card'>", unsafe_allow_html=True)
        if st.button("➕\n\n새 이력서 분석하기", use_container_width=True, key="btn_new_resume"):
            setup_modal()
        st.markdown("</div>", unsafe_allow_html=True)
        
    # [2] 저장된 이력서들 렌더링
    for i, r in enumerate(saved_resumes):
        col_idx = (i + 1) % 3
        with cols[col_idx]:
            date_str = r['created_at'].strftime("%Y.%m.%d")
            match_rate = r['analysis_result'].get('match_rate', 0) if r['analysis_result'] else 0
            
            st.markdown(f"""
            <div class='resume-card'>
                <div class='r-role'>{r['job_role']}</div>
                <div class='r-title'>{r['title']}</div>
                <div class='r-date'>등록일: {date_str} | 적합도: {match_rate}%</div>
            </div>
            """, unsafe_allow_html=True)
            
            # 카드 아래 액션 버튼들
            c1, c2 = st.columns([3, 1])
            with c1:
                if st.button("👁️ 대시보드 보기", key=f"view_{r['id']}", use_container_width=True):
                    st.session_state.selected_resume = r
                    st.rerun()
            with c2:
                if st.button("🗑️", key=f"del_{r['id']}"):
                    delete_user_resume(r['id'])
                    st.rerun()

# ─── 상태 2: 이력서 상세 대시보드 뷰 ───
else:
    r = st.session_state.selected_resume
    data = r['analysis_result']
    target_role = r['job_role']
    
    # 상단 내비게이션
    col_back, col_title = st.columns([1, 6])
    with col_back:
        if st.button("← 보관함으로", use_container_width=True):
            st.session_state.selected_resume = None
            st.rerun()
            
    st.markdown(f"<div class='hero-title'>AI 이력서 <span>Deep Analysis</span></div>", unsafe_allow_html=True)
    st.markdown(f"<div class='hero-subtitle'><b>{r['title']}</b> ({target_role}) 분석 결과입니다.</div>", unsafe_allow_html=True)
    
    col_l, col_r = st.columns([1, 1.2], gap="large")
    
    # [왼쪽 열] 키워드 & 직무 매칭률
    with col_l:
        keywords = data.get("keywords", [])
        badges_html = "".join([f"<div class='tech-badge'>#{k}</div>" for k in keywords])
        st.markdown(f"<div class='premium-card'><div class='card-header'>🏷️ AI 추출 핵심 기술 스택</div><div class='badge-container'>{badges_html if badges_html else '<div style=\"color:#94a3b8;\">추출된 키워드가 없습니다.</div>'}</div></div>", unsafe_allow_html=True)
        
        match_rate = data.get("match_rate", 0)
        feedback = data.get("match_feedback", "분석 코멘트가 없습니다.")
        st.markdown(f"<div class='premium-card'><div class='card-header'>📈 {target_role} 매칭 적합도</div><div><div class='match-header'><span style='font-size:15px; font-weight:700; color:#64748b;'>종합 매칭 스코어</span><span class='match-score'>{match_rate}%</span></div><div class='progress-bg'><div class='progress-fill' style='width: {match_rate}%;'></div></div></div><div class='match-feedback'><b>💡 AI 코멘트</b><br>{feedback}</div></div>", unsafe_allow_html=True)

    # [오른쪽 열] 예상 압박 질문 & 원본 보기
    with col_r:
        questions = data.get("expected_questions", [])
        q_boxes_html = "".join([f"<div class='q-box'><div class='q-num'>Point {i+1}</div><div class='q-text'>{q}</div></div>" for i, q in enumerate(questions)])
        st.markdown(f"<div class='premium-card' style='border-left: 5px solid #bb38d0;'><div class='card-header'>🎯 면접관의 예상 압박 포인트 TOP 3</div>{q_boxes_html if q_boxes_html else '<div style=\"color:#94a3b8;\">질문을 생성하지 못했습니다.</div>'}</div>", unsafe_allow_html=True)
        
        if st.button("🔥 이 이력서로 모의면접 바로 시작하기", type="primary", use_container_width=True):
            # 면접 페이지에서 사용할 수 있도록 세션 세팅
            st.session_state.job_role = target_role
            st.session_state.resume_text = r['resume_text']
            st.switch_page("pages/interview.py")
            
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("📄 추출된 이력서 텍스트 원본 확인"):
            st.text_area("수정이 불가능한 읽기 전용 텍스트입니다.", r['resume_text'], height=200, disabled=True)