"""
File: sign_up.py
Author: 김다빈, 김지우
Created: 2026-02-20
Description: 회원가입 화면

Modification History:
- 2026-02-20 (김다빈): 초기 틀 생성
- 2026-02-21 (김지우) : 이메일 인증 모달, 실시간 폼 검증, 약관 동의 및 가입 완료 프로세스 전체 구현, DB 연동
- 2026-02-22 (김지우) : Back/Front 구분
- 2026-02-23 (김지우) : DB 연결 에러 발생 시 전용 경고 알림창 UI 적용
-2026-02-26 (김지우) : 내용 수정 및 주석 및 코드 정리 (최종)
"""

# pip install pymysql bcrypt

import streamlit as st
import re
import random
import time
from utils.api_utils import api_check_email, api_send_signup_email, api_signup

st.set_page_config(page_title="AIWORK", page_icon="👾", layout="centered")


# --- 이메일 중복 확인 (DB 조회) ---
def check_email_exists(email):
    success, result = api_check_email(email)
    if not success:
        return "error", result
    return "success", result


# 회원 가입(DB 저장)
def register_user_to_db(email, name, raw_password):
    return api_signup(email, raw_password, name=name)


# 이메일 발송
def send_auth_email(receiver_email, auth_code):
    return api_send_signup_email(receiver_email, auth_code)


# 세션 상태 초기화
if "current_input_email" not in st.session_state:
    st.session_state.current_input_email = ""
if "id_checked" not in st.session_state:
    st.session_state.id_checked = False
if "id_check_result" not in st.session_state:
    st.session_state.id_check_result = None
if "verify_error_msg" not in st.session_state:
    st.session_state.verify_error_msg = ""
if "is_verified" not in st.session_state:
    st.session_state.is_verified = False
if "code_sent" not in st.session_state:
    st.session_state.code_sent = False
if "auth_code" not in st.session_state:
    st.session_state.auth_code = ""

# 약관 동의 세션 상태 관리
if "agree_all" not in st.session_state:
    st.session_state.agree_all = False
if "agree_terms" not in st.session_state:
    st.session_state.agree_terms = False
if "agree_privacy" not in st.session_state:
    st.session_state.agree_privacy = False


def toggle_all():
    st.session_state.agree_terms = st.session_state.agree_all
    st.session_state.agree_privacy = st.session_state.agree_all


def toggle_single():
    if st.session_state.agree_terms and st.session_state.agree_privacy:
        st.session_state.agree_all = True
    else:
        st.session_state.agree_all = False


# 이메일 입력칸 글자 변경 감지 - 초기화 로직
if "email_input" in st.session_state:
    if st.session_state.email_input != st.session_state.current_input_email:
        st.session_state.current_input_email = st.session_state.email_input
        st.session_state.id_checked = False
        st.session_state.id_check_result = None
        st.session_state.verify_error_msg = ""
        st.session_state.is_verified = False
        st.session_state.code_sent = False

# CSS 스타일
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

