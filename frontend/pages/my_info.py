"""
File: pages/my_info.py
Author: 김지우
Created: 2026-02-24
Description: 마이페이지

Modification History:
- 2026-02-24 (김지우): 초기 틀 생성
- 2026-02-26 (김지우): 전체적인 코드 확인 및 수정 작업
- 2026-02-27 (김지우): 만능 문지기(require_login) 적용 및 로직 최적화 🚀
"""
import streamlit as st
import time
from utils.api_utils import api_update_profile_image, _handle_request
from utils.function import inject_custom_header, require_login

st.set_page_config(page_title="AIWORK", page_icon="👾", layout="centered")

# 1. 헤더 그리기
inject_custom_header()

# 🚨 2. 만능 문지기 출동! (알아서 쿠키 복구하고, 비로그인 유저는 튕겨냄)
user_id = require_login()

# 3. 마음 편하게 DB 데이터 사용 시작!
user = st.session_state.user
user_name = user.get("name", "이름 없음")
user_email = user.get("email", "이메일 정보 없음") 
user_tier = user.get("tier", "normal")
profile_url = user.get("profile_image_url") or "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png"

# ============================================================
# 💅 CSS 스타일링 (탈퇴버튼 등)
# ============================================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700&display=swap');
* { font-family: 'Pretendard', sans-serif; }

