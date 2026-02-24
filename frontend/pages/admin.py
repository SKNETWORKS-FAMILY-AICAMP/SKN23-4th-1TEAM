"""
File: admin.py
Author: 김다빈
Created: 2026-02-21
Description: AWS EC2 서버 관리자 대시보드 (Suscale 스타일 UI)
             서버 제어, 배포 도구, 시스템 로그, 회원 관리, 설정 기능 포함

Modification History:
- 2026-02-21 (김다빈): 초기 생성 — 대시보드, 서버 제어, 배포, 로그, 회원 관리 UI
- 2026-02-22 (김다빈): 관리자 페이지 통합, Suscale 테마 CSS 적용, 회원 등급/삭제 기능 추가
- 2026-02-22 (양창일): username 혼동으로 email, name으로 정리
- 2026-02-23 (김지우): 회원 관리 탭 selectbox SyntaxError(쉼표 누락) 해결
- 2026-02-23 (김지우): 설정 탭 내부에 시스템 종료(로그아웃) 기능 추가 및 tier 업데이트 쿼리 버그 수정
"""

import streamlit as st
import time
import pandas as pd

from utils.config import (
    AWS_REGION,
    EC2_INSTANCE_ID,
    SSH_KEY_PATH,
    NGROK_AUTHTOKEN,
    GITHUB_REPO,
    REMOTE_APP_DIR,
    REMOTE_APP_FILE,
    STREAMLIT_PORT,
)
from utils.aws_utils import get_instance_info, start_instance, stop_instance
from utils.ssh_utils import ssh_command, get_system_metrics, check_process_status
from utils.db_utils import fetch_remote_db, run_remote_sql