:root { color-scheme: light !important; }
* { font-family: 'Noto Sans KR', sans-serif; box-sizing: border-box; color: #111 !important; }
html, body, .stApp, [data-testid="stAppViewContainer"] { background-color: #f5f5f5 !important; color: #111 !important; color-scheme: light !important; }
[data-testid="stAppViewContainer"] > .main { background-color: #f5f5f5 !important; }
[data-testid="stMarkdownContainer"], [data-testid="stMarkdownContainer"] p, [data-testid="stMarkdownContainer"] span, label[data-testid="stWidgetLabel"] p, label[data-testid="stWidgetLabel"] span { color: #111 !important; }
[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer, header { visibility: hidden; background: transparent; color-scheme: light !important; }
.block-container { max-width: 460px !important; padding-top: 60px !important; padding-bottom: 60px !important; padding-left: 1rem !important; padding-right: 1rem !important; }
[data-testid="stTextInputRootElement"], [data-testid="stTextInputRootElement"] > div { background-color: #e8e8e8 !important; border-color: transparent !important; transition: background-color 0.2s ease, box-shadow 0.2s ease; }
[data-testid="stTextInputRootElement"]:hover, [data-testid="stTextInputRootElement"] > div:hover { background-color: #f0f0f0 !important; }
[data-testid="stTextInput"], [data-testid="stTextInput"] > div, [data-testid="stTextInput"] > div > div, [data-testid="stTextInput"] input { width: 100% !important; min-width: 0 !important; }

.login-logo { font-size: 32px; font-weight: 700; color: #bb38d0; letter-spacing: -1px; text-align: center; margin-bottom: 28px; }
label[data-testid="stWidgetLabel"] > div > p { font-size: 13px !important; color: #555 !important; font-weight: 500 !important; margin-bottom: 4px !important; }

input[type="text"], input[type="password"] {
    border-color: transparent !important;
    border-radius: 6px !important;
    font-size: 15px !important;
    padding: 12px 14px !important;
    background: transparent !important;
    color: #4a4a4a !important;
    -webkit-text-fill-color: #4a4a4a !important;
    transition: all 0.2s ease;
}
input[type="text"]::placeholder, input[type="password"]::placeholder { color: #999 !important; -webkit-text-fill-color: #999 !important; }
input[type="text"]:focus, input[type="password"]:focus { border-color: #bb38d0 !important; background: #fff !important; outline: none !important; box-shadow: 0 0 0 2px rgba(187,56,208,0.12) !important; }

[data-testid="stButton"] > button[kind="primary"] {
    background-color: #bb38d0 !important;
    color: #ffffff !important;
    border: none !important;
    border-radius: 16px !important;
    height: 50px !important;
    font-size: 16px !important;
    font-weight: 700 !important;
    width: 100% !important;
    letter-spacing: 0.5px;
    transition: background 0.15s;
    margin-top: 0px !important;
}
[data-testid="stButton"] > button[kind="primary"]:hover { background-color: #872a96 !important; }

[data-testid="stButton"] > button[kind="secondary"] {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    height: auto !important;
    min-height: 0 !important;
    display: inline-flex;
    justify-content: flex-end;
    width: 100%;
    margin-top: 6px !important;
}
[data-testid="stButton"] > button[kind="secondary"]:hover,
[data-testid="stButton"] > button[kind="secondary"]:active,
[data-testid="stButton"] > button[kind="secondary"]:focus {
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    color: transparent !important;
}
[data-testid="stButton"] > button[kind="secondary"] p {
    color: #888 !important;
    font-size: 14px !important;
    text-decoration: underline !important;
    text-underline-offset: 3px;
    margin: 0 !important;
    font-weight: 500 !important;
}
[data-testid="stButton"] > button[kind="secondary"]:hover p { color: #333 !important; }

.helper-links { display: flex; justify-content: center; gap: 16px; font-size: 13px; color: #888; margin-top: 18px; }
.helper-links a { color: #888 !important; text-decoration: none; font-weight: 500; }
.helper-links a:hover { color: #bb38d0 !important; text-decoration: underline; }

.status-msg { font-size: 13px; text-align: center; margin-top: 0px; margin-bottom: 12px; font-weight: 500; }
.field-msg  { font-size: 12px; margin-top: -12px; margin-bottom: 12px; margin-left: 4px; font-weight: 500; }
.text-success { color: #2ecc71 !important; }
.text-error   { color: #e74c3c !important; }

div[data-testid="stDialog"] div[data-testid="stMarkdownContainer"] h3 { color: #bb38d0 !important; text-align: center; font-weight: 700; }
p, span, label, h1, h2, h3, h4, h5, h6, div, a, td, th, li, small, strong, b, i, em { color: #111 !important; }
[data-testid="stButton"] > button[kind="primary"] p { color: #fff !important; }

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

email_pattern = r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$"
name_pattern = r"^[가-힣a-zA-Z\s]+$"
pw_pattern = r"^(?=.*[A-Za-z])(?=.*\d)(?=.*[\W_]).{8,}$"

st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="login-logo">회원가입</div>', unsafe_allow_html=True)


# 모달: 약관 보기
@st.dialog("이용약관 및 동의서", width="large")
def show_terms_modal(title, content):
    st.markdown(f"### {title}")
    with st.container(height=350):
        st.markdown(content)
    if st.button("확인", type="primary", use_container_width=True):
        st.rerun()


terms_aiwork_text = """
**제 1 장 총칙**

**제 1 조 (목적)**
본 약관은 AIWORK가 운영하는 AI 모의면접 서비스(이하 "당 사이트")에서 제공하는 모든 서비스(이하 "서비스")의 이용조건 및 절차, 이용자와 당 사이트의 권리, 의무, 책임사항과 기타 필요한 사항을 규정함을 목적으로 합니다.

**제 2 조 (약관의 효력과 변경)**
① 당 사이트는 이용자가 본 약관 내용에 동의하는 것을 조건으로 이용자에게 서비스를 제공하며, 당 사이트의 서비스 제공 행위 및 이용자의 서비스 사용 행위에는 본 약관을 우선적으로 적용하겠습니다.
② 당 사이트는 본 약관을 사전 고지 없이 변경할 수 있으며, 변경된 약관은 당 사이트 내에 공지함으로써 이용자가 직접 확인하도록 할 것입니다. 이용자가 변경된 약관에 동의하지 아니하는 경우 본인의 회원등록을 취소(회원탈퇴)할 수 있으며, 계속 사용할 경우에는 약관 변경에 대한 암묵적 동의로 간주됩니다. 변경된 약관은 공지와 동시에 그 효력을 발휘합니다.

**제 3 조 (약관 외 준칙)**
본 약관에 명시되지 않은 사항은 전기통신기본법, 전기통신사업법, 정보통신망 이용촉진 및 정보보호 등에 관한 법률 및 기타 관련 법령의 규정에 의합니다.

**제 4 조 (용어의 정의)**
① 본 약관에서 사용하는 용어의 정의는 다음과 같습니다.
 1. 이용자 : 본 약관에 따라 당 사이트가 제공하는 서비스를 받는 자
 2. 가 입 : 당 사이트가 제공하는 신청서 양식에 해당 정보를 기입하고, 본 약관에 동의하여 서비스 이용계약을 완료시키는 행위
 3. 회 원 : 당 사이트에 필요한 개인 정보를 제공하여 회원 등록을 한 자로서, 당 사이트의 정보 및 서비스를 이용할 수 있는 자
 4. 아이디 : 이용고객의 식별과 이용자가 서비스 이용을 위하여 이용자가 정한 문자와 숫자의 조합
 5. 비밀번호 : 아이디에 대한 본인 여부를 확인하기 위하여 사용되는 문자, 숫자, 특수문자 등의 조합
 6. 탈퇴 : 서비스 또는 회원이 이용계약을 종료하는 행위
② 본 약관에서 정의하지 않은 용어는 개별서비스에 대한 별도 약관 및 이용규정에서 정의합니다.

**제 2 장 서비스 제공 및 이용**

**제 5 조 (이용 계약의 성립)**
① 이용계약은 이용자가 온라인으로 당 사이트에서 제공하는 이용계약 신청서를 작성하여 가입을 완료하는 것으로 성립됩니다.
② 당 사이트는 다음 각 호에 해당하는 경우에 가입을 취소할 수 있습니다.
 1. 다른 사람의 명의를 사용하여 신청하였을 때
 2. 이용 계약 신청서의 내용을 허위로 기재하였거나 신청하였을 때
 3. 사회의 안녕 질서 혹은 미풍양속을 저해할 목적으로 신청하였을 때
 4. 다른 사람의 당 사이트 서비스 이용을 방해하거나 그 정보를 도용하는 등의 행위를 하였을 때
 5. 당 사이트를 이용하여 법령과 본 약관이 금지하는 행위를 하는 경우
 6. 기타 당 사이트가 정한 이용신청요건이 미비 되었을 때
③ 당 사이트는 다음 각 호에 해당하는 경우 그 사유가 소멸될 때까지 이용계약 성립을 유보할 수 있습니다.
 1. 서비스 관련 제반 용량이 부족한 경우
 2. 기술상 장애 사유가 있는 경우
④ 당 사이트가 제공하는 서비스는 자체 개발하거나 다른 기관과의 협의 등을 통해 제공하는 일체의 서비스를 말하는 것이며, 그 내용을 변경할 경우에는 이용자에게 공지한 후 변경하여 제공할 수 있습니다.

제 6 조 (회원정보 사용에 대한 동의)
① 회원의 개인정보는 공공기관의 개인정보보호법에 의해 보호되며 당 사이트의  개인정보처리방침이 적용됩니다.
② 당 사이트의 회원 정보는 다음과 같이 수집, 사용, 관리, 보호됩니다.
 1. 개인정보의 수집 : 당 사이트는 회원 가입시 회원이 제공하는 정보를 수집합니다.
 2. 개인정보의 사용 : 당 사이트는 서비스 제공과 관련해서 수집된 회원정보를 본인의 승낙 없이 제3자에게 누설, 배포하지 않습니다. 단, 전기통신기본법 등 법률의 규정에 의해 국가기관의 요구가 있는 경우, 범죄에 대한 수사상의 목적이 있거나 방송통신심의위원회의 요청이 있는 경우 또는 기타 관계법령에서 정한 절차에 따른 요청이 있는 경우, 회원이 당 사이트에 제공한 개인정보를 스스로 공개한 경우에는 그러하지 않습니다.
 3. 개인정보의 관리 : 회원은 개인정보의 보호 및 관리를 위하여 서비스의 개인정보관리에서 수시로 회원의 개인정보를 수정/삭제할 수 있습니다. 수신되는 정보 중 불필요하다고 생각되는 부분도 변경/조정할 수 있습니다. 개인정보의 이용기간은 이용자가 가입을 완료하고 개인정보관리에서 회원가입을 탈퇴하는 시점이며 보호기간도 동일합니다.
 4. 개인정보의 보호 : 회원의 개인정보는 오직 회원만이 열람/수정/삭제 할 수 있으며, 이는 전적으로 회원의 아이디와 비밀번호에 의해 관리되고 있습니다. 따라서 타인에게 본인의 아이디와 비밀번호를 알려주어서는 아니 되며, 작업 종료 시에는 반드시 로그아웃 해주시고, 웹 브라우저의 창을 닫아주시기 바랍니다(이는 타인과 컴퓨터를 공유하는 인터넷 카페나 도서관 같은 공공장소에서 컴퓨터를 사용하는 경우에 회원의 정보의 보호를 위하여 필요한 사항입니다.)

제 7 조 (회원의 정보 보안)
① 가입 신청자가 당 사이트 서비스 가입 절차를 완료하는 순간부터 회원은 입력한 정보의 비밀을 유지할 책임이 있으며, 회원의 아이디와 비밀번호를 타인에게 제공하여 발생하는 모든 결과에 대한 책임은 회원 본인에게 있습니다.
② 아이디와 비밀번호에 관한 모든 관리의 책임은 회원에게 있으며, 회원의 아이디나 비밀번호가 부정하게 사용되었다는 사실을 발견한 경우에는 즉시 당 사이트에 신고하여야 합니다. 신고를 하지 않음으로 인한 모든 책임은 회원 본인에게 있습니다.
③ 회원은 당 사이트 서비스의 사용 종료 시마다 정확히 접속을 종료하도록 해야 하며, 정확히 종료하지 아니함으로써 제3자가 이용자 또는 회원에 관한 정보를 이용하게 되는 등의 결과로 인해 발생하는 손해 및 손실에 대하여 당 사이트는 책임을 부담하지 아니합니다.

제 8 조 (서비스 이용시간)
① 서비스 이용시간은 당 사이트의 업무상 또는 기술상 특별한 지장이 없는 한 연중무휴, 1일 24시간을 원칙으로 합니다.
② 제1항의 이용시간은 정기점검 등의 필요로 인하여 당 사이트가 정한 날 또는 시간 및 예기치 않은 사건사고로 인한 시간은 예외로 합니다.

제 9 조 (서비스의 중지 및 정보의 저장과 사용)
① 당 사이트 서비스에 보관되거나 전송된 메시지 및 기타 통신 메시지 등의 내용이 국가의 비상사태, 정전, 당 사이트의 관리 범위 외의 서비스 설비 장애 및 기타 불가항력에 의하여 보관되지 못하였거나 삭제된 경우, 전송되지 못한 경우 및 기타 통신 데이터의 손실이 있을 경우에 당 사이트는 관련 책임을 부담하지 아니합니다.
② 당 사이트가 정상적인 서비스 제공의 어려움으로 인하여 일시적으로 서비스를 중지하여야 할 경우에는 서비스 중지 1주일 전의 고지 후 서비스를 중지할 수 있으며, 이 기간 동안 이용자가 고지내용을 인지하지 못한 데 대하여 당 사이트는 책임을 부담하지 아니합니다. 부득이한 사정이 있을 경우 위 사전 고지기간은 감축되거나 생략될 수 있습니다. 또한 위 서비스 중지에 의하여 본 서비스에 보관되거나 전송된 메시지 및 기타 통신 메시지 등의 내용이 보관되지 못하였거나 삭제․전송되지 못한 경우 및 기타 통신 데이터의 손실이 있을 경우에 대하여도 당 사이트는 책임을 부담하지 아니합니다.
③ 당 사이트의 사정으로 서비스를 영구적으로 중단하여야 할 경우 제2항에 의거합니다. 다만, 이 경우 사전 고지기간은 1개월로 합니다.
④ 당 사이트는 사전 고지 후 서비스를 일시적으로 수정, 변경 및 중단할 수 있으며, 이에 대하여 이용자 또는 제3자에게 어떠한 책임도 부담하지 아니합니다.
⑤ 당 사이트는 이용자가 본 약관의 내용에 위배되는 행동을 한 경우, 임의로 서비스 사용을 제한 및 중지할 수 있습니다. 이 경우 당 사이트는 위 이용자의 접속을 금지할 수 있습니다.
⑥ 장기간 휴면 회원인 경우 안내 메일 또는 공지사항 발표 후 1주일간의 통지 기간을 거쳐 서비스 사용을 중지할 수 있습니다.

제 10 조 (서비스의 변경 및 해지)
① 당 사이트는 이용자가 서비스를 이용하여 얻은 자료로 인한 손해에 관하여 책임을 지지 않으며, 회원이 본 서비스에 게재한 정보, 자료, 사실의 신뢰도, 정확성 등 내용에 관하여는 책임을 지지 않습니다.
② 당 사이트는 서비스 이용과 관련하여 가입자에게 발생한 손해 중 가입자의 고의, 과실에 의한 손해에 대하여 책임을 부담하지 아니합니다.
③ 회원을 탈퇴하고자 하는 경우에는 당 사이트 로그인 후 회원탈퇴 절차에 따라 해지할 수 있습니다.

제 11 조 (정보 제공 및 홍보물 게재)
① 당 사이트는 서비스를 운영함에 있어서 각종 정보를 서비스에 게재하는 방법 등으로 회원에게 제공할 수 있습니다.
② 당 사이트는 서비스에 적절하다고 판단되거나 활용 가능성 있는 홍보물을 게재할 수 있습니다.

제 12 조 (게시물의 저작권)
① 이용자가 게시한 게시물의 내용에 대한 권리는 이용자에게 있습니다.
② 당 사이트는 게시된 내용을 사전 통지 없이 편집, 이동할 수 있는 권리를 보유하며, 다음의 경우 사전 통지 없이 삭제할 수 있습니다.
 1. 본 이용약관에 위배되거나 상용 또는 불법, 음란, 저속하다고 판단되는 게시물을 게시한 경우
 2. 다른 이용자 또는 제 3자를 비방하거나 중상모략으로 명예를 손상시키는 내용인 경우
 3. 공공질서 및 미풍양속에 위반되는 내용인 경우
 4. 범죄적 행위에 결부된다고 인정되는 내용일 경우
 5. 제3자의 저작권 등 기타 권리를 침해하는 내용인 경우
 6. 기타 관계 법령에 위배되는 경우
③ 이용자의 게시물이 타인의 저작권을 침해함으로써 발생하는 민․형사상의 책임은 전적으로 이용자가 부담하여야 합니다.

제 13 조 (이용자의 행동규범 및 서비스 이용제한)
① 이용자가 제공하는 정보의 내용이 허위인 것으로 판명되거나, 그러하다고 의심할 만한 합리적인 사유가 발생할 경우 당 사이트는 이용자의 본 서비스 사용을 일부 또는 전부 중지할 수 있으며, 이로 인해 발생하는 불이익에 대해 책임을 부담하지 아니합니다.
② 이용자가 당 사이트 서비스를 통하여 게시, 전송, 입수하였거나 전자메일 기타 다른 수단에 의하여 게시, 전송 또는 입수한 모든 형태의 정보에 대하여는 이용자가 모든 책임을 부담하며 당 사이트는 어떠한 책임도 부담하지 아니합니다.
③ 당 사이트는 당 사이트가 제공한 서비스가 아닌 가입자 또는 기타 유관기관이 제공하는 서비스의 내용상의 정확성, 완전성 및 질에 대하여 보장하지 않습니다. 따라서 당 사이트는 이용자가 위 내용을 이용함으로 인하여 입게 된 모든 종류의 손실이나 손해에 대하여 책임을 부담하지 아니합니다.
④ 이용자는 본 서비스를 통하여 다음과 같은 행동을 하지 않는데 동의합니다.
 1. 타인의 아이디와 비밀번호를 도용하는 행위
 2. 저속, 음란, 모욕적, 위협적이거나 타인의 사생활을 침해할 수 있는 내용을 전송, 게시, 게재, 전자메일 또는 기타의 방법으로 전송하는 행위
 3. 서비스를 통하여 전송된 내용의 출처를 위장하는 행위
 4. 법률, 계약에 의하여 이용할 수 없는 내용을 게시, 게재, 전자메일 또는 기타의 방법으로 전송하는 행위
 5. 타인의 특허, 상표, 영업비밀, 저작권, 기타 지적재산권을 침해하는 내용을 게시, 게재, 전자메일 또는 기타의 방법으로 전송하는 행위
 6. 당 사이트의 승인을 받지 아니한 광고, 판촉물, 정크메일, 스팸, 행운의 편지, 피라미드 조직 기타 다른 형태의 권유를 게시, 게재, 전자메일 또는 기타의 방법으로 전송하는 행위
 7. 다른 이용자의 개인정보를 수집 또는 저장하는 행위
⑤ 당 사이트는 회원이 본 약관을 위배했다고 판단되면 서비스와 관련된 모든 정보를 이용자의 동의 없이 삭제할 수 있습니다.
⑥ 제1항의 규정에 의하여 서비스의 제한을 받게 된 이용자가 위 조치에 대한 이의가 
있을 경우에는 이의신청을 할 수 있으나 서비스 제한 시 삭제된 이용자의 데이터에 대해서는 책임지지 아니합니다. 
⑦ 당 사이트는 제6항의 규정에 의한 이의신청에 대하여 그 확인이 완료될 때까지 이용제한을 연기할 수 있습니다.

제 3 장 의무 및 책임

제 14 조 (당 사이트의 의무)
① 당 사이트는 법령과 본 약관이 금지하거나 미풍양속에 반하는 행위를 하지 않으며, 지속적이고 안정적으로 서비스를 제공하기 위해 노력할 의무가 있습니다.
② 당 사이트는 회원의 개인 신상 정보를 본인의 승낙 없이 타인에게 누설, 배포하지 않습니다. 다만, 전기통신관련법령 등 관계법령에 의하여 관계 국가기관 등의 요구가 있는 경우에는 그러하지 아니합니다.
③ 당 사이트는 이용자가 안전하게 당 사이트 서비스를 이용할 수 있도록 이용자의 개인정보 (신용정보 포함) 보호를 위한 보안시스템을 갖추어야 합니다.
④ 당 사이트는 이용자의 귀책사유로 인한 서비스 이용 장애에 대하여 책임을 지지 않습니다.

제 15 조 (회원의 의무)
① 회원 가입시에 요구되는 정보는 정확하게 기입하여야 합니다. 또한 이미 제공된 회원에 대한 정보가 정확한 정보가 되도록 유지, 갱신하여야 하며, 회원은 자신의 아이디 및 비밀번호를 제3자에게 이용하게 해서는 안 됩니다.
② 회원은 당 사이트의 사전 승낙 없이 서비스를 이용하여 어떠한 영리행위도 할 수 없습니다.
③ 회원은 당 사이트 서비스를 이용하여 얻은 정보를 당 사이트의 사전승낙 없이 복사, 복제, 변경, 번역, 출판·방송 기타의 방법으로 사용하거나 이를 타인에게 제공할 수 없습니다.
④ 이용자는 당 사이트 서비스 이용과 관련하여 다음 각 호의 행위를 하여서는 안 됩니다.
 1. 다른 회원의 아이디를 부정 사용하는 행위
 2. 범죄행위를 목적으로 하거나 기타 범죄행위와 관련된 행위
 3. 선량한 풍속, 기타 사회질서를 해하는 행위
 4. 타인의 명예를 훼손하거나 모욕하는 행위
 5. 타인의 지적재산권 등의 권리를 침해하는 행위
 6. 해킹행위 또는 컴퓨터바이러스의 유포행위
 7. 타인의 의사에 반하여 광고성 정보 등 일정한 내용을 지속적으로 전송하는 행위
 8. 서비스의 안전적인 운영에 지장을 주거나 줄 우려가 있는 일체의 행위
 9. 당 사이트에 게시된 정보의 변경

제 4 장 기 타

제 16 조 (당 사이트의 소유권)
① 당 사이트가 제공하는 서비스, 그에 필요한 소프트웨어, 이미지, 마크, 로고, 디자인, 서비스명칭, 정보 및 상표 등과 관련된 지적재산권 및 기타 권리는 당 사이트에 소유권이 있습니다.
② 이용자는 당 사이트가 명시적으로 승인한 경우를 제외하고는 전항의 소정의 각 재산에 대한 전부 또는 일부의 수정, 대여, 대출, 판매, 배포, 제작, 양도, 재라이센스, 담보권 설정 행위, 상업적 이용 행위를 할 수 없으며, 제3자로 하여금 이와 같은 행위를 하도록 허락할 수 없습니다.

제 17 조 (양도금지)
회원이 서비스의 이용권한, 기타 이용계약 상 지위를 타인에게 양도, 증여할 수 없으며, 이를 담보로 제공할 수 없습니다.

제 18 조 (손해배상)
당 사이트는 무료로 제공되는 서비스와 관련하여 회원에게 어떠한 손해가 발생하더라도 당 사이트가 고의로 행한 범죄행위를 제외하고 이에 대하여 책임을 부담하지 아니합니다.

제 19 조 (면책조항)
① 당 사이트는 서비스에 표출된 어떠한 의견이나 정보에 대해 확신이나 대표할 의무가 없으며 회원이나 제3자에 의해 표출된 의견을 승인하거나 반대하거나 수정하지 않습니다. 당 사이트는 어떠한 경우라도 회원이 서비스에 담긴 정보에 의존해 얻은 이득이나 입은 손해에 대해 책임이 없습니다.
② 당 사이트는 회원간 또는 회원과 제3자간에 서비스를 매개로 하여 물품거래 혹은 금전적 거래 등과 관련하여 어떠한 책임도 부담하지 아니하고, 회원이 서비스의 이용과 관련하여 기대하는 이익에 관하여 책임을 부담하지 않습니다.

제 20 조 (관할법원)
본 서비스 이용과 관련하여 발생한 분쟁에 대해 소송이 제기될 경우 대전지방법원을 전속적 관할 법원으로 합니다.

부 칙
(시행일) 본 약관은 2018년 8월 1일부터 시행됩니다. 개정된 약관의 적용일자 이전 이용자 또는 회원은 개정된 이용약관의 적용을 받습니다.
								
"""

terms_privacy_text = """
**1. 개인정보의 수집항목 및 수집방법 **
AIWORK에서는 기본적인 회원 서비스 제공을 위한 필수정보로 실명인증정보와 가입정보로 구분하여 다음의 정보를 수집하고 있습니다. 필수정보를 입력해주셔야 회원 서비스 이용이 가능합니다.

  가. 수집하는 개인정보의 항목 
    * 수집하는 필수항목
      - 실명인증정보 : 이름, 이메일 인증
      - 가입정보 : 아이디, 비밀번호, 성명, 이메일
	
   [컴퓨터에 의해 자동으로 수집되는 정보]
   인터넷 서비스 이용과정에서 아래 개인정보 항목이 자동으로 생성되어 수집될 수 있습니다. 
    - IP주소, 서비스 이용기록, 방문기록 등
	
  나. 개인정보 수집방법
      홈페이지 회원가입을 통한 수집 

**2. 개인정보의 수집/이용 목적 및 보유/이용 기간**
AIWORK에서는 정보주체의 회원 가입일로부터 서비스를 제공하는 기간 동안에 한하여 AIWORK 서비스를 이용하기 위한 최소한의 개인정보를 보유 및 이용 하게 됩니다. 회원가입 등을 통해 개인정보의 수집·이용, 제공 등에 대해 동의하신 내용은 언제든지 철회하실 수 있습니다. 회원 탈퇴를 요청하거나 수집/이용목적을 달성하거나 보유/이용기간이 종료한 경우, 사업 폐지 등의 사유발생시 개인 정보를 지체 없이 파기합니다.

  * 실명인증정보
    - 개인정보 수집항목 : 이름, 이메일 인증
    - 개인정보의 수집·이용목적   : 홈페이지 이용에 따른 본인 식별/인증절차에 이용
    - 개인정보의 보유 및 이용기간 : 별도로 저장하지 않으며 실명인증용으로만 이용

  * 가입정보
    - 개인정보 수집항목 : 아이디, 비밀번호, 성명, 이메일
    - 개인정보의 수집·이용목적 : 홈페이지 서비스 이용 및 회원관리, 불량회원의 부정 이용방지, 민원신청 및 처리 등
    - 개인정보의 보유 및 이용기간 : 1년 또는 회원탈퇴시

정보주체는 개인정보의 수집·이용목적에 대한 동의를 거부할 수 있으며, 동의 거부시 AIWORK에 회원가입이 되지 않으며, AIWORK에서 제공하는 서비스를 이용할 수 없습니다.

**3. 수집한 개인정보 제3자 제공**
AIWORK에서는 정보주체의 동의, 법률의 특별한 규정 등 개인정보 보호법 제17조 및 제18조에 해당하는 경우에만 개인정보를 제3자에게 제공합니다.
		
**4. 개인정보 처리업무 안내**
AIWORK에서는 개인정보의 취급위탁은 하지 않고 있으며, 원활한 서비스 제공을 위해 아래의 기관을 통한 실명인증 및 공공 I-PIN, GPKI 인증을 하고 있습니다. 

  * 수탁업체
    - 사자개 
"""


# 모달: 이메일 인증
@st.dialog("이메일 인증", width="small")
def email_verification_modal():
    st.markdown("### 본인 확인을 진행합니다")
    st.caption("가입하실 이메일 주소로 인증번호를 발송합니다.")

    st.text_input(
        "인증받을 이메일 주소",
        value=st.session_state.current_input_email,
        disabled=True,
    )

    btn_text = "인증번호 재발송" if st.session_state.code_sent else "인증번호 발송"

    if st.button(btn_text, type="primary", use_container_width=True):
        with st.spinner("이메일 발송 중..."):
            code = str(random.randint(100000, 999999))
            is_sent, msg = send_auth_email(st.session_state.current_input_email, code)

            if is_sent:
                st.session_state.code_sent = True
                st.session_state.auth_code = code
            else:
                st.markdown(
                    f'<div class="status-msg text-error">{msg}</div>',
                    unsafe_allow_html=True,
                )

    if st.session_state.code_sent and not st.session_state.is_verified:
        st.markdown("---")
        auth_input = st.text_input(
            "인증번호 6자리", placeholder="메일로 받은 인증번호를 입력하세요"
        )
        msg_placeholder = st.empty()

        if st.button("인증 확인", type="primary", use_container_width=True):
            if auth_input == st.session_state.auth_code:
                st.session_state.is_verified = True
                msg_placeholder.markdown(
                    '<div class="status-msg text-success">인증이 완료되었습니다.</div>',
                    unsafe_allow_html=True,
                )
                time.sleep(1.5)
                st.rerun()
            else:
                msg_placeholder.markdown(
                    '<div class="status-msg text-error">인증번호가 일치하지 않습니다. 다시 확인해주세요.</div>',
                    unsafe_allow_html=True,
                )


# 가입 완료 축하 창
@st.dialog("가입 완료", width="small")
def signup_success_modal(user_name):
    st.markdown(
        f"""
        <div style="text-align: center; padding: 20px 0;">
            <div style="font-size: 50px; margin-bottom: 10px;">👾</div>
            <h2 style="color: #bb38d0; font-weight: 700; margin-bottom: 15px;">환영합니다!</h2>
            <p style="font-size: 16px; color: #333; line-height: 1.5;">
                <b>{user_name}</b>님,<br>회원가입이 성공적으로 완료되었습니다.
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

    for key in [
        "current_input_email",
        "id_checked",
        "id_check_result",
        "verify_error_msg",
        "is_verified",
        "code_sent",
        "auth_code",
    ]:
        if key in st.session_state:
            st.session_state[key] = (
                False if isinstance(st.session_state[key], bool) else ""
            )

    st.switch_page("app.py")


# 아이디 입력 & 중복 확인 (DB 연동)
col1, col2 = st.columns([2.5, 1])

with col1:
    user_id = st.text_input(
        "아이디 (이메일)", placeholder="이메일을 입력하세요", key="email_input"
    )
with col2:
    st.markdown("<div style='margin-top: 29px;'></div>", unsafe_allow_html=True)
    if st.button("중복 확인", type="primary", use_container_width=True):
        st.session_state.verify_error_msg = ""
        st.session_state.id_checked = False

        if not user_id:
            st.session_state.id_check_result = "empty"
        elif not re.match(email_pattern, user_id):
            st.session_state.id_check_result = "invalid"
        else:
            with st.spinner("DB에서 확인 중..."):
                time.sleep(0.3)
                status, result = check_email_exists(user_id)
                st.session_state.id_checked = True

                if status == "error":
                    st.session_state.id_check_result = "db_error"
                    st.session_state.verify_error_msg = result
                else:
                    st.session_state.id_check_result = not result

if st.session_state.id_check_result == "empty":
    st.markdown(
        '<div class="status-msg text-error">이메일을 먼저 입력해주세요.</div>',
        unsafe_allow_html=True,
    )
elif st.session_state.id_check_result == "invalid":
    st.markdown(
        '<div class="status-msg text-error">유효한 이메일 형식이 아닙니다.</div>',
        unsafe_allow_html=True,
    )
elif st.session_state.id_checked and st.session_state.id_check_result == True:
    st.markdown(
        '<div class="status-msg text-success">사용가능한 아이디(이메일)입니다.</div>',
        unsafe_allow_html=True,
    )
elif st.session_state.id_checked and st.session_state.id_check_result == False:
    st.markdown(
        '<div class="status-msg text-error">이미 가입된 아이디(이메일)입니다.</div>',
        unsafe_allow_html=True,
    )
elif st.session_state.id_check_result == "db_error":
    st.markdown(
        f"""
    <div style="background-color: #fff4f4; border-left: 5px solid #e74c3c; padding: 16px; border-radius: 8px; margin-top: 10px; margin-bottom: 20px; box-shadow: 0 4px 6px rgba(231, 76, 60, 0.1);">
        <span style="font-size: 15px; font-weight: bold; color: #e74c3c;">시스템 오류 발생</span><br>
        <span style="font-size: 13px; color: #555; line-height: 1.5;">{st.session_state.verify_error_msg}</span><br>
        <span style="font-size: 12px; color: #888; margin-top: 8px; display: inline-block;">※ .env 파일의 DB 비밀번호 옆에 한글 주석이 없는지 확인해주세요.</span>
    </div>
    """,
        unsafe_allow_html=True,
    )


# 인증하기
if not st.session_state.is_verified:
    if st.button("인증하기", type="primary", use_container_width=True):
        if not st.session_state.id_checked or st.session_state.id_check_result != True:
            st.session_state.verify_error_msg = (
                "먼저 사용 가능한 아이디(이메일)인지 중복 확인을 진행해주세요."
            )
        else:
            st.session_state.verify_error_msg = ""
            email_verification_modal()

    auth_msg_ph = st.empty()
    if (
        st.session_state.verify_error_msg
        and st.session_state.id_check_result != "db_error"
    ):
        auth_msg_ph.markdown(
            f'<div class="status-msg text-error">{st.session_state.verify_error_msg}</div>',
            unsafe_allow_html=True,
        )
else:
    st.button("인증 완료", type="primary", use_container_width=True, disabled=True)
    auth_msg_ph = st.empty()


# 추가 정보 입력
st.markdown(
    "<hr style='margin:15px 0; border:none; border-top:1px solid #ddd;'>",
    unsafe_allow_html=True,
)

name = st.text_input("이름 (닉네임)", placeholder="한글 또는 영문만 입력하세요")
name_msg_ph = st.empty()

if name:
    if re.match(name_pattern, name):
        name_msg_ph.markdown(
            '<div class="field-msg text-success">올바른 이름 형식입니다.</div>',
            unsafe_allow_html=True,
        )
    else:
        name_msg_ph.markdown(
            '<div class="field-msg text-error">이름은 한글과 영어만 입력 가능합니다.</div>',
            unsafe_allow_html=True,
        )

password = st.text_input(
    "비밀번호", type="password", placeholder="영문, 숫자, 특수문자 포함 8자리 이상"
)
pw_msg_ph = st.empty()

if password:
    if re.match(pw_pattern, password):
        pw_msg_ph.markdown(
            '<div class="field-msg text-success">안전한 비밀번호입니다.</div>',
            unsafe_allow_html=True,
        )
    else:
        pw_msg_ph.markdown(
            '<div class="field-msg text-error">영문, 숫자, 특수문자를 모두 포함하여 8자리 이상이어야 합니다.</div>',
            unsafe_allow_html=True,
        )

password_confirm = st.text_input(
    "비밀번호 확인", type="password", placeholder="비밀번호를 다시 입력하세요"
)
pw2_msg_ph = st.empty()

if password_confirm:
    if password == password_confirm:
        pw2_msg_ph.markdown(
            '<div class="field-msg text-success">비밀번호가 일치합니다.</div>',
            unsafe_allow_html=True,
        )
    else:
        pw2_msg_ph.markdown(
            '<div class="field-msg text-error">비밀번호가 일치하지 않습니다. 다시 입력해주세요.</div>',
            unsafe_allow_html=True,
        )


# 약관 동의
st.markdown("<br>", unsafe_allow_html=True)
with st.container(border=True):
    st.checkbox("**전체 동의하기**", key="agree_all", on_change=toggle_all)
    st.caption(
        "실명 인증된 아이디로 가입, 필수 이용약관 및 개인정보 수집/이용 동의를 포함합니다."
    )
    st.markdown("<hr style='margin: 5px 0 15px 0;'>", unsafe_allow_html=True)

    tcol1, tcol2 = st.columns([5, 1])
    with tcol1:
        st.checkbox(
            "(필수) **AIWORK** 이용약관", key="agree_terms", on_change=toggle_single
        )
    with tcol2:
        if st.button("보기", key="btn_view_terms"):
            show_terms_modal("AIWORK 이용약관", terms_aiwork_text)

    pcol1, pcol2 = st.columns([5, 1])
    with pcol1:
        st.checkbox(
            "(필수) 개인정보 수집/이용 동의",
            key="agree_privacy",
            on_change=toggle_single,
        )
    with pcol2:
        if st.button("보기", key="btn_view_privacy"):
            show_terms_modal("개인정보 수집/이용 동의", terms_privacy_text)

terms_msg_ph = st.empty()


# 가입하기 버튼 & DB 저장
if st.button("가입하기", type="primary", use_container_width=True):
    has_error = False

    if not st.session_state.is_verified:
        auth_msg_ph.markdown(
            '<div class="status-msg text-error">이메일 인증을 먼저 진행해주세요.</div>',
            unsafe_allow_html=True,
        )
        has_error = True

    if not name:
        name_msg_ph.markdown(
            '<div class="field-msg text-error">이름을 입력해주세요.</div>',
            unsafe_allow_html=True,
        )
        has_error = True
    elif not re.match(name_pattern, name):
        name_msg_ph.markdown(
            '<div class="field-msg text-error">이름은 한글과 영어만 입력 가능합니다.</div>',
            unsafe_allow_html=True,
        )
        has_error = True

    if not password:
        pw_msg_ph.markdown(
            '<div class="field-msg text-error">비밀번호를 입력해주세요.</div>',
            unsafe_allow_html=True,
        )
        has_error = True
    elif not re.match(pw_pattern, password):
        pw_msg_ph.markdown(
            '<div class="field-msg text-error">영문, 숫자, 특수문자를 모두 포함하여 8자리 이상이어야 합니다.</div>',
            unsafe_allow_html=True,
        )
        has_error = True

    if not password_confirm:
        pw2_msg_ph.markdown(
            '<div class="field-msg text-error">비밀번호 확인을 입력해주세요.</div>',
            unsafe_allow_html=True,
        )
        has_error = True
    elif password != password_confirm:
        pw2_msg_ph.markdown(
            '<div class="field-msg text-error">비밀번호가 일치하지 않습니다. 다시 확인해주세요.</div>',
            unsafe_allow_html=True,
        )
        has_error = True

    if not st.session_state.agree_terms or not st.session_state.agree_privacy:
        terms_msg_ph.markdown(
            '<div class="field-msg text-error" style="text-align:center; margin-top:5px;">필수 약관에 모두 동의해주세요.</div>',
            unsafe_allow_html=True,
        )
        has_error = True

    # DB 저장
    if not has_error:
        with st.spinner("정보를 안전하게 저장 중입니다..."):
            success, msg = register_user_to_db(
                st.session_state.current_input_email, name, password
            )

        if success:
            signup_success_modal(name)
        else:
            st.error(msg)

st.markdown(
    """
<div class="helper-links">
    <a href="/" target="_self">이미 계정이 있으신가요? 로그인</a>
</div>
""",
    unsafe_allow_html=True,
)
