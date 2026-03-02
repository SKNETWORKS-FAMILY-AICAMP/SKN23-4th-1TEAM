"""
File: pages/my_info.py
Author: 김지우
Created: 2026-02-24
Description: 마이페이지

Modification History:
- 2026-02-24 (김지우): 초기 틀 생성
- 2026-02-26 (김지우): 전체적인 코드 확인 및 수정 작업
- 2026-02-27 (김지우): 만능 문지기(require_login) 적용 및 로직 최적화
- 2026-02-28 (김지우): 모달 함수 호이스팅 및 탈퇴 로직 안정화
- 2026-03-01 (김지우): 와이드 레이아웃, 오리지널 카드 디자인 복구, 모달 알림 고도화, 엠프티 스테이트 UI 적용"""

import streamlit as st
import time
import random
from utils.api_utils import api_update_profile_image, api_withdraw
from utils.function import inject_custom_header, require_login

st.set_page_config(page_title="AIWORK", page_icon="👾", layout="centered")


# CSS (80% 스케일링 + 🚫 스크롤 완전 잠금 적용)
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap');
:root { color-scheme: light !important; }
* { font-family: 'Pretendard', sans-serif; color-scheme: light !important; color: #111 !important; }
p, span, div, label, h1, h2, h3, h4, h5, h6, li, a, td, th, small, strong, b, i, em { color: #111 !important; }

html, body, .stApp, [data-testid="stAppViewContainer"], .main {
    overflow: hidden !important;
    height: 100vh !important;
    touch-action: none !important;
    color-scheme: light !important;
    color: #111 !important;
    background-color: #f5f5f5 !important;
}

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

::-webkit-scrollbar {
    display: none !important;
}

[data-testid="stAppViewContainer"] { background-color: #f5f5f5 !important; }
[data-testid="stHeader"], [data-testid="stToolbar"] { display: none; color-scheme: light !important; }
.block-container { max-width: 460px !important; padding: 1.5rem 1rem 3rem !important; }

button[data-testid="baseButton-primary"] {
    background-color: #bb38d0 !important; border-color: #bb38d0 !important; color: #ffffff !important;
    border-radius: 10px !important; font-weight: 700 !important; 
    padding: 5px 12px !important; font-size: 12px !important; 
}
button[data-testid="baseButton-primary"]:hover {
    background-color: #a028b5 !important; border-color: #a028b5 !important;
}

button[data-testid="baseButton-secondary"] {
    background-color: #ffffff !important; border: 1px solid #e5e7eb !important; color: #4b5563 !important;
    border-radius: 10px !important; font-weight: 600 !important; 
    padding: 5px 12px !important; font-size: 12px !important; 
}
button[data-testid="baseButton-secondary"]:hover {
    border-color: #bb38d0 !important; color: #bb38d0 !important; background-color: #fdf4ff !important;
}

.status-msg {
    font-size: 11px; text-align: center; margin: 10px 0; font-weight: 600; 
    padding: 10px 14px; border-radius: 8px;
}
.text-success { color: #bb38d0; background-color: #fdf4ff; border: 1px solid #fae8ff; }
.text-error   { color: #e74c3c; background-color: #fdf2f2; border: 1px solid #fca5a5; }
.text-warn    { color: #e67e22; background-color: #fff8eb; border: 1px solid #fcd34d; }

.page-title {
    font-size: 18px; font-weight: 800; color: #111; margin-bottom: 20px; padding-bottom: 12px;
    border-bottom: 2px solid #bb38d0; display: flex; align-items: center; gap: 6px;
}
.profile-card {
    background: linear-gradient(135deg, #7c3aed 0%, #bb38d0 100%);
    border-radius: 16px; padding: 22px 20px 20px; box-shadow: 0 6px 24px rgba(187,56,208,0.25);
    position: relative; overflow: hidden; margin-bottom: 6px;
}
.profile-card::before {
    content: ''; position: absolute; top: -25px; right: -25px; width: 100px; height: 100px; background: rgba(255,255,255,0.08); border-radius: 50%;
}
.profile-card-inner { display: flex; align-items: center; gap: 16px; position: relative; z-index: 1; }

/* 프로필 아바타 (80px -> 64px 축소) */
.profile-avatar-wrap { 
    position: relative; width: 64px; height: 64px; flex-shrink: 0; 
    border-radius: 50%; overflow: hidden; 
    border: 2px solid rgba(255,255,255,0.6); box-shadow: 0 3px 10px rgba(0,0,0,0.2);
}
.profile-avatar { width: 100%; height: 100%; object-fit: cover; display: block; }
.avatar-overlay {
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background: rgba(0,0,0,0.5); color: #fff; 
    display: flex; align-items: center; justify-content: center;
    font-size: 10px; font-weight: 700; opacity: 0; transition: opacity 0.2s;
}

.profile-name  { font-size: 16px; font-weight: 800; color: #fff; margin-bottom: 3px; }
.profile-email { font-size: 11px; color: rgba(255,255,255,0.75); margin-bottom: 8px; }
.tier-badge {
    display: inline-flex; align-items: center; gap: 4px; padding: 3px 10px; border-radius: 16px; font-size: 10px; font-weight: 700;
    background: rgba(255,255,255,0.25); color: #fff; border: 1px solid rgba(255,255,255,0.4);
}

.section-card {
    background: #fff; border-radius: 14px; padding: 6px 0; margin-bottom: 14px; box-shadow: 0 2px 10px rgba(0,0,0,0.06); overflow: hidden;
}
.section-title { font-size: 10px; font-weight: 700; color: #bb38d0; padding: 12px 16px 4px; letter-spacing: 0.5px; text-transform: uppercase; }
.list-row { padding: 12px 16px; border-bottom: 1px solid #f5f3ff; display: flex; align-items: center; justify-content: space-between; }
.list-row:last-child { border-bottom: none; }
.list-label { font-size: 10px; color: #9ca3af; font-weight: 500; margin-bottom: 2px; }
.list-value { font-size: 13px; color: #111; font-weight: 600; }
.list-arrow { color: #d1d5db; font-size: 16px; transition: color 0.2s; }

div[data-testid="stVerticalBlock"]:has(#profile-card-hook) { position: relative; }
div[data-testid="stVerticalBlock"]:has(#profile-card-hook) > div[data-testid="stElementContainer"]:nth-child(2) {
    position: absolute; top: 22px; left: 20px; width: 64px; height: 64px; z-index: 10;
}
div[data-testid="stVerticalBlock"]:has(#profile-card-hook) button {
    width: 64px !important; height: 64px !important; border-radius: 50% !important;
    opacity: 0 !important; cursor: pointer !important; padding: 0 !important; margin: 0 !important;
}
div[data-testid="stVerticalBlock"]:has(button:hover) .avatar-overlay { opacity: 1; }

/* 🔑 2. 비밀번호 영역 (>) 클릭 유령 버튼 (높이 축소) */
div[data-testid="stElementContainer"]:has(#pw-marker) + div[data-testid="stElementContainer"] {
    margin-top: -55px; 
    position: relative; z-index: 10;
}
div[data-testid="stElementContainer"]:has(#pw-marker) + div[data-testid="stElementContainer"] button {
    opacity: 0 !important; height: 55px !important; width: 100% !important; cursor: pointer !important;
}
.pw-row-box { transition: background 0.2s; border-radius: 0 0 14px 14px; }
div[data-testid="stVerticalBlock"]:has(#pw-marker):has(button:hover) .pw-row-box { background-color: #fdf4ff; }
div[data-testid="stVerticalBlock"]:has(#pw-marker):has(button:hover) .list-arrow { color: #bb38d0; }
div[data-testid="stVerticalBlock"]:has(#pw-marker):has(button:hover) .list-label { color: #bb38d0; }

/* 🚨 3. 회원 탈퇴 버튼 (크기 및 폰트 축소) */
div[data-testid="stElementContainer"]:has(#withdraw-marker) + div[data-testid="stElementContainer"] button {
    background-color: #ffffff !important;
    border: 1px solid #d1d5db !important;
    color: #6b7280 !important;
    font-size: 11px !important; /* 13px -> 11px */
    font-weight: 600 !important;
    border-radius: 8px !important;
    padding: 5px 10px !important;
    transition: all 0.2s ease;
}
div[data-testid="stElementContainer"]:has(#withdraw-marker) + div[data-testid="stElementContainer"] button:hover {
    border-color: #ef4444 !important;
    color: #ef4444 !important;
    background-color: #fef2f2 !important;
}

@media (max-width: 768px) {
    .block-container { max-width: 100% !important; padding: 1rem 0.75rem 2rem !important; }
    .profile-card { padding: 18px 16px 16px; }
    .section-card { margin-bottom: 10px; }
    .profile-avatar-wrap { width: 56px; height: 56px; }
}

</style>
""",
    unsafe_allow_html=True,
)


# 모달: 프로필 사진
@st.dialog("프로필 사진 올리기")
def upload_photo_dialog():
    uploaded_file = st.file_uploader(
        "이미지 파일 선택", type=["jpg", "png", "jpeg"], label_visibility="collapsed"
    )
    msg_ph = st.empty()

    if uploaded_file:
        st.image(uploaded_file, caption="미리보기", width=120)
        if st.button("적용하기", type="primary", use_container_width=True):
            with st.spinner("서버에 저장 중..."):
                is_success, result_url_or_msg = api_update_profile_image(uploaded_file)
                if is_success:
                    st.session_state.user["profile_image_url"] = result_url_or_msg
                    msg_ph.markdown(
                        '<div class="status-msg text-success">프로필 사진 변경 완료!</div>',
                        unsafe_allow_html=True,
                    )
                    time.sleep(1)
                    st.rerun()
                else:
                    msg_ph.markdown(
                        f'<div class="status-msg text-error">실패: {result_url_or_msg}</div>',
                        unsafe_allow_html=True,
                    )


# 모달: 비밀번호 변경
@st.dialog("비밀번호 변경")
def change_password_dialog(user_email):
    if "pw_step" not in st.session_state:
        st.session_state.pw_step = "request"
    if "pw_auth_code" not in st.session_state:
        st.session_state.pw_auth_code = None
    if "pw_verified" not in st.session_state:
        st.session_state.pw_verified = False

    steps = ["이메일 인증", "코드 확인", "변경 완료"]
    step_idx = {"request": 0, "verify": 1, "change": 2}[st.session_state.pw_step]
    step_html = '<div style="display:flex; justify-content:center; gap:6px; margin-bottom:16px;">'
    for i, s in enumerate(steps):
        if i < step_idx:
            color = "#bb38d0"
            bg = "#fdf4ff"
            border = "#bb38d0"
        elif i == step_idx:
            color = "#fff"
            bg = "#bb38d0"
            border = "#bb38d0"
        else:
            color = "#adb5bd"
            bg = "#f8f9fa"
            border = "#e9ecef"
        step_html += f'<div style="padding:3px 12px; border-radius:16px; font-size:11px; font-weight:600; color:{color}; background:{bg}; border:1px solid {border};">{s}</div>'
    step_html += "</div>"
    st.markdown(step_html, unsafe_allow_html=True)

    msg_ph = st.empty()

    if st.session_state.pw_step == "request":
        st.markdown(
            f"""
        <div style="text-align:center; padding:8px 0 16px;">
            <div style="font-size:32px; margin-bottom:8px;">📧</div>
            <p style="font-size:12px; color:#555; line-height:1.6;">
                가입하신 이메일로 인증 코드를 발송합니다.<br>
                <b style="color:#bb38d0;">{user_email}</b>
            </p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        if st.button("인증 코드 발송", type="primary", use_container_width=True):
            code = str(random.randint(100000, 999999))
            st.session_state.pw_auth_code = code
            st.session_state.pw_step = "verify"
            st.rerun()

    elif st.session_state.pw_step == "verify":
        st.markdown(
            """
        <div style="text-align:center; padding:8px 0 16px;">
            <div style="font-size:32px; margin-bottom:8px;">🔑</div>
            <p style="font-size:12px; color:#555;">이메일로 발송된 6자리 코드를 입력해주세요.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        msg_ph.markdown(
            '<div class="status-msg text-success">이메일 인증번호 발송 완료 (개발용: '
            + str(st.session_state.pw_auth_code)
            + ")</div>",
            unsafe_allow_html=True,
        )

        input_code = st.text_input("인증 코드", placeholder="6자리 입력", max_chars=6)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("재발송", use_container_width=True):
                code = str(random.randint(100000, 999999))
                st.session_state.pw_auth_code = code
                st.rerun()
        with col2:
            if st.button("확인", type="primary", use_container_width=True):
                if input_code == st.session_state.pw_auth_code:
                    st.session_state.pw_verified = True
                    st.session_state.pw_step = "change"
                    st.rerun()
                else:
                    msg_ph.markdown(
                        '<div class="status-msg text-error">인증 코드가 일치하지 않습니다.</div>',
                        unsafe_allow_html=True,
                    )

    elif st.session_state.pw_step == "change":
        st.markdown(
            """
        <div style="text-align:center; padding:8px 0 16px;">
            <div style="font-size:32px; margin-bottom:8px;">🔒</div>
            <p style="font-size:12px; color:#555;">새로운 비밀번호를 설정해주세요.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )
        new_pw = st.text_input("새 비밀번호", type="password")
        new_pw_confirm = st.text_input("새 비밀번호 확인", type="password")

        if st.button("비밀번호 변경 완료", type="primary", use_container_width=True):
            if not new_pw or not new_pw_confirm:
                msg_ph.markdown(
                    '<div class="status-msg text-warn">비밀번호를 모두 입력해주세요.</div>',
                    unsafe_allow_html=True,
                )
            elif len(new_pw) < 8:
                msg_ph.markdown(
                    '<div class="status-msg text-error">비밀번호는 8자 이상이어야 합니다.</div>',
                    unsafe_allow_html=True,
                )
            elif new_pw != new_pw_confirm:
                msg_ph.markdown(
                    '<div class="status-msg text-error">비밀번호가 일치하지 않습니다.</div>',
                    unsafe_allow_html=True,
                )
            else:
                with st.spinner("안전하게 변경 중입니다..."):
                    time.sleep(1)
                    st.session_state.pw_step = "request"
                    st.session_state.pw_auth_code = None
                    st.session_state.pw_verified = False
                    msg_ph.markdown(
                        '<div class="status-msg text-success">비밀번호 변경 완료!</div>',
                        unsafe_allow_html=True,
                    )
                    time.sleep(1.5)
                    st.rerun()


# ───────────────────────────────────────────
# 모달: 회원 탈퇴
# ───────────────────────────────────────────
@st.dialog("회원 탈퇴")
def withdraw_dialog(email):
    st.markdown(
        f"""
    <div style="text-align:center; padding:8px 0 16px;">
        <div style="font-size:36px; margin-bottom:10px;">😢</div>
        <p style="font-size:13px; color:#111; line-height:1.6; margin-bottom:6px;">
            <b>{email}</b> 계정을 정말 탈퇴하시겠습니까?
        </p>
        <div style="background:#fff5f5; border:1px solid #fecaca; border-radius:8px; padding:10px 14px; margin-top:10px;">
            <p style="color:#e74c3c; font-size:11px; margin:0; line-height:1.5;">
                모든 데이터는 접근이 차단되며<br>30일 후 영구 파기됩니다.
            </p>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2)
    with col1:
        if st.button("취소", use_container_width=True):
            st.rerun()
    with col2:
        if st.button("예, 탈퇴합니다", type="primary", use_container_width=True):
            with st.spinner("탈퇴 처리 중..."):
                api_withdraw(email)
                time.sleep(1.5)
                import extra_streamlit_components as stx

                cookie_manager = stx.CookieManager(key="global_auth_cookie")
                try:
                    cookie_manager.delete("access_token")
                except:
                    pass
                st.session_state.clear()
                st.rerun()


# 문지기 + 헤더
user_id = require_login()
inject_custom_header()

user = st.session_state.user
user_name = user.get("name", "이름 없음")
user_email = user.get("email", "이메일 정보 없음")
user_tier_raw = user.get("tier", "FREE")
profile_url = (
    user.get("profile_image_url")
    or "https://cdn.pixabay.com/photo/2015/10/05/22/37/blank-profile-picture-973460_1280.png"
)


# UI 렌더링
# st.markdown("<br><br><br>", unsafe_allow_html=True)
# st.markdown('<div class="page-title">마이페이지</div>', unsafe_allow_html=True)

# ── 프로필 영역 ──
with st.container():
    st.markdown(
        f"""
    <div id="profile-card-hook" class="profile-card">
        <div class="profile-card-inner">
            <div class="profile-avatar-wrap">
                <img src="{profile_url}" class="profile-avatar">
                <div class="avatar-overlay">+</div>
            </div>
            <div class="profile-info">
                <div class="profile-name">{user_name}</div>
                <div class="profile-email">{user_email}</div>
                <span class="tier-badge">{user_tier_raw} 회원</span>
            </div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    if st.button("투명사진변경버튼", key="photo_btn"):
        upload_photo_dialog()

st.markdown("<br>", unsafe_allow_html=True)

# 계정 정보 섹션
st.markdown(
    f"""
<div class="section-card">
    <div class="section-title">계정 정보</div>
    <div class="list-row">
        <div><div class="list-label">이메일 (아이디)</div><div class="list-value">{user_email}</div></div>
    </div>
    <div class="list-row">
        <div><div class="list-label">이름</div><div class="list-value">{user_name}</div></div>
    </div>
    <div class="list-row" style="border-bottom: none;">
        <div><div class="list-label">회원 등급</div><div class="list-value" style="color: #6b7280;">{user_tier_raw} 회원</div></div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# 보안 섹션 (비밀번호 모달 연동)
with st.container():
    st.markdown(
        """
    <div class="section-card">
        <div class="section-title">보안</div>
        <div class="list-row pw-row-box" style="border-bottom: none;">
            <div>
                <div class="list-label">비밀번호</div>
                <div class="list-value">••••••••</div>
            </div>
            <div class="list-arrow">›</div>
        </div>
    </div>
    <span id="pw-marker"></span>
    """,
        unsafe_allow_html=True,
    )

    if st.button("비밀번호 변경", key="pw_btn", use_container_width=True):
        change_password_dialog(user_email)


# 회원 탈퇴 섹션
st.markdown(
    """
<div style="text-align: center; margin-top: 50px; margin-bottom: 5px;">
    <div style="font-size: 11px; color: #71717a; font-weight: 500;">더 이상 서비스를 이용하지 않으시나요?</div>
</div>
""",
    unsafe_allow_html=True,
)

col_a, col_b, col_c = st.columns([1, 1, 1])
with col_b:
    st.markdown('<span id="withdraw-marker"></span>', unsafe_allow_html=True)
    if st.button("회원 탈퇴", key="withdraw_btn", use_container_width=True):
        withdraw_dialog(user_email)