st.set_page_config(
    page_title="서버 관리자",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- 인증 및 권한 확인 (쿠키 기반 세션 유지) ---
import extra_streamlit_components as stx
from utils.api_utils import api_verify_token

cookie_manager = stx.CookieManager(key="admin_cookie_manager")

if "new_token" in st.session_state:
    token = st.session_state.new_token
    cookie_manager.set("access_token", token, secure=False, same_site="lax")
    del st.session_state["new_token"]
else:
    try:
        token = cookie_manager.get("access_token")
    except Exception:
        token = None

if "user" not in st.session_state or st.session_state.user is None:
    if token:
        is_valid, result = api_verify_token(token)
        if is_valid:
            st.session_state.user = {
                "name": result.get("name"),
                "role": result.get("role", "user"),
            }
            st.session_state.token = token
        else:
            st.warning("유효하지 않은 토큰입니다. 다시 로그인해주세요.")
            st.stop()
    else:
        # 쿠키 읽기 재시도 로직 (초기 렌더링 시 지연 문제 해결)
        if not st.session_state.get("_admin_cookie_retry"):
            st.session_state["_admin_cookie_retry"] = True
            import time

            time.sleep(0.4)
            st.rerun()
        else:
            del st.session_state["_admin_cookie_retry"]
            st.warning("로그인이 필요합니다.")
            st.stop()

if st.session_state.user.get("role") != "admin":
    st.error("관리자 페이지 접근 권한이 없습니다.")
    st.stop()
# ----------------------

# --- 커스텀 CSS (Suscale 스타일 테마 적용) ---
st.markdown(
    """
<style>
    /* 1. 전체 대시보드 배경 - 연한 라이트 그레이 */
    .stApp, 
    [data-testid="stAppViewContainer"], 
    [data-testid="stMain"],
    [data-testid="stApp"] {
        background-color: #f0f2f5 !important;
        color: #111111 !important;
    }
    
    /* 2. 기존 기본 제공 사이드바 완전히 숨김 처리 (커스텀 컨테이너 쓸 예정) */
    [data-testid="stSidebar"] {
        display: none !important;
    }
    header[data-testid="stHeader"] {
        display: none !important; /* Streamlit 기본 헤더 완전 숨김 */
    }
    
    /* 3. 상단 풀위드스 하얀색 헤더바 (Custom) */
    .custom-header {
        position: fixed;
        top: 0; left: 0; right: 0;
        height: 60px;
        background-color: #ffffff;
        border-bottom: 1px solid #eaebf0;
        display: flex;
        align-items: center;
        padding: 0 40px;
        z-index: 999999;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }

    h1, h2, h3, h4, h5, h6, p, span, div {
        color: #333333 !important;
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, 'Helvetica Neue', 'Segoe UI', 'Apple SD Gothic Neo', 'Noto Sans KR', 'Malgun Gothic', 'Apple Color Emoji', 'Segoe UI Emoji', 'Segoe UI Symbol', sans-serif !important;
    }

    /* 4. 흰색 메인 컨테이너 (좌측 메뉴 + 우측 컨텐츠 통합박스) */
    [data-testid="block-container"],
    [data-testid="stMainBlockContainer"] {
        background-color: #ffffff !important;
        border-radius: 12px !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
        padding: 2rem 3rem !important; /* 내부 패딩 최소화 */
        width: 100% !important; 
        max-width: 1300px !important;
        margin: 80px auto 20px auto !important; /* 화면을 넘지 않도록 상/하 마진 감소 */
        border: 1px solid #eaebf0 !important;
    }

    /* 5. 좌측 메뉴 텍스트 라디오 버튼 커스텀 (Suscale 플랫 텍스트 스타일) */
    [data-testid="stRadio"],
    div[role="radiogroup"] {
        width: 100% !important;
    }
    div[role="radiogroup"] label > div:first-child { display: none !important; }
    
    div[role="radiogroup"] label {
        display: flex !important; align-items: center !important; width: 100% !important; 
        padding: 14px 18px !important; 
        background-color: transparent !important;
        border-radius: 8px !important; cursor: pointer !important; margin-bottom: 4px !important; 
        transition: all 0.2s ease !important;
        box-sizing: border-box !important;
    }
    div[role="radiogroup"] label p {
        color: #4b5563 !important; font-size: 15px !important; font-weight: 600 !important; margin: 0 !important;
    }
    div[role="radiogroup"] label:hover { 
        background-color: #f3f4f6 !important;
    }
    
    /* 상태가 On 인 경우: Streamlit의 여러 버전 DOM 구조 지원 */
    div[role="radiogroup"] label:has(input:checked),
    div[role="radiogroup"] label[data-checked="true"],
    div[role="radiogroup"] label[aria-checked="true"],
    div[role="radiogroup"] label:has(div[data-checked="true"]),
    div[role="radiogroup"] label:has([aria-checked="true"]) { 
        background-color: #3b82f6 !important; 
    }
    
    div[role="radiogroup"] label:has(input:checked) p,
    div[role="radiogroup"] label[data-checked="true"] p,
    div[role="radiogroup"] label[aria-checked="true"] p,
    div[role="radiogroup"] label:has(div[data-checked="true"]) p,
    div[role="radiogroup"] label:has([aria-checked="true"]) p {
        color: #ffffff !important; font-weight: 700 !important;
    }
    
    div[role="radiogroup"] label:focus, 
    div[role="radiogroup"] label:active {
        box-shadow: none !important; outline: none !important;
    }

    /* 6. 좌우 컬럼 레이아웃 완벽 분리 */
    /* 사이드바 영역: 패널 전체를 보더 박스로 감싸기 */
    [data-testid="column"]:first-child {
        border: 1px solid #eaebf0 !important;
        border-radius: 12px !important;
        padding: 15px 20px !important;
        background-color: #ffffff !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03) !important; 
        height: min-content !important;
    }
    
    /* 우측 메인 콘텐츠 (content_col) 좌측 패딩 */
    [data-testid="column"]:nth-of-type(2) {
        padding-left: 20px !important;
    }
    
    /* 스크롤바 커스텀 */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #9ca3af; }

    /* 작은 상태 표시 배지 */
    .status-badge {
        display: inline-block; padding: 4px 10px; border-radius: 4px; font-size: 12px; font-weight: 600;
    }
    .status-running { background-color: #e6f4ea !important; color: #1e8e3e !important; }
    .status-stopped { background-color: #fce8e6 !important; color: #d93025 !important; }
    
    /* 7. 모바일 반응형 (가로 스크롤 X, 세로는 전체 스크롤 허용) */
    @media (max-width: 768px) {
        [data-testid="block-container"], [data-testid="stMainBlockContainer"] {
            padding: 5px !important; 
            margin-top: 60px !important;
            margin-bottom: 20px !important;
        }
        [data-testid="column"]:first-child {
            padding: 15px !important; 
            border: 1px solid #eaebf0 !important;
            border-radius: 12px !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.05) !important;
            margin-bottom: 20px !important;
        }
        [data-testid="column"]:nth-of-type(2) {
            padding: 10px !important;
            height: auto !important; /* 모바일은 내부 스크롤 해제, 전체 스크롤 */
            overflow-y: visible !important;
        }
        .list-header { display: none !important; } /* 모바일에서는 테이블 헤더를 숨기는 게 깔끔함 */
        .list-row { flex-direction: column; align-items: flex-start; padding: 15px 0;}
        .list-row > div { width: 100% !important; margin-bottom: 10px; }
        .list-row > div:last-child { margin-bottom: 0; }
    }

    /* 리스트 형태의 행(row) 구분선 */
    .list-row {
        border-bottom: 1px solid #eaebf0;
        padding: 18px 0;
        display: flex;
        align-items: center;
    }
    .list-header {
        border-top: 1px solid #111;
        border-bottom: 1px solid #eaebf0;
        padding: 12px 0;
        font-size: 13px;
        color: #555;
        font-weight: 600;
        display: flex;
    }
    
    /* 제목/서브타이틀 아래 흐린 가로선 */
    .section-divider {
        border-bottom: 1px solid #eaebf0;
        padding-bottom: 15px;
        margin-bottom: 20px;
    }

    /* 버튼 기본 및 프라이머리 스타일 (가로로 꽉찬 형태 대비) */
    .stButton > button {
        background-color: #ffffff;
        color: #555555;
        border: 1px solid #cccccc;
        border-radius: 6px;
        font-weight: 500;
        transition: all 0.2s ease;
    }
    .stButton > button:hover {
        border-color: #3b82f6;
        color: #3b82f6;
        background-color: #f0f7ff;
    }
    
    /* 완료/저장 같은 주요 버튼(파란색 바탕) */
    .stButton > button[kind="primary"] {
        background-color: #3b82f6 !important;
        color: white !important;
        border: none !important;
        border-radius: 6px;
        font-weight: 600;
    }
    .stButton > button[kind="primary"]:hover {
        background-color: #2563eb !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# === 상단 헤더 (전체 폭) ===
st.markdown(
    """
    <div class="custom-header">
        <h3 style="margin:0; font-size:18px; font-weight:700; color:#111;">△ Suscale &nbsp;<span style='color:#ccc; font-weight:normal;'>|</span>&nbsp; <span style='font-size:16px; color:#555;'>3팀 서버 관리자</span></h3>
    </div>
    """,
    unsafe_allow_html=True,
)

# === 메인 컨테이너 구조 분할 (좌측 20%, 우측 80%) ===

nav_col, content_col = st.columns([2, 8], gap="large")

# --- 좌측 네비게이션 메뉴 (nav_col) ---
with nav_col:
    st.markdown("<div style='padding: 30px 20px 20px 20px;'>", unsafe_allow_html=True)
    st.markdown(
        "<h4 style='font-size:14px; color:#111; font-weight:700; margin-bottom:15px;'>대시보드</h4>",
        unsafe_allow_html=True,
    )

    # st.radio를 CSS로 투명화하여 텍스트 메뉴처럼 보이게 처리
    menu = st.radio(
        "메뉴 이동 (숨김처리용 라벨)",
        [
            "서버 제어 (Control)",
            "데이터 관리 (Data)",  # 원래 "배포 도구 (Deployment)" 였음
            "시스템 로그 (Logs)",
            "회원 관리 (Users)",
            "설정 (Settings)",
        ],
        index=0,
        label_visibility="collapsed",
    )

    st.markdown(
        "<hr style='margin:20px 0; border:none; border-top:1px solid #eaebf0;'>",
        unsafe_allow_html=True,
    )

    if EC2_INSTANCE_ID:
        st.markdown(
            f"""
            <div style='margin-top: 15px; padding: 12px 15px; background-color: #f8f9fa; border-radius: 8px; border: 1px solid #eaebf0;'>
                <p style='font-size:11px; font-weight:600; color:#888; margin:0 0 4px 0; letter-spacing:0.5px;'>INSTANCE ID</p>
                <p style='font-size:13px; color:#555; margin:0; font-family:monospace; word-break:break-all;'>{EC2_INSTANCE_ID}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            "<div style='margin-top: 15px; padding: 12px 15px; background-color: #fce8e6; border-radius: 8px; border: 1px solid #f2cfcb;'><p style='font-size:12px; color:#d93025; margin:0;'>인스턴스 ID 누락</p></div>",
            unsafe_allow_html=True,
        )

    st.markdown("</div>", unsafe_allow_html=True)

# --- 우측 메인 콘텐츠 (content_col) ---
with content_col:
    st.markdown("<div class='content-area'>", unsafe_allow_html=True)

    # --- 메인 Content 헤더 (Suscale 페이지 상단 제목 스타일) ---
    clean_menu_title = menu.split("(")[0].strip()

    st.markdown(
        f"""
    <div style="margin-bottom: 25px;">
        <h2 style="font-size:22px; font-weight:700; color:#111; margin-bottom:5px;">{clean_menu_title}</h2>
        <p style="font-size:13px; color:#888;">선택하신 '{clean_menu_title}' 메뉴의 정보와 설정을 관리합니다.</p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # 연결 테스트 및 정보 가져오기
    try:
        info = get_instance_info()
    except Exception as e:
        info = {"error": str(e)}

    if "error" in info:
        st.error(f"AWS 연결 오류: {info['error']}")
        st.info(
            "💡 Tip: .env 파일의 AWS 키 설정을 확인하거나, 인터넷 연결을 확인하세요."
        )
    else:
        state = info.get("state", "unknown")
        ip = info.get("ip", "N/A")

        # -------------------------------------------------------------------------
        # 1. 대시보드 (Dashboard)
        # -------------------------------------------------------------------------
        if "대시보드" in menu:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                if state == "running":
                    badge_html = (
                        '<span class="status-badge status-running">RUNNING</span>'
                    )
                else:
                    badge_html = f'<span class="status-badge status-stopped">{state.upper()}</span>'

                st.markdown(
                    f"""
                <div class="metric-card">
                    <p style="color:#666; font-size:14px; margin-bottom:5px; font-weight:600;">상태 (Status)</p>
                    <div>{badge_html}</div>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            with col2:
                st.markdown(
                    f"""
                <div class="metric-card">
                    <p style="color:#666; font-size:14px; margin-bottom:5px; font-weight:600;">인스턴스 타입</p>
                    <h3 style="margin:0; font-size:20px; font-weight:700;">{info.get("type", "N/A")}</h3>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            with col3:
                st.markdown(
                    f"""
                <div class="metric-card">
                    <p style="color:#666; font-size:14px; margin-bottom:5px; font-weight:600;">퍼블릭 IP</p>
                    <h3 style="margin:0; font-size:20px; font-weight:700;">{ip}</h3>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            with col4:
                uptime = "N/A"
                if state == "running":
                    import datetime

                    launch_time = info["launch_time"]
                    uptime_sec = (
                        datetime.datetime.now(launch_time.tzinfo) - launch_time
                    ).total_seconds()
                    uptime = f"{int(uptime_sec // 3600)} 시간"
                st.markdown(
                    f"""
                <div class="metric-card">
                    <p style="color:#666; font-size:14px; margin-bottom:5px; font-weight:600;">가동 시간</p>
                    <h3 style="margin:0; font-size:20px; font-weight:700;">{uptime}</h3>
                </div>
                """,
                    unsafe_allow_html=True,
                )

            st.markdown("<br>", unsafe_allow_html=True)

            if state == "running":
                st.markdown(
                    "<h3 style='font-size:16px; font-weight:700; margin-bottom:15px; color:#111;'>실시간 시스템 리소스</h3>",
                    unsafe_allow_html=True,
                )
                if st.button("새로고침 (Refresh)"):
                    st.rerun()

                cpu, mem, disk = get_system_metrics(ip)

                st.markdown(
                    "<div class='metric-card' style='padding: 30px;'>",
                    unsafe_allow_html=True,
                )
                m1, m2, m3 = st.columns(3)
                with m1:
                    st.progress(int(cpu))
                    st.markdown(
                        f"<p style='text-align:center; margin-top:10px; font-weight:600; font-size:14px;'>CPU 사용량: <span style='color:#3b82f6;'>{cpu:.1f}%</span></p>",
                        unsafe_allow_html=True,
                    )
                with m2:
                    st.progress(int(mem))
                    st.markdown(
                        f"<p style='text-align:center; margin-top:10px; font-weight:600; font-size:14px;'>메모리 사용량: <span style='color:#3b82f6;'>{mem:.1f}%</span></p>",
                        unsafe_allow_html=True,
                    )
                with m3:
                    st.progress(int(disk))
                    st.markdown(
                        f"<p style='text-align:center; margin-top:10px; font-weight:600; font-size:14px;'>디스크 사용량: <span style='color:#3b82f6;'>{disk}%</span></p>",
                        unsafe_allow_html=True,
                    )
                st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.info("리소스 정보를 보려면 서버를 먼저 켜주세요.")

        # -------------------------------------------------------------------------
        # 2. 서버 제어 (Control)
        # -------------------------------------------------------------------------
        elif "서버 제어" in menu:
            st.markdown(
                """
                <div class='list-header'>
                    <div style='width: 25%; padding-left: 10px;'>관리 항목</div>
                    <div style='width: 50%;'>세부 정보</div>
                    <div style='width: 25%; text-align: right; padding-right: 10px;'>상태 및 액션</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            col1, col2, col3 = st.columns([1, 2, 1], gap="small")
            with col1:
                st.markdown(
                    "<div style='padding: 20px 0 20px 10px; font-weight: 600; color: #333;'>전원 제어</div>",
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    """
                    <div style='padding: 20px 0; color: #555; line-height: 1.6; font-size: 14px;'>
                        서버의 전원을 켜거나 끕니다.<br>
                        <span style='color:#888; font-size:12px;'>중지 시 요금이 청구되지 않으나 퍼블릭 IP가 변경될 수 있습니다.</span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    "<div style='padding: 20px 10px 20px 0;'>", unsafe_allow_html=True
                )
                if state == "stopped":
                    if st.button(
                        "서버 시작 (START)",
                        type="primary",
                        use_container_width=True,
                        key="btn_start",
                    ):
                        st.session_state.confirm_start = True
                        st.rerun()

                    if st.session_state.get("confirm_start"):
                        pwd_start = st.text_input(
                            "📝 전원 켜기 비밀번호 입력",
                            type="password",
                            key="pwd_start",
                        )
                        col_btn1, col_btn2 = st.columns(2)
                        if col_btn1.button(
                            "✅ 확인", key="confirm_start_btn", use_container_width=True
                        ):
                            if pwd_start == "dbdbkdb":
                                start_instance()
                                st.session_state.confirm_start = False
                                st.toast("서버 시작 명령을 보냈습니다...")
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error("❌ 비밀번호가 틀렸습니다.")
                        if col_btn2.button(
                            "❌ 취소", key="cancel_start_btn", use_container_width=True
                        ):
                            st.session_state.confirm_start = False
                            st.rerun()

                elif state == "running":
                    if st.button(
                        "서버 중지 (STOP)",
                        type="primary",
                        use_container_width=True,
                        key="btn_stop",
                    ):
                        st.session_state.confirm_stop = True
                        st.rerun()

                    if st.session_state.get("confirm_stop"):
                        pwd_stop = st.text_input(
                            "📝 전원 끄기 비밀번호 입력",
                            type="password",
                            key="pwd_stop",
                        )
                        col_btn1, col_btn2 = st.columns(2)
                        if col_btn1.button(
                            "✅ 확인", key="confirm_stop_btn", use_container_width=True
                        ):
                            if pwd_stop == "dbdbkdb":
                                stop_instance()
                                st.session_state.confirm_stop = False
                                st.toast("서버 중지 명령을 보냈습니다...")
                                time.sleep(2)
                                st.rerun()
                            else:
                                st.error("❌ 비밀번호가 틀렸습니다.")
                        if col_btn2.button(
                            "❌ 취소", key="cancel_stop_btn", use_container_width=True
                        ):
                            st.session_state.confirm_stop = False
                            st.rerun()
                else:
                    st.warning(f"상태: {state}")
                    if st.button("상태 확인", use_container_width=True):
                        st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown(
                "<div style='border-bottom: 1px solid #eaebf0;'></div>",
                unsafe_allow_html=True,
            )

            col1, col2, col3 = st.columns([1, 2, 1], gap="small")
            with col1:
                st.markdown(
                    "<div style='padding: 20px 0 20px 10px; font-weight: 600; color: #333;'>시스템 정보</div>",
                    unsafe_allow_html=True,
                )
            with col2:
                st.markdown(
                    f"""
                    <div style='padding: 20px 0; color: #555; line-height: 1.6; font-size: 14px;'>
                        <b>Instance ID:</b> {EC2_INSTANCE_ID if EC2_INSTANCE_ID else 'N/A'}<br>
                        <b>인스턴스 타입:</b> {info.get("type", "N/A")}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    "<div style='padding: 20px 10px 20px 0; text-align: right;'>",
                    unsafe_allow_html=True,
                )
                if state == "running":
                    st.markdown(
                        '<span class="status-badge status-running">RUNNING</span>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<span class="status-badge status-stopped">{state.upper()}</span>',
                        unsafe_allow_html=True,
                    )
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown(
                "<div style='border-bottom: 1px solid #eaebf0;'></div>",
                unsafe_allow_html=True,
            )

            col1, col2, col3 = st.columns([1, 2, 1], gap="small")
            with col1:
                st.markdown(
                    "<div style='padding: 20px 0 20px 10px; font-weight: 600; color: #333;'>네트워크 및 접속</div>",
                    unsafe_allow_html=True,
                )
            with col2:
                pub_dns = (
                    f"ec2-{ip.replace('.','-')}.ap-northeast-2.compute.amazonaws.com"
                    if ip != "N/A"
                    else "N/A"
                )
                ssh_cmd = f"ssh -i {SSH_KEY_PATH} ubuntu@{ip}"
                st.markdown(
                    f"""
                    <div style='padding: 20px 0; color: #555; line-height: 1.6; font-size: 14px;'>
                        <b>퍼블릭 IP:</b> {ip}<br>
                        <b style='font-size: 12px; color:#888;'>DNS:</b> <span style='font-size:12px;'>{pub_dns}</span><br>
                        <b style='font-size: 12px; color:#888;'>SSH:</b> <code style='font-size:12px; color:#d93025; background:#f8f9fa; padding:2px 6px; border-radius:4px;'>{ssh_cmd}</code>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
            with col3:
                st.markdown(
                    "<div style='padding: 30px 10px 20px 0; text-align: right;'>",
                    unsafe_allow_html=True,
                )
                if st.button("연결 테스트", key="conn_test", use_container_width=True):
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

            st.markdown(
                "<div style='border-bottom: 1px solid #eaebf0;'></div>",
                unsafe_allow_html=True,
            )

        # -------------------------------------------------------------------------
        # 3. 데이터 관리 (Data Management) - 기존 배포 도구 대체
        # -------------------------------------------------------------------------
        elif "데이터 관리" in menu:
            st.markdown(
                "<div class='metric-card' style='text-align:left;'>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<h3 style='font-size:16px; font-weight:700; margin-bottom:15px; color:#111;'>데이터베이스 백업 및 다운로드</h3>",
                unsafe_allow_html=True,
            )

            if state != "running":
                st.warning("서버가 켜져 있어야 DB 데이터를 추출할 수 있습니다.")
            else:
                st.info(
                    "원격 DB의 데이터를 실시간으로 조회하여 CSV 파일로 안전하게 다운로드합니다."
                )

                # 다운로드 가능한 테이블 목록 (필요시 확장 가능)
                tables_to_export = ["users", "interviews", "reports"]

                selected_table = st.selectbox(
                    "추출할 데이터 테이블 선택", tables_to_export
                )

                if st.button("데이터 추출 및 다운로드 준비", type="primary"):
                    with st.spinner(
                        f"'{selected_table}' 테이블 데이터를 가져오는 중..."
                    ):
                        data = fetch_remote_db(ip, selected_table)

                        if data and not ("error" in data[0] if data else False):
                            df = pd.DataFrame(data)
                            st.success(
                                f"데이터 추출 성공! (총 {len(df)}개 원도우 조회됨)"
                            )

                            # CSV 변환
                            csv = df.to_csv(index=False).encode(
                                "utf-8-sig"
                            )  # Excel 호환을 위해 utf-8-sig 사용

                            st.download_button(
                                label=f"📊 {selected_table}.csv 다운로드",
                                data=csv,
                                file_name=f"{selected_table}_export_{int(time.time())}.csv",
                                mime="text/csv",
                                type="primary",
                            )
                        else:
                            st.error(
                                f"데이터 추출 실패: {data[0].get('error') if data else '알 수 없는 오류'}"
                            )

            st.markdown("</div>", unsafe_allow_html=True)

        # -------------------------------------------------------------------------
        # 4. 시스템 로그 (Logs)
        # -------------------------------------------------------------------------
        elif "시스템 로그" in menu:
            st.markdown(
                "<div class='metric-card' style='text-align:left;'>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<h3 style='font-size:16px; font-weight:700; margin-bottom:15px; color:#111;'>애플리케이션 로그 뷰어</h3>",
                unsafe_allow_html=True,
            )

            if state != "running":
                st.warning("서버가 꺼져 있어 로그를 볼 수 없습니다.")
            else:
                col_filt1, col_filt2 = st.columns([3, 1])
                lines = col_filt1.slider("가져올 라인 수", 10, 500, 50)
                only_errors = col_filt2.checkbox("🚨 Error 로그만 보기", value=False)

                if st.button("로그 새로고침 (Fetch)", type="primary"):
                    with st.spinner("서버에서 로그를 수집 중입니다..."):
                        if only_errors:
                            # grep을 통해 Error 나 Exception 이 포함된 줄만 가져오기 (-i: 대소문자 무시)
                            cmd = f"tail -n 1000 ~/nohup.out | grep -iE 'error|exception|traceback' | tail -n {lines}"
                        else:
                            cmd = f"tail -n {lines} ~/nohup.out"

                        out, _ = ssh_command(ip, cmd)
                        if out:
                            st.code(out, language="bash")
                        else:
                            if only_errors:
                                st.success("검색된 에러 로그가 없습니다! 🎉")
                            else:
                                st.code("로그 파일이 비어있거나 찾을 수 없습니다.")
            st.markdown("</div>", unsafe_allow_html=True)

        # -------------------------------------------------------------------------
        # 5. 회원 관리 (Users)
        # -------------------------------------------------------------------------
        elif "회원 관리" in menu:
            st.markdown(
                "<div class='metric-card' style='text-align:left;'>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<h3 style='font-size:16px; font-weight:700; margin-bottom:15px; color:#111;'>통합 회원 관리 시스템</h3>",
                unsafe_allow_html=True,
            )

            if state != "running":
                st.warning("서버가 켜져 있어야 데이터를 가져올 수 있습니다.")
            else:
                st.markdown(
                    "<h4 style='font-size:15px; font-weight:600; margin-bottom:10px;'>👥 전체 사용자 목록</h4>",
                    unsafe_allow_html=True,
                )
                if st.button("새로고침 (Refresh Data)"):
                    st.cache_data.clear()
                    st.rerun()

                data = fetch_remote_db(ip, "users")

                if data and not ("error" in data[0] if data else False):
                    df = pd.DataFrame(data)
                    if "status" not in df.columns:
                        df["status"] = "active"
                    if "tier" not in df.columns:
                        df["tier"] = "normal"

                    st.dataframe(df, use_container_width=True)

                    st.markdown(
                        "<div class='section-divider'></div>", unsafe_allow_html=True
                    )
                    col_u1, col_u2 = st.columns(2, gap="large")

                    # [왼쪽] 회원 등급 변경
                    with col_u1:
                        st.markdown(
                            "<h4 style='font-size:15px; font-weight:600; margin-bottom:10px;'>💎 회원 등급 변경</h4>",
                            unsafe_allow_html=True,
                        )
                        if not df.empty:
                            target_user_tier = st.selectbox(
                                "등급을 변경할 사용자",
                                [
                                    f"{row['id']}: {row.get('name') or row.get('email') or 'unknown'}"
                                    for row in data
                                ],
                                key="tier_select",
                            )
                            new_tier = st.selectbox("변경할 등급", ["normal", "plus"])

                            if st.button(
                                "등급 수정 적용",
                                type="primary",
                                use_container_width=True,
                            ):
                                user_id = target_user_tier.split(":")[0]
                                # 🔥 방금 고친 버그 수정 부분! (status -> tier 로 쿼리 완벽 수정)
                                sql = "UPDATE users SET tier = %s WHERE id = %s"
                                res = run_remote_sql(
                                    ip, sql, args=[new_tier, int(user_id)]
                                )

                                if "SUCCESS" in res:
                                    st.success("등급 변경 완료!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"수정 실패: {res}")

                    # [오른쪽] 회원 상태 관리 (휴면/탈퇴)
                    with col_u2:
                        st.markdown(
                            "<h4 style='font-size:15px; font-weight:600; margin-bottom:10px;'>🛑 계정 상태 관리 (휴면/탈퇴)</h4>",
                            unsafe_allow_html=True,
                        )
                        if not df.empty:
                            target_user_status = st.selectbox(
                                "상태를 변경할 사용자",
                                [
                                    f"{row['id']}: {row.get('name') or row.get('email') or 'unknown'}"
                                    for row in data
                                ],
                                key="status_select",
                            )
                            status_dict = {
                                "정상 (active)": "active",
                                "휴면 계정 (dormant)": "dormant",
                                "탈퇴 처리 (withdrawn)": "withdrawn",
                            }
                            selected_status_label = st.selectbox(
                                "변경할 상태", list(status_dict.keys())
                            )

                            if st.button(
                                "상태 변경 적용",
                                type="primary",
                                use_container_width=True,
                            ):
                                user_id = target_user_status.split(":")[0]
                                new_status = status_dict[selected_status_label]
                                sql = "UPDATE users SET status = %s WHERE id = %s"
                                res = run_remote_sql(
                                    ip, sql, args=[new_status, int(user_id)]
                                )

                                if "SUCCESS" in res:
                                    if new_status == "withdrawn":
                                        st.warning(
                                            "탈퇴 처리되었습니다. (데이터는 보존됨)"
                                        )
                                    else:
                                        st.success(
                                            f"상태가 {new_status}로 변경되었습니다!"
                                        )
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"변경 실패: {res}")
                else:
                    st.warning("데이터가 없거나 조회에 실패했습니다.")
            st.markdown("</div>", unsafe_allow_html=True)

        # -------------------------------------------------------------------------
        # 6. 설정 (Settings) & 시스템 종료
        # -------------------------------------------------------------------------
        elif "설정" in menu:
            st.markdown(
                "<div class='metric-card' style='text-align:left;'>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<h3 style='font-size:16px; font-weight:700; margin-bottom:15px; color:#111;'>글로벌 서비스 관리자 설정</h3>",
                unsafe_allow_html=True,
            )

            import yaml
            import os

            settings_path = os.path.join(
                os.path.dirname(__file__), "..", "utils", "admin_settings.yaml"
            )

            # YAML 설정 불러오기
            def load_settings():
                if os.path.exists(settings_path):
                    with open(settings_path, "r", encoding="utf-8") as f:
                        return yaml.safe_load(f) or {}
                return {
                    "maintenance_mode": False,
                    "system_notice": "",
                    "notice_enabled": False,
                }

            # YAML 설정 저장하기
            def save_settings(data):
                with open(settings_path, "w", encoding="utf-8") as f:
                    yaml.dump(data, f, allow_unicode=True)

            global_settings = load_settings()

            # --- 1. 점검 모드 ---
            st.markdown(
                "<h4 style='font-size:15px; color:#c0392b; font-weight:600;'>🚨 점검 모드 (Maintenance Mode)</h4>",
                unsafe_allow_html=True,
            )
            st.info(
                "점검 모드를 켜면 지정된 관리자 IP 외에는 사이트 접속이 차단되고 점검 안내 페이지가 노출됩니다."
            )

            is_maintenance = st.toggle(
                "점검 모드 활성화",
                value=global_settings.get("maintenance_mode", False),
                key="toggle_maint",
            )
            if is_maintenance != global_settings.get("maintenance_mode", False):
                global_settings["maintenance_mode"] = is_maintenance
                save_settings(global_settings)
                if is_maintenance:
                    st.toast("🚨 점검 모드가 켜졌습니다! 사용자 접속이 차단됩니다.")
                else:
                    st.toast("✅ 점검 모드가 해제되었습니다.")

            st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

            # --- 2. 전역 시스템 공지사항 ---
            st.markdown(
                "<h4 style='font-size:15px; color:#111; font-weight:600;'>📢 글로벌 지정 공지사항</h4>",
                unsafe_allow_html=True,
            )
            notice_text = st.text_input(
                "공지사항 내용 텍스트", value=global_settings.get("system_notice", "")
            )
            is_notice = st.checkbox(
                "홈 화면 상단에 공지사항 띄우기 (배너 노출)",
                value=global_settings.get("notice_enabled", False),
            )

            if st.button("공지사항 설정 저장", type="primary"):
                global_settings["system_notice"] = notice_text
                global_settings["notice_enabled"] = is_notice
                save_settings(global_settings)
                st.success("공지사항 설정이 성공적으로 저장되었습니다.")

            st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

            # --- 3. 캐시 초기화 ---
            st.markdown(
                "<h4 style='font-size:15px; color:#111; font-weight:600;'>⚡ 시스템 캐시 초기화</h4>",
                unsafe_allow_html=True,
            )
            st.info(
                "Streamlit 내부 캐시(데이터가 갱신되지 않거나 느려질 때 사용)를 즉시 지웁니다."
            )
            if st.button("모든 캐시 초기화 (Clear Cache)"):
                st.cache_data.clear()
                st.cache_resource.clear()
                st.success("내부 캐시가 완벽하게 비워졌습니다!")

            # 🔥 시스템 종료 기능 (서버 켜짐/꺼짐 상관없이 동작하도록 분리)
            st.markdown(
                "<div class='section-divider' style='margin-top: 40px;'></div>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<h3 style='font-size:16px; font-weight:700; margin-bottom:10px; color:#e74c3c;'>시스템 종료</h3>",
                unsafe_allow_html=True,
            )
            st.info(
                "관리자 대시보드 사용을 마치고 초기 로그인 화면(app.py)으로 안전하게 빠져나갑니다."
            )

            if st.button("🚪 관리자 로그아웃 (Exit)", use_container_width=True):
                # 1. 세션 정보를 싹 날려서 권한을 초기화합니다.
                st.session_state.clear()
                # 2. 로그인 페이지(app.py)로 튕겨냅니다.
                st.switch_page("app.py")

            st.markdown("</div>", unsafe_allow_html=True)
