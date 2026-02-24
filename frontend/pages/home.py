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

# ─── 경로 설정 ─────────────────────────────────────────────────────────
import sys, os, time

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─── streamlit (set_page_config는 반드시 첫 번째 st 호출이어야 함) ──────
import streamlit as st

st.set_page_config(page_title="AIWORK | 대시보드", page_icon="👾", layout="wide")

# ─── 서드파티 ──────────────────────────────────────────────────────────
import extra_streamlit_components as stx
from streamlit_option_menu import option_menu
from utils.api_utils import api_verify_token
import yaml
import os

from api.jobs import search_jobs
from services.jobs_service import build_job_cards_data
from components.job_cards import render_job_cards


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

# --- 글로벌 공지사항 배너 로직 ---
try:
    frontend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    settings_path = os.path.join(frontend_dir, "utils", "admin_settings.yaml")
    if os.path.exists(settings_path):
        with open(settings_path, "r", encoding="utf-8") as f:
            g_settings = yaml.safe_load(f) or {}
            if g_settings.get("notice_enabled") and g_settings.get("system_notice"):
                st.info(f"📢 {g_settings.get('system_notice')}")
except Exception as e:
    pass


# 쿠키 매니저 및 인증
cookie_manager = stx.CookieManager(key="home_cookie_manager")

if "new_token" in st.session_state:
    token = st.session_state.new_token
    cookie_manager.set("access_token", token, secure=False, same_site="lax")
    del st.session_state["new_token"]
else:
    try:
        token = cookie_manager.get("access_token")
    except Exception:
        token = None


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
    if is_valid:
        st.session_state.user = {
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
    if not st.session_state.get("_cookie_retry"):
        st.session_state["_cookie_retry"] = True
        time.sleep(0.4)
        st.rerun()
    else:
        del st.session_state["_cookie_retry"]
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

# 배너
st.image(
    "https://via.placeholder.com/1400x120/1a1a1a/FFFFFF?text=AIWORK+%7C+Next+Generation+AI+Interview+Platform",
    use_container_width=True,
)
st.write("")

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

            # 유저 퀵 액션 버튼들
            nc1, nc2, nc3 = st.columns(3)
            nc1.button("📄 이력서", use_container_width=True)
            nc2.button("📊 내 기록", use_container_width=True)

            # [버튼 라우팅 로직] 마이페이지 버튼 클릭 시 이동!
            if nc3.button("⚙️ 마이페이지", use_container_width=True):
                st.switch_page("pages/my_info.py")

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
        if st.button("✨ AI 모의 면접 시작", type="primary", use_container_width=True):
            action_ph.markdown(
                '<div class="alert-ok">✨ 면접 대기실로 이동합니다! 건투를 빕니다!</div>',
                unsafe_allow_html=True,
            )
            time.sleep(1)
            st.switch_page("pages/interview.py")

        st.write("")

        # 안내 카드
        with st.container(border=True):
            st.markdown(
                "<p style='font-size:14px; font-weight:700; color:#111; margin-bottom:5px;'>🔗 Github Repository</p>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<p style='font-size:13px; color:#888; margin:0;'>SKN23-3rd-1TEAM 프로젝트 주소</p>",
                unsafe_allow_html=True,
            )

    # 왼쪽 패널 (정보 및 추천 탭)
    with left_col:
        st.markdown(
            f"<h3 style='font-size:22px; font-weight:700; color:#111; margin-bottom:20px;'>👋 반가워요, {user_name}님! 오늘 준비되셨나요?</h3>",
            unsafe_allow_html=True,
        )
        tab1, tab2, tab3 = st.tabs(
            ["📋 추천 공고", "📈 백엔드 트렌드", "💡 AI 면접 Tips"]
        )

        with tab1:
            st.markdown("<br>", unsafe_allow_html=True)

            payload = {
                "startPage": 1,
                "display": 20,
            }

            try:
                data = search_jobs(payload)
                cards = build_job_cards_data(data)
                with st.container(height=360):
                    render_job_cards(cards)

            except Exception as e:
                st.error(f"채용공고 조회 실패: {e}")
            for company, role, desc in [
                (
                    "네이버 (NAVER)",
                    "Python 백엔드 신입/경력",
                    "FastAPI와 MSA 환경에서 대규모 트래픽을 처리할 개발자를 모십니다.",
                ),
                (
                    "카카오 (Kakao)",
                    "AI 엔지니어 인턴",
                    "LLM 기반 서비스를 개발할 AI 엔지니어를 모집합니다.",
                ),
                (
                    "라인 (LINE)",
                    "백엔드 개발자 (신입)",
                    "글로벌 메신저 플랫폼의 백엔드 시스템을 함께 만들어갈 분을 찾습니다.",
                ),
            ]:
                with st.container(border=True):
                    a, b = st.columns([8, 2])
                    with a:
                        st.markdown(
                            f"<p style='font-size:16px; font-weight:700; margin-bottom:4px; color:#111;'>{company} — {role}</p>",
                            unsafe_allow_html=True,
                        )
                        st.markdown(
                            f"<p style='font-size:14px; color:#666; margin:0;'>{desc}</p>",
                            unsafe_allow_html=True,
                        )
                    with b:
                        st.markdown(
                            "<div style='margin-top:10px;'></div>",
                            unsafe_allow_html=True,
                        )
                        st.button(
                            "지원하기", key=f"apply_{company}", use_container_width=True
                        )

        with tab2:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                '<div class="alert-info">💡 오늘의 기술 블로그 및 아티클이 노출되는 영역입니다.</div>',
                unsafe_allow_html=True,
            )
            for title, desc in [
                (
                    "FastAPI vs Django: 2026 트렌드 비교",
                    "비동기 처리와 타입 힌트를 중심으로 두 프레임워크를 심층 비교합니다.",
                ),
                (
                    "LLM 서빙 최적화: vLLM과 TensorRT-LLM",
                    "대규모 언어 모델을 프로덕션에서 효율적으로 서빙하는 방법을 알아봅니다.",
                ),
            ]:
                with st.container(border=True):
                    st.markdown(
                        f"<p style='font-size:15px; font-weight:700; margin-bottom:4px; color:#111;'>{title}</p>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<p style='font-size:13px; color:#666; margin:0;'>{desc}</p>",
                        unsafe_allow_html=True,
                    )

        with tab3:
            st.markdown("<br>", unsafe_allow_html=True)
            st.markdown(
                '<div class="alert-info">💡 최신 AI 면접 합격 후기 및 팁 게시판 영역입니다.</div>',
                unsafe_allow_html=True,
            )
            for tip, desc in [
                (
                    "STAR 기법으로 답변하기",
                    "Situation → Task → Action → Result 구조로 경험을 구체적으로 설명하세요.",
                ),
                (
                    "기술 면접 단골 질문 TOP 5",
                    "시간복잡도, DB 인덱스, REST API, 동시성, 캐싱 전략을 꼭 준비하세요.",
                ),
            ]:
                with st.container(border=True):
                    st.markdown(
                        f"<p style='font-size:15px; font-weight:700; margin-bottom:4px; color:#111;'>💬 {tip}</p>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<p style='font-size:13px; color:#666; margin:0;'>{desc}</p>",
                        unsafe_allow_html=True,
                    )

elif selected == "AI 면접":
    st.markdown("## 🤖 AI 모의면접")
    st.info("면접 대기실 기능은 준비 중입니다.")

elif selected == "내 기록":
    st.markdown("## 📋 내 면접 기록")
    st.info("면접 기록 기능은 준비 중입니다.")