/* 배경 및 기본 설정 */
[data-testid="stAppViewContainer"] { background-color: #ffffff !important; }
[data-testid="stHeader"] { display: none; }
.block-container { max-width: 500px !important; padding: 2rem 1rem !important; }

/* 상단 헤더 */
.app-header {
    display: flex; align-items: center; justify-content: center;
    position: relative; margin-bottom: 30px; padding-bottom: 15px;
    border-bottom: 1px solid #f1f3f5;
}
.app-header h3 { margin: 0; font-size: 18px; font-weight: 600; color: #111; }

/* 프로필 사진 영역 */
.profile-section { display: flex; flex-direction: column; align-items: center; margin-bottom: 30px; }
.profile-img-circle {
    width: 100px; height: 100px; border-radius: 50%; object-fit: cover;
    background-color: #f1f3f5; margin-bottom: 16px; border: 1px solid #e9ecef;
}

/* 리스트 뷰 (정보 행) */
.list-row {
    padding: 16px 0; border-bottom: 1px solid #f1f3f5;
    position: relative; display: flex; flex-direction: column; justify-content: center;
}
.list-label { font-size: 12px; color: #888; margin-bottom: 8px; font-weight: 500; }
.list-value { font-size: 16px; color: #111; font-weight: 500; }
.list-arrow { position: absolute; right: 0; top: 50%; transform: translateY(-50%); color: #adb5bd; font-size: 18px; }

/* 하단 탈퇴 버튼을 app.py의 비밀번호 찾기 링크처럼 위장시키는 마법의 CSS */
.withdraw-wrapper div[data-testid="stButton"] button {
    background: transparent !important;
    border: none !important;
    color: #888 !important;
    font-size: 13px !important;
    box-shadow: none !important;
    padding: 0 !important;
    font-weight: 500 !important;
    width: auto !important;
    margin: 0 auto !important;
    display: block !important;
}
.withdraw-wrapper div[data-testid="stButton"] button:hover {
    color: #bb38d0 !important;
    text-decoration: underline !important;
}
</style>
""", unsafe_allow_html=True)


# ============================================================
# 팝업(모달) 로직 정의
# ============================================================
@st.dialog("프로필 사진 올리기")
def upload_photo_dialog():
    uploaded_file = st.file_uploader("이미지 파일 선택", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    
    if uploaded_file:
        st.image(uploaded_file, caption="미리보기", width=150)
        
        if st.button("적용하기", type="primary", use_container_width=True):
            with st.spinner("서버에 사진을 저장하는 중입니다..."):
                is_success, result_url_or_msg = api_update_profile_image(uploaded_file)
                
                if is_success:
                    st.session_state.user["profile_image_url"] = result_url_or_msg
                    
                    st.success("프로필 사진이 변경되었습니다.")
                    time.sleep(1)
                    st.rerun() # 새로고침
                else:
                    st.error(f"실패: {result_url_or_msg}")

@st.dialog("비밀번호 변경")
def change_password_dialog():
    st.markdown("<p style='font-size:13px; color:#555;'>안전을 위해 기존 비밀번호를 먼저 입력해주세요.</p>", unsafe_allow_html=True)
    old_pw = st.text_input("현재 비밀번호", type="password")
    new_pw = st.text_input("새 비밀번호", type="password")
    new_pw_confirm = st.text_input("새 비밀번호 확인", type="password")
    
    if st.button("비밀번호 변경 완료", type="primary", use_container_width=True):
        if not old_pw or not new_pw or not new_pw_confirm:
            st.error("모든 항목을 입력해주세요.")
        elif new_pw != new_pw_confirm:
            st.error("새 비밀번호가 일치하지 않습니다.")
        else:
            with st.spinner("DB 업데이트 중..."):
                # TODO: 백엔드 비밀번호 변경 API 호출 
                time.sleep(1)
                st.success("비밀번호가 안전하게 변경되었습니다!")
                time.sleep(1)
                st.rerun()

@st.dialog("탈퇴 확인")
def withdraw_dialog(email):
    st.markdown(
        f"""
        <div style="text-align:center; padding: 10px 0 20px 0;">
            <div style="font-size: 40px; margin-bottom: 10px;">👾</div>
            <p style="font-size:15px; color:#333; line-height:1.6; margin-bottom:15px;">
                <b>{email}</b> 계정을 정말 탈퇴하시겠습니까?<br>
                <span style="color:#e74c3c; font-size:13px;">등록된 데이터는 접근이 차단되며, 30일 후 파기됩니다.</span>
            </p>
        </div>
        """, 
        unsafe_allow_html=True
    )
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("아니오", use_container_width=True):
            st.rerun() 
    with col2:
        if st.button("예", type="primary", use_container_width=True):
            with st.spinner("탈퇴 처리 중..."):
                _handle_request("POST", "/auth/withdraw", json={"email": email})
                time.sleep(1.5)
                st.session_state.clear() 
                st.switch_page("app.py")


# ==========================================
# 📱 4. UI 렌더링 시작
# ==========================================

# [헤더]
st.markdown("""
<div class="app-header">
    <h3>내 정보 관리</h3>
</div>
""", unsafe_allow_html=True)

# [프로필 사진 영역]
st.markdown(f"""
<div class="profile-section">
    <img src="{profile_url}" class="profile-img-circle">
</div>
""", unsafe_allow_html=True)

# 사진 올리기 버튼 (모달 연결)
col_empty1, col_btn, col_empty2 = st.columns([1, 1, 1])
with col_btn:
    if st.button("📷 사진 올리기", use_container_width=True):
        upload_photo_dialog()

st.markdown("<br>", unsafe_allow_html=True)

# [정보 리스트 영역 - DB 연동]
# 1. 가입된 이메일 (DB값)
st.markdown(f"""
<div class="list-row">
    <div class="list-label">가입된 아이디(이메일)</div>
    <div class="list-value">{user_email}</div>
</div>
""", unsafe_allow_html=True)

# 2. 이름 (DB값)
st.markdown(f"""
<div class="list-row">
    <div class="list-label">이름</div>
    <div class="list-value">{user_name}</div>
</div>
""", unsafe_allow_html=True)

# 3. 나의 등급 (DB값, 영롱한 포인트 색상 적용)
tier_color = "#bb38d0" if user_tier.lower() == "plus" else "#4b5563"
st.markdown(f"""
<div class="list-row">
    <div class="list-label">내 회원 등급</div>
    <div class="list-value" style="color:{tier_color}; font-weight:700;">{user_tier.upper()} 뱃지 보유</div>
</div>
""", unsafe_allow_html=True)

# 4. 비밀번호 (클릭 시 팝업) - 투명 버튼 덮어씌우기 스킬
st.markdown("""
<div class="list-row" style="position:relative;">
    <div class="list-label">비밀번호 변경</div>
    <div class="list-value">********</div>
    <div class="list-arrow">›</div>
</div>
""", unsafe_allow_html=True)
st.markdown('<div style="margin-top:-60px; height:60px; opacity:0; position:relative; z-index:999;">', unsafe_allow_html=True)
if st.button("비밀번호버튼", key="pw_btn", use_container_width=True):
    change_password_dialog()
st.markdown('</div>', unsafe_allow_html=True)

# 🚨 5. 하단 회원 탈퇴 버튼 (app.py 헬퍼 링크 스타일)
st.markdown("<br><br>", unsafe_allow_html=True)
st.markdown('<div class="withdraw-wrapper">', unsafe_allow_html=True)

# 버튼 자체가 투명한 링크처럼 보이도록 CSS(.withdraw-wrapper)가 입혀져 있습니다.
if st.button("회원탈퇴", key="withdraw_link_btn"):
    withdraw_dialog(user_email)
    
st.markdown('</div>', unsafe_allow_html=True)