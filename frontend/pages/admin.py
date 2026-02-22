"""
File: admin.py
Author: 김다빈
Created: 2026-02-21
Description: AWS EC2 서버 관리자 대시보드 (Suscale 스타일 UI)
             서버 제어, 배포 도구, 시스템 로그, 회원 관리, 설정 기능 포함

Modification History:
- 2026-02-21 (김다빈): 초기 생성 — 대시보드, 서버 제어, 배포, 로그, 회원 관리 UI
- 2026-02-22 (김다빈): 관리자 페이지 통합, Suscale 테마 CSS 적용, 회원 등급/삭제 기능 추가
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

# --- 인증 및 권한 확인 ---
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("로그인이 필요합니다.")
    # st.switch_page("app.py") # 필요시 주석 해제하여 리다이렉트 처리
    st.stop()

if st.session_state.user.get("role") != "admin":
    st.error("관리자 페이지 접근 권한이 없습니다.")
    st.stop()

# TODO: 추후 FastAPI를 사용해 토큰 기반으로 로직 변경 시 아래와 같이 수정
# import requests
# headers = {"Authorization": f"Bearer {st.session_state.get('access_token')}"}
# res = requests.get("http://api.backend.com/admin/verify", headers=headers)
# if res.status_code != 200:
#     st.error("유효하지 않은 토큰입니다.")
#     st.stop()
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
            "배포 도구 (Deployment)",
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

    # 전체보기 영역 삭제 완료
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
            # 테이블 헤더 UI
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

            # 행 1: 전원 제어
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
                        start_instance()
                        st.toast("서버 시작 명령을 보냈습니다...")
                        time.sleep(2)
                        st.rerun()
                elif state == "running":
                    if st.button(
                        "서버 중지 (STOP)",
                        type="primary",
                        use_container_width=True,
                        key="btn_stop",
                    ):
                        stop_instance()
                        st.toast("서버 중지 명령을 보냈습니다...")
                        time.sleep(2)
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

            # 행 2: 시스템 정보
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

            # 행 3: 네트워크 및 접속
            col1, col2, col3 = st.columns([1, 2, 1], gap="small")
            with col1:
                st.markdown(
                    "<div style='padding: 20px 0 20px 10px; font-weight: 600; color: #333;'>네트워크 및 접속</div>",
                    unsafe_allow_html=True,
                )
            with col2:
                pub_dns = (
                    "N/A"
                    if ip == "N/A"
                    else f"ec2-{ip.replace('.','-')}.ap-northeast-2.compute.amazonaws.com"
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
        # 3. 배포 도구 (Deployment)
        # -------------------------------------------------------------------------
        elif "배포 도구" in menu:
            if state != "running":
                st.warning("먼저 서버를 켜주세요.")
            else:
                t1, t2 = st.tabs(["코드 동기화 (Git)", "서비스 관리 (Service)"])

                with t1:
                    st.markdown(
                        "<div style='text-align:left; margin-top:15px;'>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        "<h3 style='font-size:16px; font-weight:700; margin-bottom:10px; color:#111;'>GitHub 연동</h3>",
                        unsafe_allow_html=True,
                    )
                    st.info("GitHub에 올린 최신 코드를 서버로 내려받습니다.")
                    if st.button("최신 코드 받기 (Git Pull)", type="primary"):
                        with st.spinner("GitHub에서 코드를 가져오는 중..."):
                            cmd = f"""
                            if [ -d "3team" ]; then cd 3team && git pull; else git clone {GITHUB_REPO} 3team; fi
                            """
                            out, err = ssh_command(ip, cmd)
                            if out:
                                st.success("업데이트 성공!")
                                st.code(out)
                            if err:
                                st.error("오류 로그")
                                st.code(err)
                    st.markdown("</div>", unsafe_allow_html=True)

                with t2:
                    st.markdown(
                        "<div style='text-align:left; margin-top:15px;'>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        "<h3 style='font-size:16px; font-weight:700; margin-bottom:15px; color:#111;'>서비스 상태 관리</h3>",
                        unsafe_allow_html=True,
                    )
                    is_st_running = check_process_status(ip, "streamlit")

                    col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
                    st_badge = (
                        '<span class="status-badge status-running">가동 중</span>'
                        if is_st_running
                        else '<span class="status-badge status-stopped">중지됨</span>'
                    )
                    col_s1.markdown(
                        f"**Streamlit 앱 상태** &nbsp; {st_badge}",
                        unsafe_allow_html=True,
                    )

                    if col_s3.button("앱 재시작 (Restart)"):
                        ssh_command(ip, "pkill -f streamlit")
                        run_cmd = f"cd {REMOTE_APP_DIR} && nohup ~/myenv/bin/streamlit run {REMOTE_APP_FILE} --server.port {STREAMLIT_PORT} > ~/nohup.out 2>&1 &"
                        ssh_command(ip, run_cmd)
                        st.toast("앱을 재시작했습니다.")
                        time.sleep(2)
                        st.rerun()

                    st.markdown(
                        "<div class='section-divider'></div>", unsafe_allow_html=True
                    )
                    st.markdown(
                        "<h3 style='font-size:16px; font-weight:700; margin-bottom:15px; color:#111;'>Ngrok (외부 접속)</h3>",
                        unsafe_allow_html=True,
                    )
                    is_ngrok_running = check_process_status(ip, "ngrok")
                    ng_badge = (
                        '<span class="status-badge status-running">가동 중</span>'
                        if is_ngrok_running
                        else '<span class="status-badge status-stopped">중지됨</span>'
                    )
                    st.markdown(
                        f"**Ngrok 상태** &nbsp; {ng_badge}", unsafe_allow_html=True
                    )

                    st.markdown(
                        "<div style='height:10px;'></div>", unsafe_allow_html=True
                    )

                    ng_col1, ng_col2 = st.columns(2)
                    with ng_col1:
                        if not is_ngrok_running:
                            if st.button("Ngrok 시작 (Start)"):
                                ssh_command(
                                    ip,
                                    f"nohup ngrok http {STREAMLIT_PORT} > /dev/null 2>&1 &",
                                )
                                st.toast("Ngrok을 시작했습니다.")
                                time.sleep(2)
                                st.rerun()
                    with ng_col2:
                        if is_ngrok_running:
                            if st.button("Ngrok 중지 (Kill)"):
                                ssh_command(ip, "pkill -f ngrok")
                                st.toast("Ngrok을 종료했습니다.")
                                time.sleep(1)
                                st.rerun()

                    st.markdown(
                        "<div class='section-divider'></div>", unsafe_allow_html=True
                    )
                    st.markdown(
                        "<h4 style='font-size:14px; color:#555;'>접속 주소 확인</h4>",
                        unsafe_allow_html=True,
                    )
                    if st.button("주소 가져오기 (Fetch URL)"):
                        if not is_ngrok_running:
                            st.error("Ngrok이 꺼져 있습니다. 먼저 시작해주세요.")
                        elif not is_st_running:
                            st.warning("Streamlit 앱이 꺼져 있습니다!")
                        else:
                            out, _ = ssh_command(
                                ip,
                                "curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url'",
                            )
                            if out and "http" in out:
                                st.success(
                                    "접속 성공! 아래 주소를 클릭해서 들어가세요."
                                )
                                st.markdown(
                                    f"""
                                <div style="padding: 15px; border-radius: 8px; background-color: #f0f7ff; border: 1px dashed #3b82f6; text-align: center; margin-top:10px;">
                                    <h3 style="margin:0;"><a href="{out}" target="_blank" style="text-decoration: none; color: #2563eb;">{out}</a></h3>
                                </div>
                                """,
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.warning("주소를 가져올 수 없습니다.")
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
                lines = st.slider("가져올 라인 수", 10, 200, 50)
                if st.button("로그 새로고침 (Fetch)", type="primary"):
                    out, _ = ssh_command(ip, f"tail -n {lines} ~/nohup.out")
                    st.code(out if out else "로그 파일이 비어있거나 찾을 수 없습니다.")
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
                with st.expander("DB 스키마 업데이트 (최초 1회 실행)"):
                    if st.button("Tier 컬럼 추가하기 (ALTER TABLE)"):
                        res = run_remote_sql(
                            ip,
                            "ALTER TABLE users ADD COLUMN tier TEXT DEFAULT 'normal'",
                        )
                        if "SUCCESS" in res:
                            st.success("컬럼 추가 성공!")
                        else:
                            st.error(f"오류 발생: {res}")

                st.markdown(
                    "<div class='section-divider'></div>", unsafe_allow_html=True
                )
                st.markdown(
                    "<h4 style='font-size:15px; font-weight:600; margin-bottom:10px;'>사용자 목록</h4>",
                    unsafe_allow_html=True,
                )
                if st.button("새로고침 (Refresh Data)"):
                    st.cache_data.clear()
                    st.rerun()

                data = fetch_remote_db(ip, "users")

                if data and not ("error" in data[0] if data else False):
                    df = pd.DataFrame(data)
                    if "tier" not in df.columns:
                        df["tier"] = "N/A"
                    st.dataframe(df, use_container_width=True)

                    st.markdown(
                        "<div class='section-divider'></div>", unsafe_allow_html=True
                    )

                    col_u1, col_u2 = st.columns(2, gap="large")

                    with col_u1:
                        st.markdown(
                            "<h4 style='font-size:15px; font-weight:600; margin-bottom:10px;'>회원 등급 변경</h4>",
                            unsafe_allow_html=True,
                        )
                        if not df.empty:
                            target_user = st.selectbox(
                                "사용자 선택",
                                [f"{row['id']}: {row['username']}" for row in data],
                            )
                            new_tier = st.selectbox("변경할 등급", ["normal", "plus"])

                            if st.button(
                                "등급 수정 적용",
                                type="primary",
                                use_container_width=True,
                            ):
                                user_id = target_user.split(":")[0]
                                # args를 이용해 Injection 방어
                                sql = "UPDATE users SET tier = ? WHERE id = ?"
                                res = run_remote_sql(
                                    ip, sql, args=[new_tier, int(user_id)]
                                )

                                if "SUCCESS" in res:
                                    st.success("등급 변경 완료!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"수정 실패: {res}")

                    with col_u2:
                        st.markdown(
                            "<h4 style='font-size:15px; font-weight:600; margin-bottom:10px; color:#ef4444;'>회원 삭제</h4>",
                            unsafe_allow_html=True,
                        )
                        if not df.empty:
                            del_target = st.selectbox(
                                "삭제할 사용자 선택",
                                [f"{row['id']}: {row['username']}" for row in data],
                                key="del",
                            )
                            if st.button(
                                "사용자 삭제 (주의)",
                                type="primary",
                                use_container_width=True,
                            ):
                                user_id = del_target.split(":")[0]
                                sql = "DELETE FROM users WHERE id = ?"
                                res = run_remote_sql(ip, sql, args=[int(user_id)])

                                if "SUCCESS" in res:
                                    st.warning("삭제 완료!")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"삭제 실패: {res}")
                else:
                    st.warning("데이터가 없거나 조회에 실패했습니다.")
            st.markdown("</div>", unsafe_allow_html=True)

        # -------------------------------------------------------------------------
        # 6. 설정 (Settings)
        # -------------------------------------------------------------------------
        elif "설정" in menu:
            st.markdown(
                "<div class='metric-card' style='text-align:left;'>",
                unsafe_allow_html=True,
            )
            st.markdown(
                "<h3 style='font-size:16px; font-weight:700; margin-bottom:15px; color:#111;'>필수 연결 설정</h3>",
                unsafe_allow_html=True,
            )

            if state != "running":
                st.warning("설정을 변경하려면 서버를 먼저 켜주세요.")
            else:
                st.markdown(
                    "<h4 style='font-size:14px; color:#555;'>Ngrok 설정</h4>",
                    unsafe_allow_html=True,
                )
                ngrok_token = st.text_input(
                    "Ngrok 토큰",
                    value=NGROK_AUTHTOKEN if NGROK_AUTHTOKEN else "",
                    type="password",
                )
                if st.button("토큰 등록", type="primary"):
                    if ngrok_token:
                        out, err = ssh_command(
                            ip, f"ngrok config add-authtoken {ngrok_token}"
                        )
                        st.success("Ngrok 토큰 등록 완료!")
                    else:
                        st.error("토큰을 입력해주세요.")

                st.markdown(
                    "<div class='section-divider'></div>", unsafe_allow_html=True
                )
                st.markdown(
                    "<h4 style='font-size:14px; color:#555;'>GitHub 설정</h4>",
                    unsafe_allow_html=True,
                )
                if st.button("SSH 키 확인 / 생성"):
                    out, err = ssh_command(ip, "cat ~/.ssh/id_rsa.pub")
                    if not out or "No such file" in err:
                        ssh_command(
                            ip, "ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa -N ''"
                        )
                        out, _ = ssh_command(ip, "cat ~/.ssh/id_rsa.pub")
                    st.code(out, language="text")
            st.markdown("</div>", unsafe_allow_html=True)

        # 컨텐츠 종료
