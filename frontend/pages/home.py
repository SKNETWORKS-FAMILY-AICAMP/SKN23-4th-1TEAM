"""
File: home.py
Author: 김지우
Created: 2026-02-20
Description: 메인 화면

Modification History:
- 2026-02-21 (김지우): JWT 해독 로직 백엔드 이관
- 2026-02-22 (김지우): stx.CookieManager 타이밍 문제 해결, 쿠키 retry 로직 추가
- 2026-02-23 (양창일): user_profile_image_url 추가
"""

# ─── 1. 경로 설정 ─────────────────────────────────────────────────────────
import sys, os, time
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# ─── 2. Streamlit (set_page_config는 반드시 첫 번째 st 호출이어야 함) ──────
import streamlit as st
st.set_page_config(page_title="AIWORK", page_icon="👾", layout="wide")

# ─── 3. 서드파티 ──────────────────────────────────────────────────────────
import extra_streamlit_components as stx
from streamlit_option_menu import option_menu
from utils.api_utils import api_verify_token

# ==========================================
# 🎨 CSS
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');
* { font-family: 'Noto Sans KR', sans-serif; }
.alert-warn    { background:rgba(231,76,60,.08);  color:#e74c3c; border:1px solid rgba(231,76,60,.2);   padding:16px; border-radius:8px; text-align:center; font-size:15px; font-weight:600; margin-bottom:20px; }
.alert-ok      { background:rgba(187,56,208,.08); color:#bb38d0; border:1px solid rgba(187,56,208,.2);  padding:16px; border-radius:8px; text-align:center; font-size:15px; font-weight:700; margin-bottom:20px; }
.alert-info    { background:rgba(52,152,219,.05); color:#2980b9; border-left:4px solid #3498db; padding:14px 18px; border-radius:6px; font-size:14px; font-weight:500; margin-bottom:16px; }
[data-testid="stHeader"], #MainMenu, footer, header { visibility:hidden; background:transparent; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 🍪 쿠키 매니저
# ==========================================
cookie_manager = stx.CookieManager(key="home_cookie_manager")

if "new_token" in st.session_state:
    token = st.session_state.new_token
    cookie_manager.set("access_token", token)
    del st.session_state["new_token"]
else:
    try:
        token = cookie_manager.get("access_token")
    except Exception:
        token = None

# ==========================================
# 🔒 강제 로그아웃
# ==========================================
def force_logout(msg: str):
    st.markdown(f'<div class="alert-warn">{msg}</div>', unsafe_allow_html=True)
    st.session_state.clear()
    try:
        cookie_manager.delete("access_token")
    except Exception:
        pass
    time.sleep(2)
    try:
        st.switch_page("app.py")
    except Exception:
        st.switch_page("frontend/app.py")
    st.stop()

# ==========================================
# 🔥 인증 체크
# ==========================================
if "user" in st.session_state and st.session_state.user is not None:
    # ✅ 이미 이번 세션에서 인증 완료 → 바로 통과
    pass

elif token:
    # 쿠키가 있다면 백엔드에 검증 요청
    is_valid, result = api_verify_token(token)
    if is_valid:
        user_name_from_api = result.get("name") or (token and "사용자") or "사용자"
        st.session_state.user = {
            "name": result.get("name"),
            "role": result.get("role", "user"),
            "profile_image_url": result.get("profile_image_url"),
        }
        st.session_state.token = token
    else:
        force_logout(f"🔒 {result}")

else:
    # stx가 첫 렌더에 쿠키를 못 읽는 경우 → 한 번만 재시도
    if not st.session_state.get("_cookie_retry"):
        st.session_state["_cookie_retry"] = True
        time.sleep(0.4)
        st.rerun()
    else:
        # 두 번 시도해도 없으면 진짜 비로그인 상태
        del st.session_state["_cookie_retry"]
        force_logout("로그인이 필요한 서비스입니다. 2초 후 이동합니다.")

# 여기까지 오면 session_state.user 확정
user_info   = st.session_state.user or {}
user_name   = user_info.get("name") or "사용자"
user_role   = user_info.get("role", "user")
user_profile_image_url = user_info.get("profile_image_url")
role_display = "일반회원" if user_role == "user" else "관리자"

# ==========================================
# 🧭 상단 네비게이션 바
# ==========================================
selected = option_menu(
    menu_title=None,
    options=["홈", "AI 면접", "내 기록", "마이페이지"],
    icons=["house", "robot", "clipboard-data", "person"],
    menu_icon="cast",
    default_index=0,
    orientation="horizontal",
    styles={
        "container":         {"padding": "0!important", "background-color": "#fafafa"},
        "icon":              {"color": "#bb38d0", "font-size": "20px"},
        "nav-link":          {"font-size": "16px", "text-align": "left", "margin": "0px", "--hover-color": "#eee"},
        "nav-link-selected": {"background-color": "#bb38d0"},
    }
)

# ==========================================
# 🖼️ 배너
# ==========================================
st.image(
    "https://via.placeholder.com/1400x100/1E1E1E/FFFFFF?text=AIWORK+%7C+AI+%EB%AA%A8%EC%9D%98%EB%A9%B4%EC%A0%91+%ED%94%8C%EB%9E%AB%ED%8F%BC",
    use_container_width=True,
)
st.write("")

# ==========================================
# 🏠 홈 탭
# ==========================================
if selected == "홈":
    left_col, _, right_col = st.columns([7, 0.1, 3])

    # ── 오른쪽 패널 ──────────────────────────────
    with right_col:
        with st.container(border=True):
            c1, c2 = st.columns([2, 8])
            with c1:
                avatar_url = user_profile_image_url or f"https://api.dicebear.com/7.x/avataaars/svg?seed={user_name}"
                st.image(avatar_url, width=55)
            with c2:
                st.markdown(f"**{user_name} 님** ({role_display}) 🔒")
                if st.button("로그아웃 ➔", key="logout_btn"):
                    try:
                        cookie_manager.delete("access_token")
                    except Exception:
                        pass
                    st.session_state.clear()
                    time.sleep(0.3)
                    st.switch_page("app.py")

            st.divider()
            nc1, nc2, nc3 = st.columns(3)
            nc1.button("이력서",     use_container_width=True)
            nc2.button("내 기록",    use_container_width=True)
            nc3.button("마이페이지", use_container_width=True)

        st.write("")
        action_ph = st.empty()
        if st.button("✨ AI 모의 면접 시작", type="primary", use_container_width=True):
            action_ph.markdown('<div class="alert-ok">✨ 면접 대기실로 이동합니다! 건투를 빕니다!</div>', unsafe_allow_html=True)
            time.sleep(1)
            st.switch_page("pages/interview.py")

        st.write("")
        with st.container(border=True):
            st.markdown("🔗 **Github Repository**")
            st.caption("SKN23-3rd-1TEAM 깃허브 주소")

    # ── 왼쪽 패널 ────────────────────────────────
    with left_col:
        st.markdown(f"### **{user_name}** 님을 위한 맞춤 추천")
        tab1, tab2, tab3 = st.tabs(["📋 추천 공고", "📈 백엔드 트렌드", "💡 AI 면접 Tips"])

        with tab1:
            for company, role, desc in [
                ("네이버 (NAVER)", "Python 백엔드 신입/경력", "FastAPI와 MSA 환경에서 대규모 트래픽을 처리할 개발자를 모십니다."),
                ("카카오 (Kakao)", "AI 엔지니어 인턴",        "LLM 기반 서비스를 개발할 AI 엔지니어를 모집합니다."),
                ("라인 (LINE)",   "백엔드 개발자 (신입)",     "글로벌 메신저 플랫폼의 백엔드 시스템을 함께 만들어갈 분을 찾습니다."),
            ]:
                with st.container(border=True):
                    a, b = st.columns([8, 2])
                    with a:
                        st.markdown(f"#### {company} — {role}")
                        st.write(desc)
                    with b:
                        st.button("지원하기", key=f"apply_{company}", use_container_width=True)

        with tab2:
            st.markdown('<div class="alert-info">💡 오늘의 백엔드 기술 블로그 및 아티클이 노출되는 영역입니다.</div>', unsafe_allow_html=True)
            for title, desc in [
                ("FastAPI vs Django: 2026 트렌드 비교",    "비동기 처리와 타입 힌트를 중심으로 두 프레임워크를 심층 비교합니다."),
                ("LLM 서빙 최적화: vLLM과 TensorRT-LLM",  "대규모 언어 모델을 프로덕션에서 효율적으로 서빙하는 방법을 알아봅니다."),
            ]:
                with st.container(border=True):
                    st.markdown(f"**{title}**")
                    st.caption(desc)

        with tab3:
            st.markdown('<div class="alert-info">💡 최신 AI 면접 합격 후기 및 팁 게시판 영역입니다.</div>', unsafe_allow_html=True)
            for tip, desc in [
                ("STAR 기법으로 답변하기",     "Situation → Task → Action → Result 구조로 경험을 구체적으로 설명하세요."),
                ("기술 면접 단골 질문 TOP 5", "시간복잡도, DB 인덱스, REST API, 동시성, 캐싱 전략을 꼭 준비하세요."),
            ]:
                with st.container(border=True):
                    st.markdown(f"**💬 {tip}**")
                    st.caption(desc)

elif selected == "AI 면접":
    st.markdown("## 🤖 AI 모의면접")
    st.info("면접 기능은 준비 중입니다.")

elif selected == "내 기록":
    st.markdown("## 📋 내 면접 기록")
    st.info("면접 기록 기능은 준비 중입니다.")

elif selected == "마이페이지":
    st.markdown("## 👤 마이페이지")
    st.info("마이페이지 기능은 준비 중입니다.")
