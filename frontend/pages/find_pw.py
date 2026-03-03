"""
File: find_pw.py
Author: 김다빈, 김지우
Created: 2026-02-20
Description: 비밀번호 찾기 화면

Modification History:
- 2026-02-20 (김다빈): 초기 틀 생성
- 2026-02-21 (김지우): SMTP 이메일 인증 로직 및 세션 기반 단계별 비밀번호 재설정 UI 구현
- 2026-02-22 (김지우) : Back/Front 구분
- 2026-02-26 (김지우) : 비밀번호 찾기 페이지 전체적인 코드 확인 및 수정 작업 (최종)

"""

import streamlit as st
import re
import random
import time
from utils.api_utils import api_check_email, api_send_reset_email, api_reset_password

st.set_page_config(page_title="AIWORK", page_icon="👾", layout="centered")


def check_user_exists(email):
    success, result = api_check_email(email)
    return success and result


def update_password_in_db(email, new_raw_password):
    return api_reset_password(email, new_raw_password)


def send_auth_email(receiver_email, auth_code):
    return api_send_reset_email(receiver_email, auth_code)


# CSS
st.markdown(
    """
<style>
[data-testid="stSidebar"], div[data-testid="collapsedControl"] { display: none !important; }
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

:root { color-scheme: light !important; }
* { font-family: 'Noto Sans KR', sans-serif; box-sizing: border-box; color: #111 !important; }
html, body, .stApp, [data-testid="stAppViewContainer"] { background-color: #f5f5f5 !important; color: #111 !important; color-scheme: light !important; }
[data-testid="stAppViewContainer"] > .main { background-color: #f5f5f5 !important; }
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] span,
label[data-testid="stWidgetLabel"] p,
label[data-testid="stWidgetLabel"] span { color: #111 !important; }
[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer, header { visibility: hidden; background: transparent; color-scheme: light !important; }
.block-container { max-width: 460px !important; padding-top: 60px !important; padding-bottom: 60px !important; padding-left: 1rem !important; padding-right: 1rem !important; }

[data-testid="stTextInputRootElement"],
[data-testid="stTextInputRootElement"] > div { background-color: #e8e8e8 !important; border-color: transparent !important; transition: background-color 0.2s ease, box-shadow 0.2s ease; }
[data-testid="stTextInputRootElement"]:hover,
[data-testid="stTextInputRootElement"] > div:hover { background-color: #f0f0f0 !important; }
[data-testid="stTextInput"], [data-testid="stTextInput"] > div,
[data-testid="stTextInput"] > div > div, [data-testid="stTextInput"] input { width: 100% !important; min-width: 0 !important; }

.login-logo { font-size: 32px; font-weight: 700; color: #bb38d0; letter-spacing: -1px; text-align: center; margin-bottom: 28px; }
label[data-testid="stWidgetLabel"] > div > p { font-size: 13px !important; color: #555 !important; font-weight: 500 !important; margin-bottom: 4px !important; }

input[type="text"], input[type="password"] {
    border-color: transparent !important; border-radius: 6px !important;
    font-size: 15px !important; padding: 12px 14px !important;
    background: transparent !important; color: #4a4a4a !important;
    -webkit-text-fill-color: #4a4a4a !important; transition: all 0.2s ease;
}
input[type="text"]::placeholder, input[type="password"]::placeholder { color: #999 !important; -webkit-text-fill-color: #999 !important; }
input[type="text"]:focus, input[type="password"]:focus {
    border-color: #bb38d0 !important; background: #fff !important;
    outline: none !important; box-shadow: 0 0 0 2px rgba(187,56,208,0.12) !important;
}

[data-testid="stButton"] > button[kind="primary"] {
    background-color: #bb38d0 !important; color: #fff !important; border: none !important;
    border-radius: 16px !important; height: 50px !important; font-size: 16px !important;
    font-weight: 700 !important; width: 100% !important; letter-spacing: 0.5px;
    transition: background 0.15s; margin-top: 0px !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover { background-color: #872a96 !important; }

div[data-testid="stButton"] > button {
    background-color: #bb38d0 !important; color: #fff !important; border: none !important;
    border-radius: 16px !important; height: 50px !important; font-size: 16px !important;
    font-weight: 700 !important; letter-spacing: 0.5px; transition: background 0.15s; margin-top: 6px;
}
div[data-testid="stButton"] > button:hover { background-color: #872a96 !important; }

.helper-links { display: flex; justify-content: center; gap: 16px; font-size: 13px; color: #888; margin-top: 18px; }
.helper-links a { color: #888 !important; text-decoration: none; font-weight: 500; }
.helper-links a:hover { color: #bb38d0 !important; text-decoration: underline; }
.helper-sep { color: #ddd; }

.info-text  { font-size: 14px; color: #666 !important; text-align: center; margin-bottom: 20px; }

.status-msg { font-size: 13px; text-align: center; margin-top: 0px; margin-bottom: 12px; font-weight: 500; }
.field-msg  { font-size: 12px; margin-top: -12px; margin-bottom: 12px; margin-left: 4px; font-weight: 500; }
.text-success { color: #2ecc71 !important; }
.text-error   { color: #e74c3c !important; }
.text-warn    { color: #e67e22 !important; }
p, span, label, h1, h2, h3, h4, h5, h6, div, a, td, th, li, small, strong, b, i, em { color: #111 !important; }
[data-testid="stButton"] > button p, div[data-testid="stButton"] > button p { color: #fff !important; }

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

@media (max-width: 768px) {
    .block-container { padding-top: 32px !important; padding-bottom: 32px !important; }
    .login-logo { font-size: 28px; margin-bottom: 20px; }
}
</style>
""",
    unsafe_allow_html=True,
)


