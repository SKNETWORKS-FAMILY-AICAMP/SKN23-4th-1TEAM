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
from utils.function import render_memo_board, render_realtime_ai_news


# # ─── 경로 설정 ─────────────────────────────────────────────────────────
# import sys, os, time

# current_dir = os.path.dirname(os.path.abspath(__file__))
# frontend_dir = os.path.dirname(current_dir)
# root_dir = os.path.dirname(frontend_dir)
# backend_dir = os.path.join(root_dir, "backend")

# if backend_dir not in sys.path:
#     sys.path.append(backend_dir)
# if frontend_dir not in sys.path:
#     sys.path.append(frontend_dir)

## ───────────────────────────────────────────────────────────────────────


st.set_page_config(
    page_title="AIWORK", page_icon="👾", layout="wide"
)  # 모든 페이지에 고정 멘트 (utils에 넣기 가능하면 넣기)

# ─── 서드파티 ──────────────────────────────────────────────────────────
import extra_streamlit_components as stx
from streamlit_option_menu import option_menu
from utils.api_utils import api_verify_token
import yaml
import os

from api.jobs import search_jobs, get_latest_resume
from services.jobs_service import build_job_cards_data
from components.job_cards import render_job_cards

from backend.services.tavily_service import get_web_context
from backend.services.llm_service import get_home_guide_response


st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700&display=swap');
* { font-family: 'Pretendard', sans-serif; }

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

