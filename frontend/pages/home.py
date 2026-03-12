"""
File: home.py
Author: 김지우
Created: 2026-02-20
Description: 메인 화면 (프리미엄 대시보드 UI 및 에이전트 연동)

Modification History:
- 2026-02-21 (김지우): JWT 해독 로직 백엔드 이관
- 2026-02-22 (김지우): stx.CookieManager 타이밍 문제 해결, 쿠키 retry 로직 추가
- 2026-02-23 (양창일): user_profile_image_url 추가
- 2026-02-23 (김지우): UI 적용 및 마이페이지(my_info) 라우팅 연결, 프로필 기능 추가
- 2026-02-24 (유헌상): 채용공고 APi 호출 및 연결
- 2026-02-28 (김지우): require_login 중앙화 및 유령 버튼 투명화 버그 픽스
- 2026-03-10 (김지우): 자비스 에이전트(Zero-Click Navigation) 챗봇 UI 통합 및 컴포넌트 분리
"""

import streamlit as st
import time
import sys, os
import requests 

# 경로 설정
current_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.dirname(current_dir)
root_dir = os.path.dirname(frontend_dir)
backend_dir = os.path.join(root_dir, "backend")

if root_dir not in sys.path:
    sys.path.append(root_dir)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# 서드파티 및 모듈
import streamlit.components.v1 as components
from utils.function import inject_custom_header, require_login, render_memo_board
from utils.home_api_render import render_memo_board, render_realtime_ai_news
from streamlit_option_menu import option_menu
from utils.api_utils import api_get_home_guide
from api.jobs import search_jobs, get_latest_resume
from services.jobs_service import build_job_cards_data
from components.job_cards import render_job_cards

# 챗봇 컴포넌트 임포트
from components.chatbot_modal import render_fab_button

st.set_page_config(page_title="AIWORK", page_icon="👾", layout="wide")

user_id = require_login()

from urllib.parse import urlencode

inject_custom_header()

# 유저 정보 바인딩
user_info = st.session_state.user or {}
user_name = user_info.get("name", "사용자")
user_role = user_info.get("role", "user")
user_email = user_info.get("email", "이메일 정보 없음")
user_tier = user_info.get("tier", "normal")
user_profile_image_url = user_info.get("profile_image_url")


def get_web_context_first(query):
    return "__USE_WEB_SEARCH__"


def get_home_guide_response_stream(user_message, web_context):
    use_web_search = web_context == "__USE_WEB_SEARCH__"
    success, result = api_get_home_guide(user_message, use_web_search=use_web_search)
    if success:
        yield result.get("content", "")
    else:
        yield str(result)