@st.dialog("비밀번호 변경 완료", width="small")
def pw_reset_success_modal():
    st.markdown(
        """
        <div style="text-align: center; padding: 20px 0;">
            <div style="font-size: 50px; margin-bottom: 10px;">👾</div>
            <h2 style="color: #bb38d0; font-weight: 700; margin-bottom: 15px;">변경 완료!</h2>
            <p style="font-size: 16px; color: #333; line-height: 1.5;">
                비밀번호가 성공적으로 변경되었습니다.<br>
                새 비밀번호로 로그인해주세요.
            </p>
            <p style="font-size: 13px; color: #888; margin-top: 25px;">
                3초 후 로그인 페이지로 자동 이동합니다...
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    progress_bar = st.progress(0)
    for i in range(100):
        time.sleep(0.03)
        progress_bar.progress(i + 1)
    st.session_state.reset_step = 1
    st.session_state.auth_code = ""
    st.session_state.target_email = ""
    st.switch_page("app.py")


email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
pw_pattern = r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[\W_]).{8,}$"

if "reset_step" not in st.session_state:
    st.session_state.reset_step = 1
if "auth_code" not in st.session_state:
    st.session_state.auth_code = ""
if "target_email" not in st.session_state:
    st.session_state.target_email = ""

st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="login-logo">비밀번호 찾기</div>', unsafe_allow_html=True)


if st.session_state.reset_step == 1:
    st.markdown(
        '<div class="info-text">가입하신 이메일 아이디를 입력해주세요.<br>비밀번호 재설정 인증번호를 보내드립니다.</div>',
        unsafe_allow_html=True,
    )

    email_input = st.text_input(
        "아이디 (이메일)", placeholder="이메일을 입력하세요", key="email_input"
    )
    step1_msg = st.empty()

    if st.button("인증번호 발송", use_container_width=True):
        if not email_input:
            step1_msg.markdown(
                '<div class="status-msg text-warn">이메일을 입력해주세요.</div>',
                unsafe_allow_html=True,
            )
        elif not re.match(email_pattern, email_input):
            step1_msg.markdown(
                '<div class="status-msg text-error">유효한 이메일 형식이 아닙니다. 다시 확인해주세요.</div>',
                unsafe_allow_html=True,
            )
        else:
            with st.spinner("가입 정보 확인 및 이메일 발송 중..."):
                if not check_user_exists(email_input):
                    step1_msg.markdown(
                        '<div class="status-msg text-error">가입되지 않은 이메일입니다. 아이디를 다시 확인해주세요.</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    generated_code = str(random.randint(100000, 999999))
                    is_sent, error_msg = send_auth_email(email_input, generated_code)

                    if is_sent:
                        st.session_state.auth_code = generated_code
                        st.session_state.target_email = email_input
                        st.session_state.reset_step = 2
                        step1_msg.markdown(
                            '<div class="status-msg text-success">인증번호가 발송되었습니다. 이메일함을 확인해주세요!</div>',
                            unsafe_allow_html=True,
                        )
                        time.sleep(1.5)
                        st.rerun()
                    else:
                        step1_msg.markdown(
                            f'<div class="status-msg text-error">이메일 발송 실패: {error_msg}</div>',
                            unsafe_allow_html=True,
                        )


elif st.session_state.reset_step == 2:
    st.markdown(
        f'<div class="info-text"><b>{st.session_state.target_email}</b>(으)로<br>인증번호를 발송했습니다. 6자리 숫자를 입력해주세요.</div>',
        unsafe_allow_html=True,
    )

    code_input = st.text_input("인증번호", placeholder="6자리 숫자 입력")
    step2_msg = st.empty()

    if st.button("인증 확인", use_container_width=True):
        if code_input == st.session_state.auth_code:
            st.session_state.reset_step = 3
            st.rerun()
        else:
            step2_msg.markdown(
                '<div class="status-msg text-error">인증번호가 일치하지 않습니다.</div>',
                unsafe_allow_html=True,
            )

# 새 비번 설정
elif st.session_state.reset_step == 3:
    st.markdown(
        '<div class="info-text">이메일 인증이 완료되었습니다.<br>새로운 비밀번호를 설정해주세요.</div>',
        unsafe_allow_html=True,
    )

    new_password = st.text_input(
        "새 비밀번호",
        type="password",
        placeholder="영문, 숫자, 특수문자 포함 8자리 이상",
    )
    pw_msg_ph = st.empty()

    new_password_check = st.text_input(
        "새 비밀번호 확인", type="password", placeholder="비밀번호를 다시 입력하세요"
    )
    pw2_msg_ph = st.empty()

    if new_password:
        if re.match(pw_pattern, new_password):
            pw_msg_ph.markdown(
                '<div class="field-msg text-success">안전한 비밀번호입니다.</div>',
                unsafe_allow_html=True,
            )
        else:
            pw_msg_ph.markdown(
                '<div class="field-msg text-error">영문, 숫자, 특수문자를 모두 포함하여 8자리 이상이어야 합니다.</div>',
                unsafe_allow_html=True,
            )

    if new_password_check:
        if new_password == new_password_check:
            pw2_msg_ph.markdown(
                '<div class="field-msg text-success">비밀번호가 일치합니다.</div>',
                unsafe_allow_html=True,
            )
        else:
            pw2_msg_ph.markdown(
                '<div class="field-msg text-error">비밀번호가 일치하지 않습니다. 다시 확인해주세요.</div>',
                unsafe_allow_html=True,
            )

    step3_msg = st.empty()

    if st.button("비밀번호 변경 완료", use_container_width=True):
        has_error = False

        if not new_password or not re.match(pw_pattern, new_password):
            pw_msg_ph.markdown(
                '<div class="field-msg text-error">비밀번호 형식을 확인해주세요.</div>',
                unsafe_allow_html=True,
            )
            has_error = True
        elif new_password != new_password_check:
            pw2_msg_ph.markdown(
                '<div class="field-msg text-error">비밀번호가 일치하지 않습니다.</div>',
                unsafe_allow_html=True,
            )
            has_error = True

        if not has_error:
            with st.spinner("비밀번호를 안전하게 변경 중입니다..."):
                success, msg = update_password_in_db(
                    st.session_state.target_email, new_password
                )

            if success:
                pw_reset_success_modal()
            else:
                step3_msg.markdown(
                    f'<div class="status-msg text-error">{msg}</div>',
                    unsafe_allow_html=True,
                )


# 하단 링크
st.markdown(
    """
<div class="helper-links">
    <a href="/" target="_self">로그인으로 돌아가기</a>
    <span class="helper-sep">|</span>
    <a href="/sign_up" target="_self">회원가입</a>
</div>
""",
    unsafe_allow_html=True,
)
