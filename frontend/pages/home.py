"""
File: home.py
Author: 김지우
Created: 2026-02-20
Description: 메인 화면 (프리미엄 대시보드 UI)

Modification History:
- 2026-02-21 (김지우): JWT 해독 로직 백엔드 이관
- 2026-02-22 (김지우): stx.CookieManager 타이밍 문제 해결, 쿠키 retry 로직 추가
- 2026-02-23 (양창일): user_profile_image_url 추가
- 2026-02-23 (김지우): UI 적용 및 마이페이지(my_info) 라우팅 연결, 프로필 기능 추가
- 2026-02-24 (유헌상): 채용공고 APi 호출 및 연결
"""

import streamlit as st
import time
from utils.function import inject_custom_header
from utils.home_api_render import render_memo_board, render_realtime_ai_news

# ─── 경로 설정 ─────────────────────────────────────────────────────────
import sys, os

current_dir = os.path.dirname(os.path.abspath(__file__))      # 위치: frontend/pages
frontend_dir = os.path.dirname(current_dir)                     # 위치: frontend
root_dir = os.path.dirname(frontend_dir)                        # 위치: SKN23-3rd-1TEAM (최상위)
backend_dir = os.path.join(root_dir, "backend")

# sys.path에 경로를 강제로 주입!
if root_dir not in sys.path:
    sys.path.append(root_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

## ───────────────────────────────────────────────────────────────────────

st.set_page_config(page_title="AIWORK", page_icon="👾", layout="wide") 

# ─── 서드파티 ──────────────────────────────────────────────────────────
import extra_streamlit_components as stx
from streamlit_option_menu import option_menu
from utils.api_utils import api_get_home_guide, api_verify_token
import yaml

from api.jobs import search_jobs, get_latest_resume
from services.jobs_service import build_job_cards_data
from components.job_cards import render_job_cards


def get_web_context_first(query):
    return "__USE_WEB_SEARCH__"


def get_home_guide_response_stream(user_message, web_context):
    use_web_search = web_context == "__USE_WEB_SEARCH__"
    success, result = api_get_home_guide(user_message, use_web_search=use_web_search)
    if success:
        yield result.get("content", "")
    else:
        yield str(result)



st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700&display=swap');
* { font-family: 'Pretendard', sans-serif; color: #000; }
p, span, div, a { color: #000; }
.subtext { color: #666; }
.stApp { background-color: #f5f5f5 !important; background-image: none !important; }
.block-container { max-width: 1050px !important; padding-top: 4rem !important; padding-bottom: 5rem !important; }


/* 화면 전체를 감싸는 메인 컨테이너의 여백을 강제로 줄임 */
    .block-container {
        padding-top: 1rem !important;    /* 위쪽 여백 */
        padding-bottom: 1rem !important; /* 아래쪽 여백 */
        padding-left: 0.5rem !important;   /* 왼쪽 여백 */
        padding-right: 0.5rem !important;  /* 오른쪽 여백 */
        max-width: 100% !important;      /* 최대 너비 100% 꽉 채우기 */
    }

/* 배경 및 헤더 숨김 */
[data-testid="stAppViewContainer"] { background-color: #f5f7f9 !important; }
[data-testid="stHeader"], #MainMenu, footer, header { visibility:hidden; background:transparent; }

/* 상단 여백 정리 */
.block-container { padding-top: 2rem !important; max-width: 1200px !important; }

/* ✨ Streamlit 기본 컨테이너(상자)를 토스 스타일 카드 UI로 덮어쓰기 */
[data-testid="stVerticalBlockBorderWrapper"] {
    border: none !important;
    border-radius: 16px !important;
    box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04) !important;
    background-color: #ffffff !important;
    padding: 1.5rem !important;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}
[data-testid="stVerticalBlockBorderWrapper"]:hover {
    transform: translateY(-2px);
    box-shadow: 0 8px 28px rgba(0, 0, 0, 0.08) !important;
}

/* 그라데이션 프라이머리 버튼 (면접 시작 버튼 등) */
button[kind="primary"] {
    background: linear-gradient(135deg, #bb38d0 0%, #872a96 100%) !important;
    border: none !important; color: white !important; font-weight: 700 !important;
    border-radius: 12px !important; height: 50px !important; transition: all 0.2s;
}
button[kind="primary"]:hover { filter: brightness(1.1); transform: scale(0.99); }

/* 알림창 디자인 */
.alert-warn    { background:#fff4f4; color:#e74c3c; border-left:4px solid #e74c3c; padding:16px; border-radius:8px; font-size:14px; font-weight:600; margin-bottom:20px; box-shadow: 0 2px 10px rgba(231,76,60,0.1); }
.alert-ok      { background:#fdf4ff; color:#bb38d0; border-left:4px solid #bb38d0; padding:16px; border-radius:8px; font-size:14px; font-weight:700; margin-bottom:20px; box-shadow: 0 2px 10px rgba(187,56,208,0.1); }
.alert-info    { background:#f0f7ff; color:#2980b9; border-left:4px solid #3498db; padding:14px 18px; border-radius:6px; font-size:14px; font-weight:500; margin-bottom:16px; }

/* 탭(Tabs) 디자인 고급화 */
[data-testid="stTabs"] button { font-family: 'Pretendard', sans-serif !important; font-size: 16px !important; font-weight: 600 !important; color: #666 !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color: #bb38d0 !important; border-bottom-color: #bb38d0 !important; }
div[data-baseweb="tab-highlight"] {
    background-color: #bb38d0 !important;
}
/* 이미지 배너 모서리 */
[data-testid="stImage"] img { border-radius: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }

/* 🔥 숨겨진 로그아웃 버튼을 화면에서 완벽하게 제거하는 CSS 트릭 */
.hide-next-element + div {
    display: none !important;
    opacity: 0 !important;
    height: 0 !important;
    margin: 0 !important;
    padding: 0 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<style>
/* ✨ 플로팅 챗봇 버튼 고정 CSS */
div[data-testid="stElementContainer"]:has(#fab-marker) + div[data-testid="stElementContainer"] {
    position: fixed !important;
    bottom: 40px !important;
    right: 40px !important;
    z-index: 99999 !important;
    width: 70px !important;
    height: 70px !important;
}

div[data-testid="stElementContainer"]:has(#fab-marker) + div[data-testid="stElementContainer"] button {
    width: 100% !important;
    height: 100% !important;
    min-width: 70px !important;
    min-height: 70px !important;
    border-radius: 50px !important;
    background: linear-gradient(135deg, #bb38d0, #872a96) !important;
    border: none !important;
    box-shadow: 0 8px 25px rgba(187, 56, 208, 0.4) !important;
    color: transparent !important;
    font-size: 0 !important;
    line-height: 0 !important;
    text-indent: -9999px !important;
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    overflow: hidden !important;
    position: relative !important;
}

div[data-testid="stElementContainer"]:has(#fab-marker) + div[data-testid="stElementContainer"] button:hover {
    transform: scale(1.1) translateY(-5px) !important;
    box-shadow: 0 12px 30px rgba(187, 56, 208, 0.6) !important;
}

div[data-testid="stElementContainer"]:has(#fab-marker) + div[data-testid="stElementContainer"] button::after {
    content: "👾" !important;
    font-size: 32px !important;
    color: white !important;
    position: absolute !important;
    inset: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    line-height: 1 !important;
    text-indent: 0 !important;
    z-index: 1 !important;
    pointer-events: none !important;
}
</style>
""",
    unsafe_allow_html=True,
)

inject_custom_header() # 상단 메뉴바 함수


# 쿠키 매니저 및 인증
cookie_manager = None
access_token_cookie = st.session_state.get("token")
refresh_token_cookie = st.session_state.get("refresh_token")
csrf_token_cookie = st.session_state.get("csrf_token")
def sync_cookie_if_needed(name, value, current_value, key_name):
    if cookie_manager is None:
        return
    if not value:
        return
    if current_value == value:
        return
    cookie_manager.set(name, value, secure=False, same_site="lax", key=key_name)


sync_cookie_if_needed("access_token", st.session_state.get("token"), access_token_cookie, "home_set_access_boot")
sync_cookie_if_needed("refresh_token", st.session_state.get("refresh_token"), refresh_token_cookie, "home_set_refresh_boot")
sync_cookie_if_needed("csrf_token", st.session_state.get("csrf_token"), csrf_token_cookie, "home_set_csrf_boot")

def get_cookie_token_with_retry(
    retries: int = 5, delay: float = 0.1
) -> str | None:
    if cookie_manager is None:
        return st.session_state.get("token")
    for _ in range(retries):
        try:
            token = cookie_manager.get("access_token")
        except Exception:
            token = None

        if token:
            return token

        time.sleep(delay)

    return None

if "new_token" in st.session_state:
    token = st.session_state.new_token
    sync_cookie_if_needed("access_token", token, access_token_cookie, "home_set_access_new")
    sync_cookie_if_needed("refresh_token", st.session_state.get("refresh_token"), refresh_token_cookie, "home_set_refresh_new")
    sync_cookie_if_needed("csrf_token", st.session_state.get("csrf_token"), csrf_token_cookie, "home_set_csrf_new")
    del st.session_state["new_token"]
else:
    token = get_cookie_token_with_retry()

def force_logout(msg: str):
    st.markdown(f'<div class="alert-warn">{msg}</div>', unsafe_allow_html=True)
    st.session_state.clear()
    if cookie_manager:
        try:
            cookie_manager.delete("access_token")
            cookie_manager.delete("refresh_token")
            cookie_manager.delete("csrf_token")
        except Exception:
            pass
    time.sleep(2)
    st.switch_page("app.py")

# 인증 체크 로직
if "user" in st.session_state and st.session_state.user is not None:
    if token:
        st.session_state.token = token
    pass
elif token:
    is_valid, result = api_verify_token(token)
    print('유저정보', result)
    if is_valid:
        sync_cookie_if_needed("access_token", st.session_state.get("token"), access_token_cookie, "home_set_access_verify")
        sync_cookie_if_needed("refresh_token", st.session_state.get("refresh_token"), refresh_token_cookie, "home_set_refresh_verify")
        sync_cookie_if_needed("csrf_token", st.session_state.get("csrf_token"), csrf_token_cookie, "home_set_csrf_verify")
        st.session_state.user = {
            "id": result.get("id"),
            "name": result.get("name"),
            "role": result.get("role", "user"),
            "profile_image_url": result.get("profile_image_url"),
            "email": result.get("email", ""),
            "tier": result.get("tier", "normal"),
        }
        st.session_state.token = token
    else:
        force_logout(f"🔒 {result}")
else:
    force_logout("로그인이 필요한 서비스입니다. 2초 후 이동합니다.")

# 유저 정보 바인딩
user_info = st.session_state.user or {}
user_name = user_info.get("name") or "사용자"
user_role = user_info.get("role", "user")
user_email = user_info.get("email", "이메일 정보 없음")
user_tier = user_info.get("tier", "normal")
user_profile_image_url = user_info.get("profile_image_url")

# 상단 네비게이션 바
st.markdown(
    """
    <style>
    div[data-testid="stElementContainer"]:has(#hide-home-top-nav) + div[data-testid="stElementContainer"] {
        display: none !important;
        height: 0 !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
    }
    </style>
    <div id="hide-home-top-nav"></div>
    """,
    unsafe_allow_html=True,
)
selected = option_menu(
    menu_title=None,
    options=["홈", "AI 면접", "내 기록", "마이페이지"],
    icons=["house", "robot", "clipboard-data", "person"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container": {
            "padding": "0!important",
            "background-color": "#ffffff",
            "border-radius": "16px",
            "box-shadow": "0 2px 10px rgba(0,0,0,0.02)",
            "margin-bottom": "20px",
        },
        "icon": {"color": "#bb38d0", "font-size": "20px"},
        "nav-link": {
            "font-family": "Pretendard",
            "font-size": "15px",
            "font-weight": "600",
            "text-align": "center",
            "margin": "0px",
            "--hover-color": "#f8f9fa",
        },
        "nav-link-selected": {"background-color": "#bb38d0", "font-weight": "700"},
    },
)

# [네비게이션 라우팅 로직]
if selected == "마이페이지":
    st.switch_page("pages/my_info.py")


# ─── 네이버 스타일 커스텀 프로필 카드 렌더링 함수 ──────────────────────────────
def render_profile_card(user_name, user_email, user_tier, user_profile_image_url=None):
    avatar_url = (
        user_profile_image_url
        or f"https://api.dicebear.com/7.x/avataaars/svg?seed={user_name}"
    )

    tier_badge_class = (
        "profile-badge-plus"
        if user_tier.lower() == "plus"
        else "profile-badge-normal"
    )

    st.markdown(f"""
    <style>
    .profile-card-wrap {{
        background: #ffffff; border-radius: 16px; border: 1px solid #f1f3f5;
        box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04); padding: 20px 18px 0 18px;
        overflow: hidden; margin-bottom: 20px;
    }}
    .profile-top-row {{ display: flex; align-items: center; gap: 14px; margin-bottom: 12px; }}
    .profile-avatar-wrap {{ position: relative; flex-shrink: 0; }}
    .profile-avatar {{
        width: 62px; height: 62px; border-radius: 50%; object-fit: cover;
        border: 2.5px solid #ffffff; box-shadow: 0 0 0 2.5px #bb38d0, 0 4px 12px rgba(187,56,208,0.25);
    }}
    .profile-avatar-dot {{
        position: absolute; bottom: 2px; right: 2px; width: 13px; height: 13px;
        background: #22c55e; border-radius: 50%; border: 2px solid #fff;
        box-shadow: 0 0 6px rgba(34,197,94,0.5);
    }}
    .profile-info {{ flex: 1; min-width: 0; }}
    .profile-name-row {{ display: flex; align-items: center; gap: 7px; margin-bottom: 3px; }}
    .profile-name {{ font-size: 16px; font-weight: 700; color: #111; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .profile-badge-plus {{
        display: inline-flex; align-items: center; gap: 3px; background: linear-gradient(135deg, #bb38d0, #872a96);
        color: #fff; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 20px;
        letter-spacing: 0.04em; text-transform: uppercase; box-shadow: 0 2px 8px rgba(187,56,208,0.3);
    }}
    .profile-badge-normal {{
        display: inline-flex; align-items: center; background: #e9ecef; color: #6c757d;
        font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 20px; text-transform: uppercase;
    }}
    .profile-email {{ font-size: 12px; color: #888; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .profile-logout-btn {{
        flex-shrink: 0; display: inline-flex; align-items: center; gap: 5px;
        background: #fdf4ff; color: #bb38d0; border: 1px solid #fae8ff; border-radius: 12px;
        padding: 7px 13px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.2s ease;
    }}
    .profile-logout-btn:hover {{
        background: #bb38d0; color: #fff; border-color: #bb38d0;
        box-shadow: 0 4px 12px rgba(187,56,208,0.3); transform: translateY(-1px);
    }}
    .profile-divider {{ height: 1px; background: #f1f3f5; margin: 12px 0 0 0; }}
    .profile-quick-menu {{ display: flex; align-items: stretch; margin: 0 -18px; }}
    a.profile-quick-item {{
        flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
        padding: 16px 4px; font-size: 13px; font-weight: 600; color: #495057 !important; cursor: pointer;
        transition: all 0.2s ease; border-right: 1px solid #f8f9fa; background: #faf9ff;
        text-decoration: none !important;
    }}
    a.profile-quick-item:last-child {{ border-right: none; }}
    a.profile-quick-item:hover {{ background: #fdf4ff; color: #bb38d0 !important; text-decoration: none !important; }}

    /* ✅ 숨겨진 로그아웃 버튼을 화면 밖으로 밀기 (display:none 쓰면 Streamlit이 DOM에서 제거함) */
    div[data-testid="stButton"]:has(#logout-trigger-btn) {{
        position: absolute !important;
        left: -9999px !important;
        visibility: hidden !important;
        height: 0 !important;
        overflow: hidden !important;
    }}
    </style>
    <div class="profile-card-wrap">
        <div class="profile-top-row">
            <div class="profile-avatar-wrap">
                <img src="{avatar_url}" class="profile-avatar" alt="프로필">
                <div class="profile-avatar-dot"></div>
            </div>
            <div class="profile-info">
                <div class="profile-name-row">
                    <span class="profile-name">{user_name}</span>
                    <span class="{tier_badge_class}">{user_tier.upper()}</span>
                </div>
                <div class="profile-email">{user_email}</div>
            </div>
            <button class="profile-logout-btn" onclick="
                (() => {{
                    const allBtns = window.parent.document.querySelectorAll('button');
                    for (const b of allBtns) {{
                        if (b.textContent.trim().includes('__logout__')) {{
                            b.click();
                            return;
                        }}
                    }}
                }})();
            ">
                로그아웃
            </button>
        </div>
        <div class="profile-divider"></div>
        <div class="profile-quick-menu">
            <a class="profile-quick-item" href="/resume" target="_self">이력서</a>
            <a class="profile-quick-item" href="/mypage" target="_self">내 기록</a>
            <a class="profile-quick-item" href="/my_info" target="_self">내 정보</a>
        </div>
    </div>
    """, unsafe_allow_html=True)

# # ✅ 실제 로그아웃 처리 버튼 (CSS로 화면 밖에 숨김)
# if st.button("__logout__", key="logout-trigger-btn"):
#     try:
#         cookie_manager.delete("access_token")
#     except Exception:
#         pass
#     st.session_state.clear()
#     st.switch_page("app.py")

    

# ─────────────────────────────────────────────────────────────────────────────

# 홈 탭 메인 렌더링
if selected == "홈":
    left_col, _, right_col = st.columns([6.5, 0.2, 3.3])

    # 오른쪽 패널 (프로필 및 액션 카드)
    with right_col:
        # 🔥 새로 만든 네이버 스타일 프로필 카드 렌더링!
        render_profile_card(
            user_name=user_name,
            user_email=user_email,
            user_tier=user_tier,
            user_profile_image_url=user_profile_image_url,
        )

        # 메인 액션 버튼 (AI 면접 시작)
        action_ph = st.empty()
        if st.button("AI 모의 면접 시작", type="primary", use_container_width=True):
            action_ph.markdown(
                '<div class="alert-ok">면접 대기실로 이동합니다!</div>',
                unsafe_allow_html=True,
            )
            time.sleep(1)
            st.switch_page("pages/interview.py")

        st.write("")

        # 안내 카드 (Github 주소 복사 제공)
        with st.container(border=True):
            st.markdown(
                """
                <a href="https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN23-3rd-1TEAM.git" target="_blank" style="text-decoration: none; display: block;">
                    <p style='font-size:14px; font-weight:700; color:#111; margin-bottom:5px;'>🔗 Github Repository</p>
                    <p style='font-size:13px; color:#888; margin:0;'>SKN23-3rd-1TEAM 프로젝트 주소</p>
                </a>
                <div style="
                    font-size: 24px; 
                    font-weight: 800; 
                    background: linear-gradient(135deg, #bb38d0 0%, #872a96 100%);
                    -webkit-background-clip: text;
                    -webkit-text-fill-color: transparent;
                    display: inline-block;
                    letter-spacing: -0.5px;
                    margin-bottom: 10px;
                ">
                    SKN23-3rd-1TEAM
                </div>
                """,
                unsafe_allow_html=True,
            )


    with left_col:
        
        # 1️⃣ 로컬 이미지(AD.png)를 Base64로 변환하여 가져오기
        try:
            import base64
            # 경로 설정 (frontend/assets/AD.png)
            current_dir = os.path.dirname(os.path.abspath(__file__))
            frontend_root = os.path.dirname(current_dir)
            ad_image_path = os.path.join(frontend_root, "assets", "AD.png")
            
            with open(ad_image_path, "rb") as img_file:
                ad_img_base64 = base64.b64encode(img_file.read()).decode("utf-8")
                ad_img_src = f"data:image/png;base64,{ad_img_base64}"
        except Exception as e:
            ad_img_src = "" # 이미지 없을 시 대비

        # 2️⃣ 배너 HTML 렌더링
        if ad_img_src:
            st.markdown(f"""
            <style>
            .ad-banner-wrap {{
                display: block; width: 100%; border-radius: 16px; overflow: hidden;
                margin-bottom: 24px; border: 1px solid #fae8ff;
                box-shadow: 0 4px 20px rgba(187, 56, 208, 0.12);
                transition: transform 0.2s ease; text-decoration: none;
            }}
            .ad-banner-wrap:hover {{ transform: translateY(-3px); box-shadow: 0 8px 28px rgba(187, 56, 208, 0.25); }}
            .ad-banner-wrap img {{ width: 100%; height: auto; display: block; object-fit: cover; }}
            </style>
            
            <a href="/interview" target="_self" class="ad-banner-wrap">
                <img src="{ad_img_src}" alt="AIWORK 광고 배너">
            </a>
            """, unsafe_allow_html=True)


        tab1, tab2, tab3 = st.tabs(["추천 공고", "백엔드 트렌드", "게시판"])
        user_id = st.session_state.user.get('id')
        
        # 채용공고 탭
        with tab1:
            st.markdown("<br>", unsafe_allow_html=True)

            payload = {
                "startPage": 1,
                "display": 20,
            }
            user_id = st.session_state.get("user", {}).get("id") or st.session_state.get("user_id")

            if not user_id:
                st.info('정보를 불러오는 중...')
            else:
                try:
                    parsed = {}

                    resume_cache = f'resume_latest:{user_id}'

                    if resume_cache not in st.session_state:
                        st.session_state[resume_cache] = get_latest_resume(user_id=user_id)

                    resume = st.session_state.get(resume_cache)

                    if resume:                   
                        job_role = resume.get("job_role")
                        analysis_result = resume.get("analysis_result")
                        if job_role and analysis_result:
                            parsed = {"job_role": job_role, 'keywords': analysis_result.get('keywords', '') } 
                    
                    payload.update({k: v for k, v in parsed.items() if v is not None})
                    print('페이로드', payload)
                    data = search_jobs(payload)
                    cards = build_job_cards_data(data)
                    with st.container(height=450):
                        render_job_cards(cards)

                except Exception as e:
                    st.error(f"채용공고 조회 실패: {e}")

        with tab2:  # 📈 백엔드 트렌드 탭
            st.markdown("<br>", unsafe_allow_html=True)

            render_realtime_ai_news()

            st.markdown(
                "<p style='font-size:11px; color:#aaa; text-align:right; margin-top:20px;'>Powered by Tavily Search Engine</p>",
                unsafe_allow_html=True,
            )

        # 게시판
        with tab3:
            st.markdown("<br>", unsafe_allow_html=True)
            current_name = st.session_state.get("user", {}).get("name", "익명")
            render_memo_board(current_name)

# ------------------------------

# ==========================================================
# 🤖 AI 커리어 어드바이저 모달 - ULTRA PREMIUM LIGHT THEME
# ==========================================================

def inject_chatbot_styles():
    st.markdown(
        """
    <style>

    /* ══════════════════════════════════════════════════════
       1. MODAL 창 자체 디자인 (애플/토스 스타일)
    ══════════════════════════════════════════════════════ */
    div[data-testid="stDialog"] > div > div {
        background-color: #F0F8FF !important; 
        border-radius: 28px !important;
        box-shadow: 0 24px 80px rgba(0, 0, 0, 0.12), 0 0 0 1px rgba(0,0,0,0.05) !important;
        border: none !important;
        overflow: hidden !important;
    }

    div[data-testid="stDialog"] > div > div > div {
        padding: 32px 36px 28px !important;
    }

    div[data-testid="stDialog"] h2 {
        font-weight: 800 !important;
        font-size: 1.5rem !important;
        letter-spacing: -0.5px !important;
        background: linear-gradient(135deg, #bb38d0 0%, #872a96 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 8px !important;
    }

    /* ══════════════════════════════════════════════════════
       2. 상태 배지 (실시간 검색 안내)
    ══════════════════════════════════════════════════════ */
    .advisor-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: #fdf4ff;
        border: 1px solid #fae8ff;
        border-radius: 100px;
        padding: 6px 14px;
        font-size: 0.75rem;
        font-weight: 700;
        color: #bb38d0;
        margin-bottom: 24px;
    }
    .advisor-badge::before {
        content: '';
        display: inline-block;
        width: 8px; height: 8px;
        border-radius: 50%;
        background: #bb38d0;
        box-shadow: 0 0 8px rgba(187,56,208,0.6);
        animation: pulse-dot 2s ease-in-out infinite;
    }
    @keyframes pulse-dot {
        0%, 100% { opacity: 1; transform: scale(1); }
        50% { opacity: 0.6; transform: scale(0.85); }
    }

    /* ══════════════════════════════════════════════════════
       3. 채팅 스크롤 영역
    ══════════════════════════════════════════════════════ */
    div[data-testid="stDialog"] div[data-testid="stVerticalBlockBorderWrapper"] {
        background: #F0F8FF !important; 
        border: 1px solid #e2e8f0 !important;
        border-radius: 20px !important;
        padding: 10px !important;
    }

    /* ══════════════════════════════════════════════════════
       4. 말풍선(Bubble) 럭셔리 커스텀
    ══════════════════════════════════════════════════════ */
    @keyframes msg-pop {
        from { opacity: 0; transform: translateY(15px) scale(0.95); }
        to   { opacity: 1; transform: translateY(0) scale(1); }
    }

    .ai-bubble {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 4px 20px 20px 20px;
        padding: 16px 20px;
        color: #1e293b !important;
        font-size: 0.95rem; line-height: 1.6;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
        white-space: pre-wrap;
        animation: msg-pop 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) both;
    }

    .user-bubble {
        background: linear-gradient(135deg, #bb38d0 0%, #872a96 100%);
        border-radius: 20px 4px 20px 20px;
        padding: 16px 20px;
        color: #ffffff !important;
        font-size: 0.95rem; line-height: 1.6;
        box-shadow: 0 8px 20px rgba(187,56,208,0.25);
        white-space: pre-wrap;
        animation: msg-pop 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275) both;
    }

    .sender-label {
        font-size: 12px; color: #bb38d0 !important;
        font-weight: 700; margin-bottom: 6px; padding-left: 4px;
    }

   /* ══════════════════════════════════════════════════════
       🚀 5. 채팅 입력창 (울트라 프리미엄 리빌드 + 퓨어 화이트)
    ══════════════════════════════════════════════════════ */
    :root {
        --accent-primary: #7c3aed;      
        --accent-secondary: #5b21b6;    
        --accent-glow: rgba(124, 58, 237, 0.25);
        --accent-ring: rgba(124, 58, 237, 0.15);
    }

    div[data-testid="stChatInput"] {
        border-radius: 32px !important;
        border: 1.5px solid #e8e0f5 !important;  
        background: #ffffff !important; 
        backdrop-filter: blur(16px) saturate(180%) !important;
        box-shadow:
            0 2px 8px rgba(0, 0, 0, 0.04),
            0 0 0 0px var(--accent-ring),
            inset 0 1px 0 rgba(255,255,255,0.8) !important;
        padding: 0px 10px 0px 5px !important;
        margin-top: -9px !important;
        margin-bottom: 20px !important;
        transition: all 0.35s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
    }

    div[data-testid="stChatInput"]:focus-within {
        border-color: var(--accent-primary) !important;
        box-shadow:
            0 12px 32px var(--accent-glow),
            0 0 0 3px var(--accent-ring),
            inset 0 1px 0 rgba(255,255,255,0.9) !important;
        transform: translateY(-2px) !important;
    }

    div[data-testid="stChatInput"] > div,
    div[data-testid="stChatInput"] div[data-baseweb="textarea"],
    div[data-testid="stChatInput"] div[data-baseweb="base-input"] {
        background-color: transparent !important;
        border: none !important;
    }

    div[data-testid="stChatInput"] textarea {
        background-color: transparent !important; 
        color: #1e1b2e !important;
        font-size: 15px !important;
        font-weight: 500 !important;
        letter-spacing: -0.01em !important;
        caret-color: var(--accent-primary) !important;
    }

    div[data-testid="stChatInput"] textarea::placeholder {
        color: #a89bc2 !important;    
        font-weight: 400 !important;
    }

    button[data-testid="stChatInputSubmitButton"],
    div[data-testid="stChatInputSubmitButton"] {
        background: linear-gradient(145deg, #7c3aed 0%, #5b21b6 100%) !important;
        color: white !important;
        border-radius: 50% !important;
        width: 40px !important;
        height: 40px !important;
        min-width: 40px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        box-shadow:
            0 4px 14px var(--accent-glow),
            inset 0 1px 0 rgba(255,255,255,0.2) !important;
        transition: all 0.28s cubic-bezier(0.34, 1.56, 0.64, 1) !important;
        position: relative !important;
        overflow: hidden !important;
    }

    button[data-testid="stChatInputSubmitButton"]::before,
    div[data-testid="stChatInputSubmitButton"]::before {
        content: "" !important;
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        height: 50% !important;
        background: linear-gradient(180deg, rgba(255,255,255,0.18) 0%, transparent 100%) !important;
        border-radius: 50% 50% 0 0 !important;
        pointer-events: none !important;
    }

    button[data-testid="stChatInputSubmitButton"]:hover,
    div[data-testid="stChatInputSubmitButton"]:hover {
        transform: scale(1.12) translateY(-1px) !important;
        box-shadow:
            0 8px 24px rgba(124, 58, 237, 0.45),
            0 0 0 4px var(--accent-ring) !important;
        background: linear-gradient(145deg, #8b5cf6 0%, #6d28d9 100%) !important;
    }

    button[data-testid="stChatInputSubmitButton"]:active,
    div[data-testid="stChatInputSubmitButton"]:active {
        transform: scale(0.96) !important;
        box-shadow: 0 2px 8px var(--accent-glow) !important;
        transition-duration: 0.1s !important;
    }

    button[data-testid="stChatInputSubmitButton"] svg,
    div[data-testid="stChatInputSubmitButton"] svg {
        fill: #ffffff !important;
        color: #ffffff !important;
        width: 18px !important;
        height: 18px !important;
        filter: drop-shadow(0 1px 2px rgba(0,0,0,0.2)) !important;
    }
    div[data-testid="stDialog"] > div > div > div {
        padding: 32px 32px 32px !important;
    }
    div[data-testid="stDialog"] > div > div > div > div {
        margin: -15px;
        font-family: "Source Sans", sans-serif;
        font-size: 1.2em;
    }
    </style>
    """,
        unsafe_allow_html=True,
    )

# ─── 세션 초기화 ───
if "guide_chat" not in st.session_state:
    st.session_state.guide_chat = [
        {
            "role": "assistant",
            "content": "안녕하세요! <strong>AIWORK 수석 어드바이저 사자개</strong>입니다. ✦\n\n플랫폼 사용법, 취업 트렌드, 직무 고민 등 무엇이든 물어보세요. 실시간 웹 검색으로 2026년 최신 데이터를 기반으로 답변드립니다.",
        }
    ]

# ─── 챗봇 모달 팝업 ───
@st.dialog("👾", width="medium")
def chatbot_modal():
    inject_chatbot_styles()

    st.markdown(
    """
    <div> <strong>AIWORK 가이드 봇</strong></div>
    <div class="advisor-badge">
        실시간 Tavily 웹 검색 연동 · 2026 최신 채용 동향 팩트체크
    </div>
    """,
    unsafe_allow_html=True,
)
    
    use_web_search = st.toggle("웹 검색 기능 켜기", value=False)
    if use_web_search:
        st.caption("활성화됨: 면접 동향, 직무 전망 등 최신 정보가 필요할 때 유용합니다.")
    else:
        st.caption("비활성화됨: 플랫폼 사용법 등 일반적인 질문에 빠르게 답변합니다.")

    chat_container = st.container(height=600)

    for chat in st.session_state.guide_chat:
        with chat_container:
            if chat["role"] == "assistant":
                st.markdown(
                    f"""<div style="display:flex; justify-content:flex-start; margin-bottom:16px; gap:12px;">
                        <div style="font-size:32px; line-height:1; margin-top:20px;">🦁</div>
                        <div style="display:flex; flex-direction:column; max-width:85%;">
                            <div class="sender-label">AI 사자개</div>
                            <div class="ai-bubble">{chat["content"]}</div>
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""<div style="display:flex; justify-content:flex-end; margin-bottom:16px; gap:12px;">
                        <div style="display:flex; flex-direction:column; align-items:flex-end; max-width:85%;">
                            <div class="sender-label" style="color:#94a3b8!important;">사용자</div>
                            <div class="user-bubble">{chat["content"]}</div>
                        </div>
                        <div style="font-size:32px; line-height:1; margin-top:20px;">👤</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    if prompt := st.chat_input("예: 개발자 요새 전망 어때? / AIWORK는 어떻게 써?"):
        st.session_state.guide_chat.append({"role": "user", "content": prompt})

        with chat_container:
            st.markdown(
                f"""<div style="display:flex; justify-content:flex-end; margin-bottom:16px; gap:12px;">
                    <div style="display:flex; flex-direction:column; align-items:flex-end; max-width:85%;">
                        <div class="sender-label" style="color:#94a3b8!important;">사용자</div>
                        <div class="user-bubble">{prompt}</div>
                    </div>
                    <div style="font-size:32px; line-height:1; margin-top:20px;">👤</div>
                </div>""",
                unsafe_allow_html=True,
            )

            web_info = ""
            if use_web_search:
                with st.spinner("웹을 탐색 중입니다..."):
                    web_info = get_web_context_first(prompt)

            placeholder = st.empty()  
            full_reply = ""           
            
            for chunk in get_home_guide_response_stream(prompt, web_info):
                full_reply += chunk
                
                placeholder.markdown(
                    f"""<div style="display:flex; justify-content:flex-start; margin-bottom:16px; gap:12px;">
                        <div style="font-size:32px; line-height:1; margin-top:20px;">🦁</div>
                        <div style="display:flex; flex-direction:column; max-width:85%;">
                            <div class="sender-label">AI 사자개</div>
                            <div class="ai-bubble">{full_reply}▌</div> 
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )

            placeholder.markdown(
                f"""<div style="display:flex; justify-content:flex-start; margin-bottom:16px; gap:12px;">
                    <div style="font-size:32px; line-height:1; margin-top:20px;">🦁</div>
                    <div style="display:flex; flex-direction:column; max-width:85%;">
                        <div class="sender-label">AI 사자개</div>
                        <div class="ai-bubble">{full_reply}</div>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )

        st.session_state.guide_chat.append({"role": "assistant", "content": full_reply})


def render_fab_button():
    st.markdown('<div id="fab-marker"></div>', unsafe_allow_html=True)
    if st.button("chatbot_trigger_btn", key="fab_btn"):
        chatbot_modal()

# 함수 실행
render_fab_button()