/* 프로필 뱃지 및 텍스트 */
.profile-badge-plus { background: linear-gradient(135deg, #bb38d0, #7b2cb1); color: white; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; margin-left: 6px; box-shadow: 0 2px 8px rgba(187,56,208,0.3); }
.profile-badge-normal { background: #e9ecef; color: #6c757d; padding: 4px 10px; border-radius: 20px; font-size: 11px; font-weight: 700; margin-left: 6px; }
.user-name-title { font-size: 18px; font-weight: 700; color: #111; margin: 0; display:flex; align-items:center; }
.user-email-text { font-size: 13px; color: #888; font-weight: 500; margin-top: 2px; }

/* 그라데이션 프라이머리 버튼 (면접 시작 버튼 등) */
button[kind="primary"] {
    background: linear-gradient(135deg, #bb38d0 0%, #872a96 100%) !important;
    border: none !important; color: white !important; font-weight: 700 !important;
    border-radius: 12px !important; height: 50px !important; transition: all 0.2s;
}
button[kind="primary"]:hover { filter: brightness(1.1); transform: scale(0.99); }

/* 일반 버튼들 (이력서, 내기록, 마이페이지) */
button[kind="secondary"] {
    background-color: #f8f9fa !important; border: 1px solid #e9ecef !important;
    color: #495057 !important; border-radius: 10px !important; font-weight: 600 !important; transition: all 0.2s;
}
button[kind="secondary"]:hover { background-color: #e9ecef !important; color: #111 !important; border-color:#dee2e6 !important;}

/* 알림창 디자인 */
.alert-warn    { background:#fff4f4; color:#e74c3c; border-left:4px solid #e74c3c; padding:16px; border-radius:8px; font-size:14px; font-weight:600; margin-bottom:20px; box-shadow: 0 2px 10px rgba(231,76,60,0.1); }
.alert-ok      { background:#fdf4ff; color:#bb38d0; border-left:4px solid #bb38d0; padding:16px; border-radius:8px; font-size:14px; font-weight:700; margin-bottom:20px; box-shadow: 0 2px 10px rgba(187,56,208,0.1); }
.alert-info    { background:#f0f7ff; color:#2980b9; border-left:4px solid #3498db; padding:14px 18px; border-radius:6px; font-size:14px; font-weight:500; margin-bottom:16px; }

/* 탭(Tabs) 디자인 고급화 */
[data-testid="stTabs"] button { font-family: 'Pretendard', sans-serif !important; font-size: 16px !important; font-weight: 600 !important; color: #888 !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color: #bb38d0 !important; border-bottom-color: #bb38d0 !important; }

/* 이미지 배너 모서리 */
[data-testid="stImage"] img { border-radius: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }
</style>
""",
    unsafe_allow_html=True,
)

# ============================= 상단 메뉴바 (유틸로 넣어주시면 감사하겠습니다 !) ==================================
import streamlit as st
import base64
import os


# 1. 로컬 이미지를 읽어서 Base64 문자열로 변환하는 함수
def get_image_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")


def inject_custom_header():
    # 2. 이미지 절대 경로 설정 (home.py 위치를 기준으로 계산)
    # 현재 파일(home.py)의 상위->상위 폴더 구조에 맞춰 경로를 잘 잡아주셔야 합니다.
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 예시: home.py가 frontend 폴더 안에 있다면, 상위 폴더로 가서 backend/data/... 로 접근
    project_root = os.path.dirname(current_dir)
    image_path = os.path.join(project_root, "assets", "AIWORK.jpg")

    # 3. Base64 문자열 생성
    try:
        img_base64 = get_image_base64(image_path)
        # JPEG 이미지일 경우 data:image/jpeg;base64, 를 붙여줍니다.
        img_src = f"data:image/jpeg;base64,{img_base64}"
    except FileNotFoundError:
        st.error(f"이미지 경로를 찾을 수 없습니다: {image_path}")
        img_src = ""  # 에러 시 빈 문자열 처리

    # 파이썬 f-string을 사용하기 위해 기존 HTML 문자열을 f""" """ 로 감쌉니다.
    header_html = f"""
    <style>
    /* 상단 여백 조절 */
    .block-container {{
        padding-top: 100px !important; 
    }}
    
    /* 헤더 전체 컨테이너 */
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

    /* 왼쪽 로고 영역 */
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

    /* 가운데 메뉴 영역 */
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

    /* 오른쪽 유틸리티 영역 */
    .header-utils {{
        display: flex;
        align-items: center;
    }}
    .icon-group {{
        display: flex;
        font-size: 24px;
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
        transform: scale(1.1);
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
            <div class="icon-group">
                <a href="/my_info" target="_self" title="마이페이지">👤</a>
            </div>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)


# 함수 실행
inject_custom_header()
# ============================================================================


# --- 글로벌 공지사항 배너 로직 ---
# try:
#     frontend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
#     settings_path = os.path.join(frontend_dir, "utils", "admin_settings.yaml")
#     if os.path.exists(settings_path):
#         with open(settings_path, "r", encoding="utf-8") as f:
#             g_settings = yaml.safe_load(f) or {}
#             if g_settings.get("notice_enabled") and g_settings.get("system_notice"):
#                 st.info(f"📢 {g_settings.get('system_notice')}")
# except Exception as e:
#     pass

# --- 글로벌 공지사항 배너 로직 (스타일 2 적용) ---
try:
    frontend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    settings_path = os.path.join(frontend_dir, "utils", "admin_settings.yaml")
    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            g_settings = yaml.safe_load(f) or {}
            if g_settings.get("notice_enabled") and g_settings.get("system_notice"):
                notice_text = g_settings.get("system_notice")
                st.markdown(
                    f"""
                    <style>
                    @keyframes ring-pulse {{
                        0% {{ transform: scale(1); opacity: 1; }}
                        50% {{ transform: scale(1.15); opacity: 0.7; }}
                        100% {{ transform: scale(1); opacity: 1; }}
                    }}
                    </style>
                    <div style="
                        background: rgba(253, 244, 255, 0.8);
                        backdrop-filter: blur(10px);
                        border-left: 4px solid #bb38d0;
                        border-top: 1px solid #fae8ff;
                        border-right: 1px solid #fae8ff;
                        border-bottom: 1px solid #fae8ff;
                        border-radius: 8px;
                        padding: 16px 20px;
                        display: flex;
                        align-items: center;
                        gap: 14px;
                        margin-bottom: 24px;
                        box-shadow: 0 4px 15px rgba(187,56,208,0.06);
                    ">
                        <div style="font-size: 22px; animation: ring-pulse 2s infinite;">👾</div>
                        <div style="color: #111111; font-size: 15px; font-weight: 700; letter-spacing: -0.3px;">
                            <span style="color: #bb38d0; margin-right: 6px;">[Notice]</span>{notice_text}
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
except Exception as e:
    pass


# 쿠키 매니저 및 인증
cookie_manager = stx.CookieManager(key="home_cookie_manager")


def get_cookie_token_with_retry(
    retries: int = 5, delay: float = 0.1
) -> str | None:
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
    cookie_manager.set("access_token", token, secure=False, same_site="lax")
    del st.session_state["new_token"]
else:
    token = get_cookie_token_with_retry()


def force_logout(msg: str):
    st.markdown(f'<div class="alert-warn">{msg}</div>', unsafe_allow_html=True)
    st.session_state.clear()
    try:
        cookie_manager.delete("access_token")
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

# [네비게이션 라우팅 로직] 마이페이지 탭을 누르면 즉시 이동!
if selected == "마이페이지":
    st.switch_page("pages/my_info.py")


# 홈 탭 메인 렌더링
if selected == "홈":
    left_col, _, right_col = st.columns([6.5, 0.2, 3.3])

    # 오른쪽 패널 (프로필 및 액션 카드)
    with right_col:
        # 1-1. 내 프로필 카드
        with st.container(border=True):
            c1, c2 = st.columns([2.5, 7.5])
            with c1:
                avatar_url = (
                    user_profile_image_url
                    or f"https://api.dicebear.com/7.x/avataaars/svg?seed={user_name}"
                )
                st.markdown(
                    f'<img src="{avatar_url}" style="width:60px; height:60px; border-radius:50%; object-fit:cover; border: 2px solid #f1f3f5;">',
                    unsafe_allow_html=True,
                )
            with c2:
                tier_badge_class = (
                    "profile-badge-plus"
                    if user_tier.lower() == "plus"
                    else "profile-badge-normal"
                )
                st.markdown(
                    f'<p class="user-name-title">{user_name} <span class="{tier_badge_class}">{user_tier.upper()}</span></p>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<p class="user-email-text">{user_email}</p>',
                    unsafe_allow_html=True,
                )

            st.markdown(
                "<div style='margin: 15px 0 10px 0; border-bottom: 1px solid #f1f3f5;'></div>",
                unsafe_allow_html=True,
            )

            # # 유저 퀵 액션 버튼들
            # nc1, nc2, nc3 = st.columns(3)
            # nc1.button("이력서", use_container_width=True)
            # nc2.button("내 기록", use_container_width=True)

            # # [버튼 라우팅 로직] 마이페이지 버튼 클릭 시 이동!
            # if nc3.button("마이페이지", use_container_width=True):
            #     st.switch_page("pages/my_info.py")

            st.write("")
            # 로그아웃 버튼 (텍스트 링크 스타일)
            if st.button("로그아웃", use_container_width=True):
                try:
                    cookie_manager.delete("access_token")
                except Exception:
                    pass
                st.session_state.clear()
                time.sleep(0.3)
                st.switch_page("app.py")

        st.write("")

        # 메인 액션 버튼 (AI 면접 시작)
        action_ph = st.empty()
        if st.button("AI 모의 면접 시작", type="primary", use_container_width=True):
            action_ph.markdown(
                '<div class="alert-ok">면접 대기실로 이동합니다! 건투를 빕니다!</div>',
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

    # 왼쪽 패널 (정보 및 추천 탭)
    with left_col:
        st.markdown(
            f"<h3 style='font-size:22px; font-weight:700; color:#111; margin-bottom:20px;'>반가워요, {user_name}님! 오늘 준비되셨나요?</h3>",
            unsafe_allow_html=True,
        )
        tab1, tab2, tab3 = st.tabs(["추천 공고", "백엔드 트렌드", "게시판"])
        user_id = st.session_state.user.get('id')
        
        # 채용공고 탭
        with tab1:
            st.markdown("<br>", unsafe_allow_html=True)

            payload = {
                "startPage": 1,
                "display": 20,
            }
            user_id = user_id or st.session_state.get("user_id")

            if not user_id:
                st.info('정보를 불러오는 중...')
                st.stop()

            try:
                parsed = {}

                resume_cache = f'resume_latest:{user_id}'

                if resume_cache not in st.session_state:
                    st.session_state[resume_cache] = get_latest_resume(user_id=user_id)

                resume = st.session_state.get(resume_cache)

                if resume:                   # 이력서가 존재하면, 관련 직무 공채 출력
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

            # 여기서 실시간 뉴스 함수를 실행!
            render_realtime_ai_news()

            st.markdown(
                "<p style='font-size:11px; color:#aaa; text-align:right; margin-top:20px;'>Powered by Tavily Search Engine</p>",
                unsafe_allow_html=True,
            )

        # 게시판
        with tab3:
            st.markdown("<br>", unsafe_allow_html=True)
            # 2. 대시보드 화면 렌더링 영역 (왼쪽 패널 등 원하는 곳에 호출)
            # 세션에 저장된 유저 이름이 있으면 넘겨주고, 없으면 "익명"을 넘깁니다.
            current_name = st.session_state.get("user", {}).get("name", "익명")

            # 함수 호출로 메모장 위젯 렌더링!
            render_memo_board(current_name)

# ------------------------------

import streamlit as st

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
        /* 👉 [여기를 수정하세요!] 모달창 전체 배경색입니다. */
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
        /* 👉 [여기를 수정하세요!] 실제 말풍선들이 올라가는 대화창 배경색입니다. */
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
       5. 채팅 입력창
    ══════════════════════════════════════════════════════ */
    div[data-testid="stChatInput"] {
        border-radius: 30px !important;
        border: 2px solid #e2e8f0 !important;
        background: #ffffff !important;
        padding: 4px 12px !important;
        box-shadow: 0 10px 30px rgba(0,0,0,0.06) !important;
        margin-top: 15px !important;
        transition: all 0.3s ease !important;
    }
    div[data-testid="stChatInput"]:focus-within {
        border-color: #bb38d0 !important;
        box-shadow: 0 0 0 4px rgba(187,56,208,0.15) !important;
    }
    div[data-testid="stChatInput"] textarea {
        color: #1e293b !important;
        caret-color: #bb38d0 !important;
    }
    div[data-testid="stChatInputSubmitButton"] {
        color: white !important;
        background: #bb38d0 !important;
        border-radius: 50% !important;
        transition: transform 0.2s !important;
    }
    div[data-testid="stChatInputSubmitButton"]:hover {
        transform: scale(1.1) !important;
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
            "content": "안녕하세요! **AIWORK 수석 어드바이저**입니다. ✦\n\n플랫폼 사용법, 취업 트렌드, 직무 고민 등 무엇이든 물어보세요. 실시간 웹 검색으로 2026년 최신 데이터를 기반으로 답변드립니다.",
        }
    ]


# ─── 챗봇 모달 팝업 ───
@st.dialog("🤖 AIWORK 어드바이저", width="large")
def chatbot_modal():
    inject_chatbot_styles()

    st.markdown(
        '<div class="advisor-badge">실시간 Tavily 웹 검색 연동 · 2026 최신 채용 동향 팩트체크</div>',
        unsafe_allow_html=True,
    )

    chat_container = st.container(height=450)

    for chat in st.session_state.guide_chat:
        with chat_container:
            if chat["role"] == "assistant":
                st.markdown(
                    f"""<div style="display:flex; justify-content:flex-start; margin-bottom:16px; gap:12px;">
                        <div style="font-size:32px; line-height:1; margin-top:20px;">🤖</div>
                        <div style="display:flex; flex-direction:column; max-width:85%;">
                            <div class="sender-label">AI 어드바이저</div>
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
                        <div style="font-size:32px; line-height:1; margin-top:20px;">🧑‍💻</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    if prompt := st.chat_input(
        "예: 데이터 엔지니어 요새 전망 어때? / AIWORK는 어떻게 써?"
    ):
        # 1. 사용자 질문을 세션에 저장
        st.session_state.guide_chat.append({"role": "user", "content": prompt})

        with chat_container:
            # 2. 사용자 말풍선 즉시 렌더링
            st.markdown(
                f"""<div style="display:flex; justify-content:flex-end; margin-bottom:16px; gap:12px;">
                    <div style="display:flex; flex-direction:column; align-items:flex-end; max-width:85%;">
                        <div class="sender-label" style="color:#94a3b8!important;">사용자</div>
                        <div class="user-bubble">{prompt}</div>
                    </div>
                    <div style="font-size:32px; line-height:1; margin-top:20px;">🧑‍💻</div>
                </div>""",
                unsafe_allow_html=True,
            )

            # 3. AI 답변 대기 및 생성
            with st.spinner("웹을 탐색하며 트렌드를 분석 중입니다... 🌐"):
                web_info = get_web_context(prompt)
                ai_reply = get_home_guide_response(prompt, web_info)

            # 🚨 [수정 및 추가된 부분] AI 답변을 받아왔으니, 화면에 즉시 말풍선으로 그려줍니다!
            st.markdown(
                f"""<div style="display:flex; justify-content:flex-start; margin-bottom:16px; gap:12px;">
                    <div style="font-size:32px; line-height:1; margin-top:20px;">🤖</div>
                    <div style="display:flex; flex-direction:column; max-width:85%;">
                        <div class="sender-label">AI 어드바이저</div>
                        <div class="ai-bubble">{ai_reply}</div>
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )

        # 4. 세션에 AI 답변 저장 (나중에 모달을 껐다 켜도 대화가 유지되도록)
        st.session_state.guide_chat.append({"role": "assistant", "content": ai_reply})


# 플로팅 챗봇 버튼 (FAB) 랜더링 및 CSS 스나이퍼 타겟팅
st.markdown(
    """
<style>
/* ✨ 다른 UI는 절대 깨지 않으면서 버튼만 우측 하단에 고정하는 CSS */
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
    border-radius: 50px !important;
    background: linear-gradient(135deg, #bb38d0, #8b1faa) !important;
    border: none !important;
    box-shadow: 0 8px 25px rgba(187, 56, 208, 0.4) !important;
    color: transparent !important; /* 'chatbot_trigger_btn' 텍스트를 투명하게 숨김 */
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important;
    padding: 0 !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
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
}
</style>
""",
    unsafe_allow_html=True,
)


st.markdown('<div id="fab-marker"></div>', unsafe_allow_html=True)
if st.button("chatbot_trigger_btn", key="fab_btn"):
    chatbot_modal()
