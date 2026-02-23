"""
File: app.py
Author: 김지우, 양창일
Created: 2026-02-20
Description: 로그인 화면

Modification History:
- 2026-02-20 (김지우): 초기 생성
- 2026-02-21 (양창일): 소셜 로그인 구현
- 2026-02-22 (김지우): utils/api_utils.py 모듈을 적용하여 API 통신 로직 완벽 분리 및 관리자 UX 개선
- 2026-02-23 (양창일): 소셜 로그인 수정, 세션에 사용자이름 추가, profile_image_url 저장
- 2026-02-23 (김지우): 휴면 계정 로그인 시 복구 모달(Popup) 로직 적용
- 2026-02-23 (김지우): 아이디/비밀번호 입력 후 엔터키로 로그인 가능하도록 st.form 적용
- 2026-02-23 (김지우): 휴면 계정 복구 모달(Popup) 로직 수정 
- 2026-02-23 (김지우): 마이페이지 연동을 위해 로그인 성공 시 세션에 email, tier 정보 추가
"""
import streamlit as st
import time
from utils.api_utils import api_login, api_verify_token, api_unlock_dormant
from utils.config import GOOGLE_URI, KAKAO_URI

st.set_page_config(page_title="AIWORK", page_icon="👾", layout="centered")

# 휴면 계정 해제 & 자동 로그인 모달
@st.dialog("🔒 휴면 계정 안내")
def dormant_recovery_modal(email, password):
    st.markdown(
        f"""
        <div style="text-align:center; padding: 10px 0 20px 0;">
            <p style="font-size:15px; color:#333; line-height:1.6; margin-bottom:15px;">
                <b>{email}</b> 계정은<br>장기 미접속으로 인해 현재 <b>휴면 상태</b>로 전환되었습니다.
            </p>
            <p style="font-size:14px; color:#bb38d0; font-weight:600;">
                지금 바로 휴면 상태를 해제하시겠습니까?
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
            with st.spinner("계정 활성화 중..."):
                # 휴면 풀기
                success, msg = api_unlock_dormant(email)
                
                if success:
                    # 비번으로 즉시 자동 로그인
                    is_login_success, login_result = api_login(email, password)
                    
                    if is_login_success:
                        # 토큰 발급받고 세션 세팅
                        st.session_state.new_token = login_result.get("access_token")
                        st.session_state.user = {
                            "name": login_result.get("name"),
                            "role": login_result.get("role"),
                            "profile_image_url": login_result.get("profile_image_url"),
                        }
                        st.switch_page("pages/home.py")
                    else:
                        st.error("자동 로그인에 실패했습니다. 창을 닫고 다시 로그인해주세요.")
                        time.sleep(1.5)
                        st.rerun()
                else:
                    st.error(msg)

# 기존 소셜 로그인 및 세션 로직
if "token" not in st.session_state:
    st.session_state.token = None

social_token = st.query_params.get("access_token")
if social_token:
    st.session_state.token = social_token
    st.session_state.new_token = social_token

    ok, result = api_verify_token(social_token)
    if ok:
        st.session_state.user = {
            "name": result.get("name") or "사용자",
            "role": result.get("role") or "user",
            "profile_image_url": result.get("profile_image_url"),
        }
        st.query_params.clear()
        st.switch_page("pages/home.py")
    else:
        st.session_state.token = None
        st.session_state.user = None
        st.query_params.clear()

if st.query_params.get("logout") == "true":
    st.session_state.clear()
    st.query_params.clear()
    time.sleep(0.1)
    st.rerun()

if "user" not in st.session_state: st.session_state.user = None
if "show_admin_choice" not in st.session_state: st.session_state.show_admin_choice = False

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
* { font-family: 'Noto Sans KR', sans-serif; box-sizing: border-box; }
html, body, [data-testid="stAppViewContainer"] { background-color: #f5f5f5 !important; }
[data-testid="stAppViewContainer"] > .main { background-color: #f5f5f5; }
[data-testid="stHeader"], #MainMenu, footer, header { visibility: hidden; background: transparent; }
[data-testid="stToolbar"] { display: none; }
.block-container { max-width: 460px !important; padding-top: 60px !important; padding-bottom: 60px !important; padding-left: 1rem !important; padding-right: 1rem !important; }
[data-testid="stTextInputRootElement"], [data-testid="stTextInputRootElement"] > div { background-color: #FAFAFA !important; border-color: transparent !important; }
[data-testid="stTextInput"], [data-testid="stTextInput"] > div, [data-testid="stTextInput"] > div > div, [data-testid="stTextInput"] input { width: 100% !important; min-width: 0 !important; }
.login-logo { font-size: 32px; font-weight: 700; color: #bb38d0; letter-spacing: -1px; text-align: center; margin-bottom: 28px; }
.login-logo span { color: #222; }
label[data-testid="stWidgetLabel"] > div > p { font-size: 13px !important; color: #555 !important; font-weight: 500 !important; margin-bottom: 4px !important; }
input[type="text"], input[type="password"] { border-color: transparent !important; border-radius: 6px !important; font-size: 15px !important; padding: 12px 14px !important; background: #fafafa !important; }
input[type="text"]:focus, input[type="password"]:focus { border-color: #bb38d0 !important; background: #fff !important; outline: none !important; box-shadow: 0 0 0 2px rgba(187, 56, 208, 0.12) !important; }
[data-testid="stButton"] > button[kind="primary"], div[data-testid="stButton"]:first-of-type > button, [data-testid="stFormSubmitButton"] > button { background-color: #bb38d0 !important; color: #fff !important; border: none !important; border-radius: 6px !important; height: 50px !important; font-size: 16px !important; font-weight: 700 !important; width: 100% !important; letter-spacing: 0.5px; transition: background 0.15s; margin-top: 6px; }
div[data-testid="stButton"]:first-of-type > button:hover, [data-testid="stFormSubmitButton"] > button:hover { background-color: #872a96 !important; }
.divider-row { display: flex; align-items: center; margin: 24px 0 20px; color: #bbb; font-size: 13px; gap: 10px; }
.divider-row::before, .divider-row::after { content: ''; flex: 1; border-top: 1px solid #eee; }
.social-btns { display: flex; flex-direction: column; gap: 10px; margin-bottom: 20px; }
.social-btn { display: flex; align-items: center; justify-content: center; gap: 10px; border: none; border-radius: 6px; height: 48px; font-size: 15px; font-weight: 600; cursor: pointer; text-decoration: none !important; color: inherit !important; transition: filter 0.15s, box-shadow 0.15s; width: 100%; }
.btn-google { background: #fff; color: #3c4043; border: 1.5px solid #ddd !important; }
.btn-kakao { background: #FEE500; color: #3c1e1e; }
.helper-links { display: flex; justify-content: center; gap: 16px; font-size: 13px; color: #888; margin-top: 18px; }
.helper-links a { color: #888; text-decoration: none; font-weight: 500; }
.helper-links a:hover{ color: #bb38d0 !important; text-decoration: underline; transition: all 300ms; }
.helper-sep { color: #ddd; }
[data-testid="stButton"] > button { border-radius: 6px !important; }
[data-testid="stForm"] { border: none !important; padding: 0 !important; background: transparent !important; box-shadow: none !important; }
.custom-error-msg { font-size: 13px; color: #e74c3c; text-align: center; margin-top: 10px; font-weight: 500; }
.custom-success-box { background-color: rgba(187, 56, 208, 0.08); color: #bb38d0; border: 1px solid rgba(187, 56, 208, 0.2); padding: 14px; border-radius: 8px; text-align: center; font-size: 14px; font-weight: 600; margin-bottom: 16px; }
</style>
""", unsafe_allow_html=True)

