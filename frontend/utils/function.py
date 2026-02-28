"""
Shared frontend utility helpers.
"""

import base64
import os
import time

import streamlit as st

from utils.api_utils import api_verify_token


def require_login():
    """Validate the current login state and recover from cookie when possible."""
    import extra_streamlit_components as stx

    if (
        "user_id" in st.session_state
        and isinstance(st.session_state["user_id"], int)
        and "user" in st.session_state
    ):
        return st.session_state["user_id"]

    cookie_manager = stx.CookieManager(key="global_auth_cookie")
    token = cookie_manager.get("access_token")
    refresh_token = cookie_manager.get("refresh_token")
    csrf_token = cookie_manager.get("csrf_token")

    if refresh_token:
        st.session_state.refresh_token = refresh_token
    if csrf_token:
        st.session_state.csrf_token = csrf_token

    if st.session_state.get("token"):
        cookie_manager.set("access_token", st.session_state.token)
    if st.session_state.get("refresh_token"):
        cookie_manager.set("refresh_token", st.session_state.refresh_token)
    if st.session_state.get("csrf_token"):
        cookie_manager.set("csrf_token", st.session_state.csrf_token)

    if token:
        is_valid, result = api_verify_token(token)
        if is_valid:
            st.session_state["user_id"] = result.get("id")
            st.session_state.user = {
                "id": result.get("id"),
                "name": result.get("name"),
                "role": result.get("role", "user"),
                "profile_image_url": result.get("profile_image_url"),
                "email": result.get("email", ""),
                "tier": result.get("tier", "normal"),
            }
            st.session_state.token = token
            return st.session_state["user_id"]

        st.warning("세션이 만료되었습니다. 다시 로그인해주세요.")
        time.sleep(1)
        st.switch_page("pages/login.py")
        st.stop()

    if "cookie_waiting" not in st.session_state:
        st.session_state["cookie_waiting"] = True
        st.spinner("사용자 정보를 불러오는 중입니다...")
        st.stop()

    del st.session_state["cookie_waiting"]
    st.warning("로그인이 필요한 서비스입니다.")
    time.sleep(1.5)
    st.switch_page("pages/login.py")
    st.stop()


def get_image_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


def inject_custom_header():
    user_info = st.session_state.get("user", {})
    user_name = user_info.get("name", "사용자")

    current_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_root = os.path.dirname(current_dir)
    image_path = os.path.join(frontend_root, "assets", "AIWORK.jpg")

    try:
        img_src = f"data:image/jpeg;base64,{get_image_base64(image_path)}"
    except FileNotFoundError:
        img_src = ""

    header_html = f"""
    <style>
    .block-container {{
        padding-top: 100px !important;
    }}
    .custom-header {{
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 72px;
        background-color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 40px;
        border-bottom: 1px solid #e2e8f0;
        z-index: 999999;
        font-family: 'Pretendard', sans-serif;
    }}
    .header-logo {{
        display: flex;
        align-items: center;
        text-decoration: none;
    }}
    .header-logo img {{
        height: 28px;
        width: auto;
        object-fit: contain;
    }}
    .header-menu {{
        display: flex;
        gap: 40px;
        position: absolute;
        left: 50%;
        transform: translateX(-50%);
    }}
    .header-menu a {{
        text-decoration: none;
        color: #111111;
        font-size: 16px;
        font-weight: 600;
        transition: color 0.2s;
    }}
    .header-menu a:hover {{
        color: #bb38d0;
    }}
    .header-utils {{
        display: flex;
        align-items: center;
    }}
    .icon-group {{
        display: flex;
        font-size: 15px;
        font-weight: 600;
    }}
    .icon-group a {{
        text-decoration: none;
        color: #333333;
        transition: transform 0.2s;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .icon-group a:hover {{
        color: #bb38d0;
    }}
    </style>
    <div class="custom-header">
        <a href="/home" target="_self" class="header-logo">
            <img src="{img_src}" alt="AIWORK 로고">
        </a>
        <div class="header-menu">
            <a href="/interview" target="_self">AI면접</a>
            <a href="/resume" target="_self">이력서</a>
            <a href="/mypage" target="_self">내기록</a>
            <a href="/my_info" target="_self">마이페이지</a>
        </div>
        <div class="header-utils">
            <div class="icon-group">
                <a href="/my_info" target="_self" title="마이페이지">👤 {user_name}님 반갑습니다.</a>
            </div>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)


def render_memo_board(current_user_name="익명"):
    from utils.home_api_render import render_memo_board as _render_memo_board

    return _render_memo_board(current_user_name)


def render_realtime_ai_news():
    from utils.home_api_render import render_realtime_ai_news as _render_realtime_ai_news

    return _render_realtime_ai_news()
