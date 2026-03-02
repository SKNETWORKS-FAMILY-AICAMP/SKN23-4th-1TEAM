"""
Shared frontend utility helpers.
"""

import base64
import os
import time

import streamlit as st

from utils.api_utils import api_verify_token


import time
import streamlit as st
import extra_streamlit_components as stx
from utils.api_utils import api_verify_token


def require_login():
    """
    로그인 상태를 완벽하게 검증하고,
    새로고침으로 세션이 날아갔다면 쿠키를 통해 자동 복구해주는 완벽한 문지기입니다.
    """
    cookie_manager = stx.CookieManager(key="global_auth_cookie")

    # 1. 로그아웃 요청이 들어오면 제일 먼저 처리
    if st.query_params.get("do_logout") == "1":
        try:
            cookie_manager.delete("access_token")
            cookie_manager.delete("refresh_token")
            cookie_manager.delete("csrf_token")
        except Exception:
            pass

        st.session_state.clear()
        st.query_params.clear()
        st.switch_page("app.py")
        st.stop()

    if "user" in st.session_state and st.session_state.user:
        return st.session_state.user.get("id", "guest")

    token = cookie_manager.get("access_token")

    if token:
        is_valid, result = api_verify_token(token)
        if is_valid:
            st.session_state.user = {
                "id": result.get("id"),
                "name": result.get("name"),
                "role": result.get("role", "user"),
                "profile_image_url": result.get("profile_image_url"),
                "email": result.get("email", ""),
                "tier": result.get("tier", "normal"),
            }
            st.session_state.token = token

            if "cookie_checking" in st.session_state:
                del st.session_state["cookie_checking"]

            user_id = st.session_state.user.get("id")
            if user_id is None:
                st.warning("유효하지 않은 유저 정보입니다. 다시 로그인해주세요.")
                time.sleep(1)
                st.switch_page("app.py")
                st.stop()
            return user_id
        else:
            st.warning("세션이 만료되었습니다. 다시 로그인해주세요.")
            time.sleep(1)
            st.switch_page("app.py")
            st.stop()
    else:
        if "cookie_checking" not in st.session_state:
            st.session_state["cookie_checking"] = True
            st.stop()
        else:
            del st.session_state["cookie_checking"]
            st.warning("로그인이 필요한 서비스입니다.")
            time.sleep(1)
            st.switch_page("app.py")
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
        img_base64 = get_image_base64(image_path)
        img_src = f"data:image/jpeg;base64,{img_base64}"
    except FileNotFoundError:
        img_src = ""

    is_admin = str(user_info.get("role", "")).lower() == "admin"
    admin_link = (
        '<a href="/admin" target="_self">🔥 관리자 대시보드</a>' if is_admin else ""
    )

    # CSS + 로그아웃 버튼 숨김
    st.markdown(
        """
    <style>
    .block-container { padding-top: 100px !important; }
    div[data-testid="stElementContainer"]:has(#global-logout-marker),
    div[data-testid="stElementContainer"]:has(#global-logout-marker) + div[data-testid="stElementContainer"] {
        position: absolute !important; width: 0px !important; height: 0px !important;
        opacity: 0 !important; overflow: hidden !important; z-index: -9999 !important; pointer-events: none !important;
        margin: 0 !important; padding: 0 !important;
    }
    @media (max-width: 768px) {
        .block-container { padding-top: 80px !important; }
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

    # st.html()은 새니타이저 없이 직접 렌더링 (Streamlit 1.33+)
    st.html(
        f"""
    <style>
    .custom-header {{
        position: fixed; top: 0; left: 0; right: 0; height: 72px;
        background-color: #ffffff; display: flex; align-items: center; justify-content: space-between;
        padding: 0 40px; border-bottom: 1px solid #e2e8f0; z-index: 999999;
        font-family: 'Pretendard', sans-serif;
    }}
    .header-logo {{ display: flex; align-items: center; text-decoration: none; }}
    .header-logo img {{ height: 28px; width: auto; object-fit: contain; }}
    .header-menu {{ display: flex; gap: 40px; position: absolute; left: 50%; transform: translateX(-50%); }}
    .header-menu a {{ text-decoration: none; color: #111111 !important; font-size: 16px; font-weight: 600; transition: color 0.2s; }}
    .header-menu a:hover {{ color: #bb38d0 !important; }}
    .header-utils {{ display: flex; align-items: center; }}
    .header-user-wrap {{ position: relative; display: inline-block; }}
    .header-user-btn {{
        background: #fdf4ff; color: #bb38d0 !important; border: 1px solid #fae8ff;
        padding: 8px 16px; border-radius: 24px; font-size: 14px; font-weight: 700;
        cursor: pointer; transition: all 0.2s ease; display: flex; align-items: center; gap: 6px;
    }}
    .header-user-btn:hover {{
        background: #bb38d0; color: #fff !important; box-shadow: 0 4px 12px rgba(187,56,208,0.25);
    }}
    .header-dropdown {{
        visibility: hidden; opacity: 0; position: absolute; right: 0; top: calc(100% + 10px);
        background-color: #ffffff; min-width: 160px; box-shadow: 0 10px 30px rgba(0,0,0,0.08);
        border-radius: 14px; overflow: hidden; z-index: 9999999; border: 1px solid #f1f3f5;
        transform: translateY(-10px); transition: all 0.2s ease;
    }}
    .header-user-wrap:hover .header-dropdown {{
        visibility: visible; opacity: 1; transform: translateY(0);
    }}
    .header-dropdown a {{
        color: #333 !important; padding: 14px 18px; text-decoration: none; display: flex; align-items: center;
        gap: 10px; font-size: 14px; font-weight: 600; transition: background 0.2s; cursor: pointer;
    }}
    .header-dropdown a:hover {{
        background-color: #fdf4ff; color: #bb38d0 !important;
    }}
    .mobile-nav-links {{ display: none; }}
    .dropdown-divider {{ height: 1px; background: #f1f3f5; margin: 0; }}
    @media (max-width: 768px) {{
        .custom-header {{ padding: 0 16px; height: 60px; }}
        .header-menu {{ display: none !important; }}
        .header-user-btn {{ font-size: 12px; padding: 6px 12px; }}
        .mobile-nav-links {{ display: block; }}
    }}
    </style>
    <div class="custom-header">
        <a href="/home" target="_self" class="header-logo">
            <img src="{img_src}" alt="AIWORK 로고">
        </a>
        <div class="header-menu">
            <a href="/interview" target="_self">AI면접</a>
            <a href="/resume" target="_self">이력서</a>
            <a href="/mypage" target="_self">내 기록</a>
            <a href="/my_info" target="_self">마이페이지</a>
        </div>
        <div class="header-utils">
            <div class="header-user-wrap">
                <div class="header-user-btn">
                    👤 {user_name} 님 ▾
                </div>
                <div class="header-dropdown">
                    <div class="mobile-nav-links">
                        <a href="/interview" target="_self">AI면접</a>
                        <a href="/resume" target="_self">이력서</a>
                        <a href="/mypage" target="_self">내 기록</a>
                        <a href="/my_info" target="_self">마이페이지</a>
                        <div class="dropdown-divider"></div>
                    </div>
                    {admin_link}
                    <a href="/login?logout=true" target="_self">로그아웃</a>
                </div>
            </div>
        </div>
    </div>
    """
    )

    # 전역 로그아웃 유령 버튼
    st.markdown('<div id="global-logout-marker"></div>', unsafe_allow_html=True)
    if st.button("__global_logout__", key="global_logout_trigger"):
        st.toast("로그아웃 되었습니다.")

        # 쿠키 삭제 및 세션 초기화
        import extra_streamlit_components as stx

        cookie_manager = stx.CookieManager(key="global_header_cookie")
        try:
            cookie_manager.delete("access_token")
            cookie_manager.delete("refresh_token")
            cookie_manager.delete("csrf_token")
        except Exception:
            pass

        st.session_state.clear()
        time.sleep(1)
        st.switch_page("login")


def render_memo_board(current_user_name="익명"):
    from utils.home_api_render import render_memo_board as _render_memo_board

    return _render_memo_board(current_user_name)


def render_realtime_ai_news():
    from utils.home_api_render import (
        render_realtime_ai_news as _render_realtime_ai_news,
    )

    return _render_realtime_ai_news()