st.markdown('<br>', unsafe_allow_html=True)
st.markdown('<div class="login-logo">AI<span>WORK</span></div>', unsafe_allow_html=True)

# 일반 로그인 폼
if not st.session_state.get("show_admin_choice"):
    with st.form("login_form"):
        username = st.text_input("아이디", placeholder="이메일을 입력하세요")
        password = st.text_input("비밀번호", type="password", placeholder="비밀번호를 입력하세요")
        submitted = st.form_submit_button("로그인", use_container_width=True)

    msg_placeholder = st.empty()

    if submitted:
        if not username or not password:
            msg_placeholder.markdown('<div class="custom-error-msg">아이디와 비밀번호를 모두 입력해주세요.</div>', unsafe_allow_html=True)
        elif username == "admin" and password == "1234":
            st.session_state.new_token = "admin_token"
            st.session_state.user = {"name": username, "role": "admin"}
            st.session_state.show_admin_choice = True
            st.rerun()
        else:
            with st.spinner("로그인 중..."):
                is_success, result = api_login(username, password)
                
                if is_success:
                    st.session_state.new_token = result.get("access_token")
                    st.session_state.user = {
                        "name": result.get("name"),
                        "role": result.get("role"),
                        "profile_image_url": result.get("profile_image_url"),
                        "email": result.get("email"), 
                        "tier": result.get("tier")    
                    }
                    
                    if result.get("role") == "admin":
                        st.session_state.show_admin_choice = True
                        st.rerun()
                    else:
                        st.switch_page("pages/home.py")
                else:
                    if "휴면" in result:
                        dormant_recovery_modal(username, password)
                    elif "탈퇴" in result:
                        msg_placeholder.markdown(f'<div class="custom-error-msg" style="color:red; font-size:14px; font-weight:bold;">{result}</div>', unsafe_allow_html=True)
                    else:
                        msg_placeholder.markdown(f'<div class="custom-error-msg">{result}</div>', unsafe_allow_html=True)

    # 하단 헬퍼 링크 및 소셜 로그인 버튼
    st.markdown(f"""
    <div class="helper-links"><a href="find_pw" target="_self">비밀번호 찾기</a><span class="helper-sep">|</span><a href="sign_up" target="_self">회원가입</a></div>
    <div class="divider-row">소셜 계정으로 로그인</div>
    <div class="social-btns">
        <a href="{GOOGLE_URI}" class="social-btn btn-google" target="_self"><svg width="20" height="20" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.54 0 6.71 1.22 9.21 3.6l6.85-6.85C35.9 2.38 30.47 0 24 0 14.62 0 6.51 5.38 2.56 13.22l7.98 6.19C12.43 13.72 17.74 9.5 24 9.5z"/><path fill="#4285F4" d="M46.98 24.55c0-1.57-.15-3.09-.38-4.55H24v9.02h12.94c-.58 2.96-2.26 5.48-4.78 7.18l7.73 6c4.51-4.18 7.09-10.36 7.09-17.65z"/><path fill="#FBBC05" d="M10.53 28.59c-.48-1.45-.76-2.99-.76-4.59s.27-3.14.76-4.59l-7.98-6.19C.92 16.46 0 20.12 0 24c0 3.88.92 7.54 2.56 10.78l7.97-6.19z"/><path fill="#34A853" d="M24 48c6.48 0 11.93-2.13 15.89-5.81l-7.73-6c-2.18 1.48-4.97 2.31-8.16 2.31-6.26 0-11.57-4.22-13.47-9.91l-7.98 6.19C6.51 42.62 14.62 48 24 48z"/></svg>Google로 계속하기</a><br>
        <a href="{KAKAO_URI}" class="social-btn btn-kakao" target="_self"><svg width="20" height="20" viewBox="0 0 24 24"><path fill="#3c1e1e" d="M12 3C6.477 3 2 6.477 2 10.5c0 2.611 1.563 4.911 3.938 6.258L4.5 21l4.688-2.344A11.3 11.3 0 0012 18c5.523 0 10-3.477 10-7.5S17.523 3 12 3z"/></svg>카카오로 계속하기</a>
    </div>
    """, unsafe_allow_html=True)

# 관리자 전용 선택지 모달
else:
    st.markdown('<div class="custom-success-box">관리자 권한 인증 완료!<br>이동할 페이지를 선택하세요.</div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("기존 홈 화면", use_container_width=True):
            st.session_state.show_admin_choice = False
            st.switch_page("pages/home.py")
    with col2:
        if st.button("관리자 페이지", use_container_width=True, type="primary"):
            st.session_state.show_admin_choice = False
            st.switch_page("pages/admin.py")
            
    st.markdown("""
    <div class="helper-links" style="margin-top: 24px;">
        <a href="/?logout=true" target="_self">로그아웃</a>
    </div>
    """, unsafe_allow_html=True)
            
    st.stop()