# CSS
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700&display=swap');
:root { color-scheme: light !important; }
* { font-family: 'Pretendard', sans-serif; color: #111 !important; }
p, span, div, a, label, h1, h2, h3, h4, h5, h6, li, td, th, small, strong, b, i, em, caption { color: #111 !important; }
.subtext { color: #666 !important; }
.stApp, html, body { background-color: #f5f5f5 !important; background-image: none !important; color-scheme: light !important; color: #111 !important; }

[data-testid="stAppViewContainer"] { background-color: #f5f7f9 !important; color-scheme: light !important; }
[data-testid="stAppViewContainer"] > .main { background-color: #f5f7f9 !important; }
[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer, header { visibility:hidden; background:transparent; color-scheme: light !important; }

/* Streamlit 내부 컴포넌트 다크모드 완전 차단 */
[data-testid="stVerticalBlock"],
[data-testid="stHorizontalBlock"],
[data-testid="stColumn"],
[data-testid="stForm"],
[data-testid="stExpander"],
[data-testid="stExpanderContent"],
[data-testid="stMarkdownContainer"],
[role="tabpanel"],
[data-baseweb="tab-panel"],
[data-baseweb="tab-list"],
[data-baseweb="tab"],
[data-testid="stRadio"],
[data-testid="stRadio"] > div,
[data-testid="stSelectbox"],
[data-testid="stSelectbox"] > div,
[data-testid="stMultiSelect"],
[data-testid="stTextArea"],
[data-testid="stSlider"],
[data-testid="stCheckbox"],
[data-testid="stMetric"],
[data-testid="stDataFrame"],
[data-testid="stTable"],
[data-testid="stAlert"] { color: #111 !important; }

/* Dialog / Modal */
[data-testid="stDialog"] > div > div,
[data-testid="stDialog"] [data-testid="stVerticalBlockBorderWrapper"],
[data-testid="stDialog"] [data-testid="stVerticalBlock"],
section[data-testid="stDialog"] { background-color: #ffffff !important; color: #111 !important; }

/* Baseweb 입력/선택 컴포넌트 */
[data-baseweb="input"],
[data-baseweb="input"] > div,
[data-baseweb="select"],
[data-baseweb="select"] > div,
[data-baseweb="textarea"],
[data-baseweb="popover"] > div,
[data-baseweb="menu"],
[data-baseweb="menu"] li { background-color: #ffffff !important; color: #111 !important; }
[data-baseweb="radio"] > div > div > div { color: #111 !important; }

/* 모든 Streamlit 버튼 배경 강제 */
[data-testid="stButton"] > button,
[data-testid="stLinkButton"] > a,
[data-testid="stFormSubmitButton"] > button {
    background-color: #ffffff !important; color: #111 !important;
    border: 1px solid #ddd !important;
}
[data-testid="stButton"] > button p,
[data-testid="stLinkButton"] > a p,
[data-testid="stFormSubmitButton"] > button p { color: #111 !important; }
button[kind="primary"], [data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #bb38d0 0%, #872a96 100%) !important;
    border: none !important; color: white !important;
}
button[kind="primary"] p, button[kind="primary"] span,
[data-testid="stButton"] > button[kind="primary"] p { color: #fff !important; }

/* 테이블/데이터프레임 배경 강제 */
[data-testid="stDataFrame"],
[data-testid="stDataFrame"] > div,
[data-testid="stDataFrame"] iframe,
[data-testid="stTable"],
[data-testid="stTable"] table,
[data-testid="stTable"] th,
[data-testid="stTable"] td { background-color: #ffffff !important; color: #111 !important; }

/* 컨테이너(border=True) 내부 배경 강제 */
[data-testid="stVerticalBlockBorderWrapper"] > div,
[data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] { background-color: transparent !important; }

/* 탭 패널 배경 */
[role="tabpanel"], [data-baseweb="tab-panel"] { background-color: transparent !important; }

/* Toggle/Checkbox */
[data-testid="stCheckbox"] label span,
[data-testid="stToggle"] label span { color: #111 !important; }
.block-container { padding-top: 2rem !important; max-width: 1200px !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important; padding-bottom: 1rem !important; }

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

button[kind="primary"] {
    background: linear-gradient(135deg, #bb38d0 0%, #872a96 100%) !important;
    border: none !important; color: white !important; font-weight: 700 !important;
    border-radius: 12px !important; height: 50px !important; transition: all 0.2s;
}
button[kind="primary"]:hover { filter: brightness(1.1); transform: scale(0.99); }

.alert-warn    { background:#fff4f4; color:#e74c3c; border-left:4px solid #e74c3c; padding:16px; border-radius:8px; font-size:14px; font-weight:600; margin-bottom:20px; box-shadow: 0 2px 10px rgba(231,76,60,0.1); }
.alert-ok      { background:#fdf4ff; color:#bb38d0; border-left:4px solid #bb38d0; padding:16px; border-radius:8px; font-size:14px; font-weight:700; margin-bottom:20px; box-shadow: 0 2px 10px rgba(187,56,208,0.1); }
.alert-info    { background:#f0f7ff; color:#2980b9; border-left:4px solid #3498db; padding:14px 18px; border-radius:6px; font-size:14px; font-weight:500; margin-bottom:16px; }

[data-testid="stTabs"] button { font-family: 'Pretendard', sans-serif !important; font-size: 16px !important; font-weight: 600 !important; color: #666 !important; }
[data-testid="stTabs"] button[aria-selected="true"] { color: #bb38d0 !important; border-bottom-color: #bb38d0 !important; }
div[data-baseweb="tab-highlight"] { background-color: #bb38d0 !important; }
[data-testid="stImage"] img { border-radius: 16px; box-shadow: 0 4px 15px rgba(0,0,0,0.05); }

div[data-testid="stElementContainer"]:has(#logout-marker),
div[data-testid="stElementContainer"]:has(#logout-marker) + div[data-testid="stElementContainer"] {
    position: absolute !important; width: 0px !important; height: 0px !important;
    opacity: 0 !important; overflow: hidden !important; z-index: -9999 !important; pointer-events: none !important;
    margin: 0 !important; padding: 0 !important;
}

div[data-testid="stElementContainer"]:has(#fab-marker) + div[data-testid="stElementContainer"] {
    position: fixed !important; bottom: 40px !important; right: 40px !important; z-index: 99999 !important;
    width: 70px !important; height: 70px !important;
}
div[data-testid="stElementContainer"]:has(#fab-marker) + div[data-testid="stElementContainer"] button {
    width: 100% !important; height: 100% !important; min-width: 70px !important; min-height: 70px !important;
    border-radius: 50px !important; background: linear-gradient(135deg, #bb38d0, #872a96) !important;
    border: none !important; box-shadow: 0 8px 25px rgba(187, 56, 208, 0.4) !important;
    color: transparent !important; font-size: 0 !important; line-height: 0 !important; text-indent: -9999px !important;
    transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1) !important; padding: 0 !important; display: flex !important;
    align-items: center !important; justify-content: center !important; overflow: hidden !important; position: relative !important;
}
div[data-testid="stElementContainer"]:has(#fab-marker) + div[data-testid="stElementContainer"] button:hover {
    transform: scale(1.1) translateY(-5px) !important; box-shadow: 0 12px 30px rgba(187, 56, 208, 0.6) !important;
}
div[data-testid="stElementContainer"]:has(#fab-marker) + div[data-testid="stElementContainer"] button::after {
    content: "👾" !important; font-size: 32px !important; color: white !important; position: absolute !important; inset: 0 !important; display: flex !important; align-items: center !important; justify-content: center !important; line-height: 1 !important; text-indent: 0 !important; z-index: 1 !important; pointer-events: none !important;
}
@media (max-width: 768px) {
    .block-container { padding: 1rem 0.75rem !important; }
    [data-testid="stVerticalBlockBorderWrapper"] { padding: 1rem !important; }
    div[data-testid="stElementContainer"]:has(#fab-marker) + div[data-testid="stElementContainer"] { bottom: 20px !important; right: 20px !important; width: 56px !important; height: 56px !important; }
    div[data-testid="stElementContainer"]:has(#fab-marker) + div[data-testid="stElementContainer"] button { min-width: 56px !important; min-height: 56px !important; }
    div[data-testid="stElementContainer"]:has(#fab-marker) + div[data-testid="stElementContainer"] button::after { font-size: 26px !important; }
}
</style>
""",
    unsafe_allow_html=True,
)


def render_profile_card(user_name, user_email, user_tier, user_profile_image_url=None):
    avatar_url = (
        user_profile_image_url
        or f"https://api.dicebear.com/7.x/avataaars/svg?seed={user_name}"
    )
    tier_badge_class = (
        "profile-badge-plus" if user_tier.lower() == "plus" else "profile-badge-normal"
    )

    st.markdown(
        f"""
    <style>
    .profile-card-wrap {{ background: #ffffff; border-radius: 16px; border: 1px solid #f1f3f5; box-shadow: 0 4px 24px rgba(0, 0, 0, 0.04); padding: 20px 18px 0 18px; overflow: hidden; margin-bottom: 20px; }}
    .profile-top-row {{ display: flex; align-items: center; gap: 14px; margin-bottom: 12px; }}
    .profile-avatar-wrap {{ position: relative; flex-shrink: 0; }}
    .profile-avatar {{ width: 62px; height: 62px; border-radius: 50%; object-fit: cover; border: 2.5px solid #ffffff; box-shadow: 0 0 0 2.5px #bb38d0, 0 4px 12px rgba(187,56,208,0.25); }}
    .profile-avatar-dot {{ position: absolute; bottom: 2px; right: 2px; width: 13px; height: 13px; background: #22c55e; border-radius: 50%; border: 2px solid #fff; box-shadow: 0 0 6px rgba(34,197,94,0.5); }}
    .profile-info {{ flex: 1; min-width: 0; }}
    .profile-name-row {{ display: flex; align-items: center; gap: 7px; margin-bottom: 3px; }}
    .profile-name {{ font-size: 16px; font-weight: 700; color: #111; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .profile-badge-plus {{ display: inline-flex; align-items: center; gap: 3px; background: linear-gradient(135deg, #bb38d0, #872a96); color: #fff; font-size: 10px; font-weight: 700; padding: 2px 8px; border-radius: 20px; letter-spacing: 0.04em; text-transform: uppercase; box-shadow: 0 2px 8px rgba(187,56,208,0.3); }}
    .profile-badge-normal {{ display: inline-flex; align-items: center; background: #e9ecef; color: #6c757d; font-size: 10px; font-weight: 600; padding: 2px 8px; border-radius: 20px; text-transform: uppercase; }}
    .profile-email {{ font-size: 12px; color: #888; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .profile-logout-btn {{ flex-shrink: 0; display: inline-flex; align-items: center; gap: 5px; background: #fdf4ff; color: #bb38d0; border: 1px solid #fae8ff; border-radius: 12px; padding: 7px 13px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.2s ease; cursor: pointer; text-decoration: none !important;  }}
    .profile-logout-btn:hover {{ background: #bb38d0; color: #fff; border-color: #bb38d0; box-shadow: 0 4px 12px rgba(187,56,208,0.3); transform: translateY(-1px); }}
    .profile-divider {{ height: 1px; background: #f1f3f5; margin: 12px 0 0 0; }}
    .profile-quick-menu {{ display: flex; align-items: stretch; margin: 0 -18px; }}
    a.profile-quick-item {{ flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 16px 4px; font-size: 13px; font-weight: 600; color: #495057 !important; cursor: pointer; transition: all 0.2s ease; border-right: 1px solid #f8f9fa; background: #faf9ff; text-decoration: none !important; }}
    a.profile-quick-item:last-child {{ border-right: none; }}
    a.profile-quick-item:hover {{ background: #fdf4ff; color: #bb38d0 !important; text-decoration: none !important; }}
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
            <a class="profile-logout-btn" href="/login?logout=true" target="_self">로그아웃</a>
        </div>
        <div class="profile-divider"></div>
        <div class="profile-quick-menu">
            <a class="profile-quick-item" href="/resume" target="_self">이력서</a>
            <a class="profile-quick-item" href="/mypage" target="_self">내 기록</a>
            <a class="profile-quick-item" href="/my_info" target="_self">내 정보</a>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )


st.markdown(
    """
<style>
.block-container {{
    padding-top: 100px !important;
}}
</style>
""",
    unsafe_allow_html=True,
)


import base64

try:
    with open("assets/search.png", "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode()
    search_icon_base64 = f"data:image/png;base64,{encoded_string}"
except FileNotFoundError:
    search_icon_base64 = ""

st.markdown(
    f"""
<style>
.search-wrapper {{
    position: relative; width: 100%; margin: 10px auto 30px; z-index: 9999;
}}
.search-box {{
    display: flex; align-items: center; width: 100%; height: 56px;
    border: 2.5px solid #bb38d0; border-radius: 28px; padding: 0 20px 0 24px;
    background: #fff; box-shadow: 0 4px 15px rgba(187, 56, 208, 0.08);
    position: relative; z-index: 101; transition: all 0.2s ease;
}}
.search-wrapper:focus-within .search-box {{
    border-bottom-left-radius: 0px; border-bottom-right-radius: 0px;
    border-bottom-color: #f8f9fa; box-shadow: none;
}}
.search-logo {{ font-size: 22px; font-weight: 900; color: #bb38d0; margin-right: 12px; letter-spacing: -0.5px; }}
.search-select {{ border: none; outline: none; background: transparent; font-size: 14px; font-weight: 700; color: #bb38d0; cursor: pointer; margin-right: 10px; padding-right: 5px; border-right: 2px solid #fae8ff; }}
.search-input {{ flex: 1; border: none; outline: none; font-size: 16px; font-weight: 500; color: #111; background: transparent; padding-top: 2px; padding-left: 10px; }}
.search-input::placeholder {{ color: #adb5bd; }}
.search-btn {{ background: transparent; border: none; font-size: 22px; cursor: pointer; color: #bb38d0; padding: 0; margin-left: 10px; transition: transform 0.2s; display: flex; align-items: center; justify-content: center; }}
.search-btn:hover {{ transform: scale(1.15); }}
.search-btn img {{ width: 22px; height: 22px; object-fit: contain; }}
.search-dropdown {{
    position: absolute; top: 54px; left: 0; width: 100%; 
    background: #fff; border: 2.5px solid #bb38d0; border-top: none;
    border-radius: 0 0 24px 24px; box-shadow: 0 15px 30px rgba(187, 56, 208, 0.15);
    padding: 10px 0 16px 0; z-index: 100;
    opacity: 0; visibility: hidden; transform: translateY(-10px);
    transition: all 0.25s cubic-bezier(0.2, 0.8, 0.2, 1);
}}
.search-wrapper:focus-within .search-dropdown {{ opacity: 1; visibility: visible; transform: translateY(0); }}
.dropdown-header {{ font-size: 12px; font-weight: 700; color: #888; padding: 10px 24px 8px; border-bottom: 1px solid #f1f3f5; margin-bottom: 8px; }}
.dropdown-item {{ display: flex; align-items: center; padding: 10px 24px; text-decoration: none !important; color: #111; font-size: 15px; font-weight: 500; transition: background 0.1s; cursor: pointer; }}
.dropdown-item:hover {{ background: #fdf4ff; color: #bb38d0; }}
.dropdown-icon {{ display: flex; align-items: center; justify-content: center; width: 24px; height: 24px; border-radius: 50%; background: #f8f9fa; margin-right: 12px; font-size: 12px; color: #adb5bd; }}
.dropdown-item:hover .dropdown-icon {{ background: #fae8ff; color: #bb38d0; }}
.dropdown-url {{ margin-left: auto; font-size: 12px; color: #adb5bd; font-weight: 400; }}
</style>
<div class="search-wrapper">
    <div class="search-box">
        <div class="search-logo">A</div>
        <select id="search-engine" class="search-select">
            <option value="saramin">사람인 공고</option>
            <option value="jobkorea">잡코리아 공고</option>
            <option value="worknet">워크넷 공고</option>
        </select>
        <input type="text" id="job-keyword" class="search-input" 
               placeholder="무엇이든 검색해보세요!" 
               autocomplete="off">        
        <button class="search-btn" id="search-action-btn">
            <img src="{search_icon_base64}" alt="검색">
        </button>
    </div>
    <div class="search-dropdown">
        <div class="dropdown-header">빠른 포털 이동</div>
        <a href="https://www.saramin.co.kr" target="_blank" class="dropdown-item">
            <div class="dropdown-icon">🕒</div>사람인 (Saramin) 홈
            <span class="dropdown-url">saramin.co.kr ↗</span>
        </a>
        <a href="https://www.jobkorea.co.kr" target="_blank" class="dropdown-item">
            <div class="dropdown-icon">🕒</div>잡코리아 (JobKorea) 홈
            <span class="dropdown-url">jobkorea.co.kr ↗</span>
        </a>
        <a href="https://www.work.go.kr" target="_blank" class="dropdown-item">
            <div class="dropdown-icon">🕒</div>고용노동부 워크넷 홈
            <span class="dropdown-url">work.go.kr ↗</span>
        </a>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

components.html(
    """
<script>
function attachSearchEvents() {
    const doc = window.parent.document;
    const inputEl = doc.getElementById('job-keyword');
    const btnEl = doc.getElementById('search-action-btn');
    const engineEl = doc.getElementById('search-engine');
    if (!inputEl || !btnEl || !engineEl) {
        setTimeout(attachSearchEvents, 100);
        return;
    }
    
    // 이미 이벤트가 바인딩된 경우 중복 바인딩 방지
    if (inputEl.dataset.initialized === "true") {
        return;
    }
    inputEl.dataset.initialized = "true";

    function executeSearch() {
        const kw = inputEl.value.trim();
        const engine = engineEl.value;
        if (kw !== '') {
            let url = '';
            if (engine === 'saramin') url = 'https://www.saramin.co.kr/zf_user/search?searchword=' + encodeURIComponent(kw);
            else if (engine === 'jobkorea') url = 'https://www.jobkorea.co.kr/Search/?stext=' + encodeURIComponent(kw);
            else if (engine === 'worknet') url = 'https://www.work.go.kr/empInfo/empInfoSrch/list/dtlEmpSrchList.do?keyword=' + encodeURIComponent(kw); 
            window.parent.open(url, '_blank');
        } else {
            inputEl.focus();
        }
    }
    btnEl.onclick = function(e) {
        e.preventDefault();
        executeSearch();
    };
    inputEl.onkeydown = function(e) {
        if (e.key === 'Enter' || e.keyCode === 13) {
            e.preventDefault();       
            e.stopPropagation();    
            executeSearch();
        }
    };
}
attachSearchEvents();
</script>
""",
    height=0,
    width=0,
)

left_col, _, right_col = st.columns([6.5, 0.2, 3.3])

# 오른쪽 패널
with right_col:
    render_profile_card(user_name, user_email, user_tier, user_profile_image_url)

    action_ph = st.empty()
    if st.button("AI 모의 면접 시작", type="primary", use_container_width=True):
        action_ph.markdown(
            '<div class="alert-ok">면접 대기실로 이동합니다!</div>',
            unsafe_allow_html=True,
        )
        time.sleep(1)
        st.switch_page("pages/interview.py")

    if user_role == "admin":
        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        if st.button("관리자 대시보드", use_container_width=True):
            st.switch_page("pages/admin.py")

    st.write("")

    with st.container(border=True):
        st.markdown(
            """
            <a href="https://github.com/SKNETWORKS-FAMILY-AICAMP/SKN23-3rd-1TEAM.git" target="_blank" style="text-decoration: none; display: block;">
                <p style='font-size:14px; font-weight:700; color:#111; margin-bottom:5px;'>🔗 Github Repository</p>
                <p style='font-size:13px; color:#888; margin:0;'>SKN23-3rd-1TEAM 프로젝트 주소</p>
            </a>
            <div style="font-size: 24px; font-weight: 800; background: linear-gradient(135deg, #bb38d0 0%, #872a96 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; display: inline-block; letter-spacing: -0.5px; margin-bottom: 10px;">
                SKN23-3rd-1TEAM
            </div>
            """,
            unsafe_allow_html=True,
        )

    try:
        import base64

        def get_b64(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()

        ad_image_path = os.path.join(frontend_dir, "assets", "saja.png")
        ad_img_b64 = f"data:image/png;base64,{get_b64(ad_image_path)}"
    except:
        ad_img_b64 = ""

    single_ad_banner_html = f"""
    <style>
        .banner-link {{
            display: inline-block;
            text-decoration: none;
            width: 380px; 
        }}
        
        .banner-container {{
            position: relative; 
            width: 100%; 
            border-radius: 16px; 
            overflow: hidden; 
            margin-bottom: 24px; 
            box-shadow: 0 10px 40px rgba(187, 56, 208, 0.08);
            border: 2px solid #fae8ff; 
            
            height: 355px; 
            cursor: pointer;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        
        .banner-container:hover {{
            transform: translateY(-4px);
            box-shadow: 0 15px 45px rgba(187, 56, 208, 0.15);
        }}
        
        .banner-img {{
            width: 100%;
            height: 100%;
            object-fit: cover; 
            display: block;
        }}
    </style>

    <a href="https://discord.com/oauth2/authorize?client_id=1465155158022426675&permissions=4279296&integration_type=0&scope=bot" target="_blank" class="banner-link">
        <div class="banner-container">
            <img src="{ad_img_b64}" class="banner-img" alt="사자개 광고">
        </div>
    </a>
    """

    st.markdown(single_ad_banner_html, unsafe_allow_html=True)


# 왼쪽 패널
with left_col:
    try:
        import base64

        def get_b64(path):
            with open(path, "rb") as f:
                return base64.b64encode(f.read()).decode()

        ad_image_path = os.path.join(frontend_dir, "assets", "AD.png")
        img1 = f"data:image/png;base64,{get_b64(ad_image_path)}"
        img2 = img1
    except:
        img1 = img2 = ""

    slider_html = f"""
<div id="custom-slider-block">
<style>
.slider-container {{ position: relative; width: 100%; border-radius: 16px; overflow: hidden; margin-bottom: 24px; box-shadow: 0 4px 20px rgba(0,0,0,0.08); }}
.slides {{ display: flex; transition: transform 0.5s ease-in-out; width: 200%; }}
.slide {{ width: 50%; flex-shrink: 0; cursor: pointer; }}
.slide img {{ width: 100%; display: block; }}
.nav-btn {{ position: absolute; top: 50%; transform: translateY(-50%); background: rgba(255,255,255,0.8); border: 1px solid #eee; border-radius: 50%; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; cursor: pointer; z-index: 10; font-weight: bold; color: #666; box-shadow: 0 2px 5px rgba(0,0,0,0.1); transition: all 0.2s; }}
.nav-btn:hover {{ background: #fff; color: #bb38d0; transform: translateY(-50%) scale(1.1); }}
.prev {{ left: 10px; }}
.next {{ right: 10px; }}
.page-counter {{ position: absolute; bottom: 10px; right: 15px; background: rgba(0,0,0,0.5); color: white; padding: 2px 10px; border-radius: 20px; font-size: 11px; font-weight: 600; margin: 0; }}
</style>
<div class="slider-container">
<div class="nav-btn prev" onclick="moveSlide(-1)"> &lt; </div>
<div class="nav-btn next" onclick="moveSlide(1)"> &gt; </div>
<div class="page-counter" id="p-count">1 / 2</div>
<div class="slides" id="slide-track">
<div class="slide" onclick="window.parent.location.href='/interview'"><img src="{img1}"></div>
<div class="slide" onclick="window.parent.location.href='/resume'"><img src="{img2}"></div>
</div>
</div>
<script>
let currentIdx = 0;
const track = document.getElementById('slide-track');
const count = document.getElementById('p-count');
function moveSlide(dir) {{
currentIdx = (currentIdx + dir + 2) % 2;
track.style.transform = `translateX(-${{currentIdx * 50}}%)`;
count.innerText = `${{currentIdx + 1}} / 2`;
}}
setInterval(() => moveSlide(1), 5000);
</script>
</div>
"""
    st.markdown(slider_html, unsafe_allow_html=True)

    st.markdown(
        """
<style>
div[data-testid="stTabs"] { margin-top: 24px !important; background-color: #fcfcfc !important; border: none !important; border-radius: 16px !important; padding: 16px 20px 24px 20px !important; box-shadow: 0 10px 30px rgba(0, 0, 0, 0.08) !important; }
div[data-testid="stTabs"] > div[data-baseweb="tab-list"] { border-bottom: 2px solid #e1e4e8 !important; gap: 24px !important; padding: 0 4px !important; background: transparent !important; }
div[data-testid="stTabs"] > div[data-baseweb="tab-list"] button { background: transparent !important; border: none !important; padding: 12px 6px 16px 6px !important; font-size: 17px !important; font-weight: 600 !important; color: #8b95a1 !important; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Pretendard", sans-serif !important; position: relative !important; transition: color 0.2s ease !important; }
div[data-testid="stTabs"] > div[data-baseweb="tab-list"] button:hover { color: #4e5968 !important; }
div[data-testid="stTabs"] > div[data-baseweb="tab-list"] button[aria-selected="true"] { color: #191f28 !important; font-weight: 800 !important; }
div[data-testid="stTabs"] > div[data-baseweb="tab-list"] button[aria-selected="true"]::after { content: '' !important; position: absolute !important; bottom: -2px !important; left: 0 !important; width: 100% !important; height: 3px !important; background: linear-gradient(90deg, #bb38d0, #9f24b5) !important; border-radius: 3px 3px 0 0 !important; z-index: 2 !important; }
div[data-testid="stTabs"] > div[role="tabpanel"], div[data-testid="stTabs"] div[data-testid="stVerticalBlockBorderWrapper"] { padding: 24px 0 0 0 !important; border: none !important; box-shadow: none !important; background: transparent !important; }
</style>
""",
        unsafe_allow_html=True,
    )

    resume = None
    job_role = None

    if user_id:
        resume_cache = f"resume_latest:{user_id}"
        if resume_cache not in st.session_state:
            st.session_state[resume_cache] = get_latest_resume(user_id=user_id)

        resume = st.session_state.get(resume_cache) or {}
        job_role = resume.get("job_role")

    if job_role:
        tab1, tab2, tab3 = st.tabs(["추천 공고", f"{job_role} 트렌드", "게시판"])
    else:
        tab1, tab2, tab3 = st.tabs(["채용공고", "백엔드 트렌드", "게시판"])

    # 채용공고 탭
    with tab1:
        st.markdown("<br>", unsafe_allow_html=True)
        payload = {"startPage": 1, "display": 20}
        if not user_id:
            st.info("정보를 불러오는 중...")
        else:
            try:
                parsed = {}
                resume_cache = f"resume_latest:{user_id}"

                if resume:
                    job_role = resume.get("job_role")
                    analysis_result = resume.get("analysis_result")
                    if job_role and analysis_result:
                        parsed = {
                            "job_role": job_role,
                            "keywords": analysis_result.get("keywords", ""),
                        }

                payload.update({k: v for k, v in parsed.items() if v is not None})
                data = search_jobs(payload)
                cards = build_job_cards_data(data)
                with st.container(height=410):
                    render_job_cards(cards)

            except Exception as e:
                st.error(f"채용공고 조회 실패: {e}")

    # 백엔드 트렌드 탭
    with tab2:
        st.markdown("<br>", unsafe_allow_html=True)
        render_realtime_ai_news(job_role)
        st.markdown(
            "<p style='font-size:11px; color:#aaa; text-align:right; margin-top:20px;'>Powered by Tavily Search Engine</p>",
            unsafe_allow_html=True,
        )

    # 게시판 탭
    with tab3:
        st.markdown("<br>", unsafe_allow_html=True)
        render_memo_board(user_name)

# 분리된 컴포넌트 호출 (파일 가장 마지막)
render_fab_button()