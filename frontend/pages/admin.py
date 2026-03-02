"""
File: admin.py
Description: AIWORK 서비스 관리자 대시보드
             회원 관리, 서비스 설정 기능 포함
"""

import streamlit as st
import time
import pandas as pd

from utils.aws_utils import get_instance_info
from utils.ssh_utils import ssh_command
from utils.db_utils import fetch_remote_db, run_remote_sql

st.set_page_config(
    page_title="서비스 관리자",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# --- 인증 및 권한 확인 ---
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
        if not st.session_state.get("_admin_cookie_retry"):
            st.session_state["_admin_cookie_retry"] = True
            time.sleep(0.4)
            st.rerun()
        else:
            del st.session_state["_admin_cookie_retry"]
            st.warning("로그인이 필요합니다.")
            st.stop()

if st.session_state.user.get("role") != "admin":
    st.error("관리자 페이지 접근 권한이 없습니다.")
    st.stop()

admin_name = st.session_state.user.get("name", "관리자")

# --- 커스텀 CSS ---
st.markdown(
    """
<style>
    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap');

    :root { color-scheme: light !important; }

    *, *::before, *::after {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
        box-sizing: border-box;
        color: #111 !important;
    }

    html, body, .stApp,
    [data-testid="stAppViewContainer"],
    [data-testid="stAppViewContainer"] > .main,
    [data-testid="stMain"],
    [data-testid="stHeader"],
    [data-testid="stToolbar"] {
        background: #f0f2f6 !important;
        color: #111111 !important;
        color-scheme: light !important;
    }
    p, span, div, label, h1, h2, h3, h4, h5, h6, li, a, td, th, small, strong, b, i, em, caption { color: #111 !important; }

    /* === Streamlit 내부 컴포넌트 다크모드 차단 === */
    [data-testid="stVerticalBlock"], [data-testid="stHorizontalBlock"],
    [data-testid="stColumn"], [data-testid="stForm"],
    [data-testid="stMarkdownContainer"],
    [data-testid="stRadio"], [data-testid="stRadio"] > div,
    [data-testid="stSelectbox"], [data-testid="stSelectbox"] > div,
    [data-testid="stMetric"], [data-testid="stDataFrame"],
    [data-testid="stTable"] { color: #111 !important; }
    [data-testid="stDialog"] > div > div,
    [data-testid="stDialog"] [data-testid="stVerticalBlockBorderWrapper"],
    [data-testid="stDialog"] [data-testid="stVerticalBlock"],
    section[data-testid="stDialog"] { background-color: #ffffff !important; color: #111 !important; }
    [data-baseweb="input"], [data-baseweb="input"] > div,
    [data-baseweb="select"], [data-baseweb="select"] > div,
    [data-baseweb="textarea"],
    [data-baseweb="popover"] > div,
    [data-baseweb="menu"], [data-baseweb="menu"] li { background-color: #ffffff !important; color: #111 !important; }
    [data-baseweb="radio"] > div > div > div { color: #111 !important; }
    /* === 모든 Streamlit 버튼 배경 강제 === */
    [data-testid="stButton"] > button, [data-testid="stLinkButton"] > a,
    [data-testid="stFormSubmitButton"] > button { background-color: #ffffff !important; color: #111 !important; border: 1px solid #ddd !important; }
    [data-testid="stButton"] > button p, [data-testid="stLinkButton"] > a p { color: #111 !important; }
    button[kind="primary"], [data-testid="stButton"] > button[kind="primary"] {
        background: linear-gradient(135deg, #bb38d0 0%, #872a96 100%) !important; border: none !important; color: white !important;
    }
    button[kind="primary"] p, button[kind="primary"] span { color: #fff !important; }

    /* === 테이블/데이터프레임 배경 강제 (관리자 회원관리 표) === */
    [data-testid="stDataFrame"], [data-testid="stDataFrame"] > div, [data-testid="stDataFrame"] iframe,
    [data-testid="stTable"], [data-testid="stTable"] table,
    [data-testid="stTable"] th, [data-testid="stTable"] td,
    .stDataFrame, .stDataFrame > div { background-color: #ffffff !important; color: #111 !important; }
    [data-testid="stVerticalBlockBorderWrapper"] > div { background-color: transparent !important; }

    [data-testid="stSidebar"] { display: none !important; }
    header[data-testid="stHeader"] { display: none !important; }
    footer { display: none !important; }

    /* 상단 헤더바 */
    .admin-header {
        position: fixed;
        top: 0; left: 0; right: 0;
        height: 60px;
        background: #ffffff;
        border-bottom: 1px solid #e5e7eb;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 40px;
        z-index: 999999;
        box-shadow: 0 1px 4px rgba(0,0,0,0.04);
    }
    .admin-header-logo {
        font-size: 18px;
        font-weight: 800;
        color: #111 !important;
        letter-spacing: -0.5px;
    }
    .admin-header-logo span {
        color: #3b82f6 !important;
    }
    .admin-header-user {
        display: flex;
        align-items: center;
        gap: 12px;
        font-size: 14px;
        color: #555 !important;
    }

    /* 메인 블록 */
    [data-testid="block-container"],
    [data-testid="stMainBlockContainer"] {
        max-width: 1300px !important;
        margin: 80px auto 40px auto !important;
        padding: 0 20px !important;
        background: transparent !important;
        box-shadow: none !important;
        border: none !important;
    }

    /* 좌측 네비 패널 - 컬럼 자체를 카드처럼 스타일링 */
    [data-testid="column"]:first-of-type {
        background: #ffffff !important;
        border-radius: 16px !important;
        border: 1px solid #e5e7eb !important;
        padding: 28px 16px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
        align-self: flex-start !important;
    }

    /* 우측 컨텐츠 컬럼 */
    [data-testid="column"]:not(:first-of-type) {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding-left: 16px !important;
    }
    .nav-brand {
        font-size: 11px;
        font-weight: 700;
        color: #9ca3af !important;
        letter-spacing: 1.5px;
        text-transform: uppercase;
        margin: 0 0 12px 0;
        padding: 0 8px;
    }
    .nav-divider {
        border: none;
        border-top: 1px solid #f0f2f6;
        margin: 16px 0;
    }
    .nav-footer {
        font-size: 12px;
        color: #9ca3af !important;
        padding: 0 8px;
        line-height: 1.6;
    }

    /* 네비 버튼 - 기본 (비활성) */
    [data-testid="column"]:first-of-type .stButton > button {
        display: block !important;
        width: 100% !important;
        text-align: left !important;
        padding: 11px 16px !important;
        background: transparent !important;
        color: #4b5563 !important;
        border: none !important;
        outline: none !important;
        border-radius: 10px !important;
        font-size: 14px !important;
        font-weight: 600 !important;
        cursor: pointer !important;
        transition: background 0.15s ease, color 0.15s ease !important;
        margin-bottom: 4px !important;
        box-shadow: none !important;
        letter-spacing: -0.1px;
    }
    [data-testid="column"]:first-of-type .stButton > button:hover,
    [data-testid="column"]:first-of-type .stButton > button:focus,
    [data-testid="column"]:first-of-type .stButton > button:active {
        background: #e8f0fe !important;
        color: #2563eb !important;
        box-shadow: none !important;
        border: none !important;
        outline: none !important;
    }

    /* 네비 버튼 - 활성 (primary type) */
    [data-testid="column"]:first-of-type .stButton > button[kind="primary"] {
        background: #3b82f6 !important;
        color: #ffffff !important;
        box-shadow: 0 4px 14px rgba(59, 130, 246, 0.35) !important;
        border: none !important;
        outline: none !important;
        font-weight: 700 !important;
    }
    [data-testid="column"]:first-of-type .stButton > button[kind="primary"]:hover,
    [data-testid="column"]:first-of-type .stButton > button[kind="primary"]:focus,
    [data-testid="column"]:first-of-type .stButton > button[kind="primary"]:active {
        background: #2563eb !important;
        color: #ffffff !important;
        box-shadow: 0 6px 18px rgba(59, 130, 246, 0.45) !important;
        border: none !important;
        outline: none !important;
    }

    /* stButton wrapper margin 제거 */
    [data-testid="column"]:first-of-type .stButton {
        margin-bottom: 0 !important;
    }


    /* 우측 컨텐츠 영역 */
    [data-testid="column"]:nth-of-type(2) {
        padding-left: 16px !important;
    }

    /* 페이지 타이틀 */
    .page-title-block {
        margin-bottom: 24px;
    }
    .page-title {
        font-size: 24px !important;
        font-weight: 800 !important;
        color: #111 !important;
        margin: 0 0 4px 0 !important;
    }
    .page-subtitle {
        font-size: 13px !important;
        color: #9ca3af !important;
        margin: 0 !important;
    }

    /* st.container(border=True) — 우측 콘텐츠 영역에만 적용 */
    [data-testid="column"]:not(:first-of-type) [data-testid="stVerticalBlockBorderWrapper"] {
        border-radius: 16px !important;
        border-color: #e5e7eb !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
        background: #fff !important;
        margin-bottom: 16px !important;
    }
    [data-testid="column"]:not(:first-of-type) [data-testid="stVerticalBlockBorderWrapper"] > div {
        padding: 24px 28px !important;
    }
    .card-title {
        font-size: 15px !important;
        font-weight: 700 !important;
        color: #111 !important;
        margin: 0 0 14px 0 !important;
    }
    .settings-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 14px 0;
    }
    .settings-row + .settings-row {
        border-top: 1px solid #f3f4f6;
    }
    .settings-label {
        font-size: 14px !important;
        font-weight: 600 !important;
        color: #374151 !important;
        margin: 0 0 2px 0 !important;
    }
    .settings-desc {
        font-size: 12px !important;
        color: #9ca3af !important;
        margin: 0 !important;
    }
    .settings-badge {
        font-size: 12px;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 20px;
        white-space: nowrap;
    }

    /* 통계 메트릭 카드 */
    .metric-box {
        background: #f9fafb;
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        padding: 20px 24px;
        text-align: center;
    }
    .metric-label {
        font-size: 12px !important;
        font-weight: 600 !important;
        color: #9ca3af !important;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        margin: 0 0 6px 0 !important;
    }
    .metric-value {
        font-size: 28px !important;
        font-weight: 800 !important;
        color: #111 !important;
        margin: 0 !important;
        line-height: 1 !important;
    }
    .metric-desc {
        font-size: 12px !important;
        color: #9ca3af !important;
        margin: 6px 0 0 0 !important;
    }

    /* 뱃지 */
    .badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 99px;
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.2px;
    }
    .badge-active { background: #dcfce7; color: #16a34a; }
    .badge-dormant { background: #fef9c3; color: #ca8a04; }
    .badge-withdrawn { background: #fee2e2; color: #dc2626; }
    .badge-plus { background: #eff6ff; color: #3b82f6; }
    .badge-normal { background: #f3f4f6; color: #6b7280; }

    /* 구분선 */
    .section-sep {
        border: none;
        border-top: 1px solid #f0f2f6;
        margin: 24px 0;
    }

    /* 버튼 */
    .stButton > button {
        background: #ffffff;
        color: #374151;
        border: 1px solid #d1d5db;
        border-radius: 8px;
        font-weight: 600;
        font-size: 14px;
        padding: 8px 16px;
        transition: all 0.15s ease;
    }
    .stButton > button:hover {
        border-color: #3b82f6;
        color: #3b82f6;
        background: #eff6ff;
    }
    .stButton > button[kind="primary"] {
        background: #3b82f6 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px;
        font-weight: 700;
    }
    .stButton > button[kind="primary"]:hover {
        background: #2563eb !important;
    }



    /* 스크롤바 */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #d1d5db; border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: #9ca3af; }

    h1, h2, h3, h4, h5, h6, p, span, div, li, label {
        color: #111111 !important;
    }

    /* 입력 필드 */
    [data-baseweb="input"], [data-baseweb="select"] > div, textarea {
        border: 1px solid #d1d5db !important;
        border-radius: 8px !important;
        background: #ffffff !important;
        transition: all 0.15s ease !important;
    }
    [data-baseweb="input"]:focus-within,
    [data-baseweb="select"] > div:focus-within,
    textarea:focus {
        border-color: #3b82f6 !important;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
    }

    @media (max-width: 768px) {
        [data-testid="block-container"],
        [data-testid="stMainBlockContainer"] {
            padding: 0 10px !important;
            margin-top: 70px !important;
        }
    }
</style>
""",
    unsafe_allow_html=True,
)

# === 상단 헤더 ===
st.markdown(
    f"""
    <div class="admin-header">
        <div class="admin-header-logo">AI<span>WORK</span> &nbsp;
            <span style="font-size:14px; font-weight:400; color:#9ca3af;">관리자 대시보드</span>
        </div>
        <div class="admin-header-user">
            <span style="font-size:13px; color:#6b7280;">{admin_name} 님</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# 메뉴 상태 초기화
if "admin_menu" not in st.session_state:
    st.session_state.admin_menu = "회원 관리"

# === 메인 레이아웃 ===
nav_col, content_col = st.columns([2, 8], gap="medium")

# --- 좌측 네비 ---
with nav_col:
    st.markdown('<p class="nav-brand">메뉴</p>', unsafe_allow_html=True)

    nav_menus = [
        ("회원 관리", "회원 관리"),
        ("서비스 설정", "서비스 설정"),
    ]
    for btn_label, menu_key in nav_menus:
        is_active = st.session_state.admin_menu == menu_key
        btn_type = "primary" if is_active else "secondary"
        if st.button(
            btn_label, key=f"nav_{menu_key}", use_container_width=True, type=btn_type
        ):
            st.session_state.admin_menu = menu_key
            st.rerun()

    st.markdown(
        '<hr class="nav-divider"><p class="nav-footer">AIWORK Admin v1.0</p>',
        unsafe_allow_html=True,
    )

menu = st.session_state.admin_menu

# --- 우측 콘텐츠 ---
with content_col:

    # ─── 서버 정보 조회 (회원 관리에서만 사용) ───
    try:
        info = get_instance_info()
        server_state = info.get("state", "unknown")
        server_ip = info.get("ip", "N/A")
        server_ok = "error" not in info
    except Exception:
        server_ok = False
        server_state = "unknown"
        server_ip = "N/A"

    # =========================================================================
    # 1. 회원 관리
    # =========================================================================
    if "회원 관리" in menu:

        st.markdown(
            """
            <div class="page-title-block">
                <h2 class="page-title">회원 관리</h2>
                <p class="page-subtitle">AIWORK 서비스 사용자 목록을 확인하고 관리합니다.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if not server_ok or server_state != "running":
            st.warning("서버가 실행 중이어야 회원 데이터를 불러올 수 있습니다.")
        else:
            # 데이터 불러오기
            data = fetch_remote_db(server_ip, "users")

            if data and not ("error" in data[0] if data else False):
                df = pd.DataFrame(data)
                if "status" not in df.columns:
                    df["status"] = "active"
                if "tier" not in df.columns:
                    df["tier"] = "normal"

                total = len(df)
                active = (
                    len(df[df["status"] == "active"])
                    if "status" in df.columns
                    else total
                )
                plus_users = (
                    len(df[df["tier"] == "plus"]) if "tier" in df.columns else 0
                )

                # 상단 통계 카드
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.markdown(
                        f"""
                        <div class="metric-box">
                            <p class="metric-label">전체 회원</p>
                            <p class="metric-value">{total:,}</p>
                            <p class="metric-desc">명</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with c2:
                    st.markdown(
                        f"""
                        <div class="metric-box">
                            <p class="metric-label">활성 회원</p>
                            <p class="metric-value" style="color:#16a34a !important;">{active:,}</p>
                            <p class="metric-desc">명</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with c3:
                    st.markdown(
                        f"""
                        <div class="metric-box">
                            <p class="metric-label">Plus 회원</p>
                            <p class="metric-value" style="color:#3b82f6 !important;">{plus_users:,}</p>
                            <p class="metric-desc">명</p>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                # 회원 목록
                st.markdown('<div style="height:16px;"></div>', unsafe_allow_html=True)
                with st.container(border=True):
                    hdr1, hdr2 = st.columns([5, 1])
                    with hdr1:
                        st.markdown(
                            '<p class="card-title">전체 사용자 목록</p>',
                            unsafe_allow_html=True,
                        )
                    with hdr2:
                        if st.button("새로고침", use_container_width=True):
                            st.cache_data.clear()
                            st.rerun()
                    st.dataframe(df, use_container_width=True, height=300)

                # 회원 정보 수정
                with st.container(border=True):
                    st.markdown(
                        '<p class="card-title">회원 정보 수정</p>',
                        unsafe_allow_html=True,
                    )

                    action_col1, action_col2 = st.columns(2, gap="large")

                    # 왼쪽: 회원 등급 변경
                    with action_col1:
                        st.markdown(
                            "<p style='font-size:14px; font-weight:700; color:#374151; margin:0 0 12px 0;'>회원 등급 변경</p>",
                            unsafe_allow_html=True,
                        )
                        target_user_tier = st.selectbox(
                            "대상 사용자",
                            [
                                f"{row['id']}: {row.get('name') or row.get('email') or 'unknown'}"
                                for row in data
                            ],
                            key="tier_select",
                            label_visibility="collapsed",
                        )
                        new_tier = st.selectbox(
                            "변경할 등급",
                            ["normal", "plus"],
                            key="new_tier_select",
                            label_visibility="collapsed",
                        )
                        if st.button(
                            "등급 변경 적용", type="primary", use_container_width=True
                        ):
                            user_id = target_user_tier.split(":")[0]
                            sql = "UPDATE users SET tier = %s WHERE id = %s"
                            res = run_remote_sql(
                                server_ip, sql, args=[new_tier, int(user_id)]
                            )
                            if "SUCCESS" in res:
                                st.success("등급이 성공적으로 변경되었습니다.")
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"수정 실패: {res}")

                    # 오른쪽: 계정 상태 관리
                    with action_col2:
                        st.markdown(
                            "<p style='font-size:14px; font-weight:700; color:#374151; margin:0 0 12px 0;'>계정 상태 관리</p>",
                            unsafe_allow_html=True,
                        )
                        target_user_status = st.selectbox(
                            "대상 사용자",
                            [
                                f"{row['id']}: {row.get('name') or row.get('email') or 'unknown'}"
                                for row in data
                            ],
                            key="status_select",
                            label_visibility="collapsed",
                        )
                        status_dict = {
                            "정상 (active)": "active",
                            "휴면 계정 (dormant)": "dormant",
                            "탈퇴 처리 (withdrawn)": "withdrawn",
                        }
                        selected_status_label = st.selectbox(
                            "변경할 상태",
                            list(status_dict.keys()),
                            label_visibility="collapsed",
                        )
                        if st.button(
                            "상태 변경 적용", type="primary", use_container_width=True
                        ):
                            user_id = target_user_status.split(":")[0]
                            new_status = status_dict[selected_status_label]
                            sql = "UPDATE users SET status = %s WHERE id = %s"
                            res = run_remote_sql(
                                server_ip, sql, args=[new_status, int(user_id)]
                            )
                            if "SUCCESS" in res:
                                if new_status == "withdrawn":
                                    st.warning("해당 계정이 탈퇴 처리되었습니다.")
                                else:
                                    st.success(
                                        f"상태가 '{new_status}'(으)로 변경되었습니다."
                                    )
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(f"변경 실패: {res}")

                    # 관리자 권한 관리
                    st.markdown(
                        '<hr style="border:none;border-top:1px solid #f0f2f6;margin:16px 0;">',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        '<p style="font-size:14px;font-weight:700;color:#374151;margin:0 0 12px 0;">관리자 권한 관리</p>',
                        unsafe_allow_html=True,
                    )

                    admins = [row for row in data if row.get("role") == "admin"]
                    if admins:
                        admin_names = ", ".join(
                            row.get("name") or row.get("email") or f"id:{row['id']}"
                            for row in admins
                        )
                        st.markdown(
                            f'<p style="font-size:12px;color:#6b7280;margin:0 0 12px 0;">현재 관리자: <strong style="color:#3b82f6;">{admin_names}</strong></p>',
                            unsafe_allow_html=True,
                        )

                    role_col1, role_col2 = st.columns([4, 2])
                    with role_col1:
                        user_options_role = [
                            f"{row['id']}: {row.get('name') or row.get('email') or 'unknown'} [{row.get('role','user')}]"
                            for row in data
                        ]
                        target_role_user = st.selectbox(
                            "대상 사용자",
                            user_options_role,
                            key="role_select",
                            label_visibility="collapsed",
                        )
                    with role_col2:
                        rc1, rc2 = st.columns(2)
                        with rc1:
                            if st.button(
                                "관리자 부여",
                                type="primary",
                                use_container_width=True,
                                key="grant_admin",
                            ):
                                uid = int(target_role_user.split(":")[0])
                                res = run_remote_sql(
                                    server_ip,
                                    "UPDATE users SET role = 'admin' WHERE id = %s",
                                    args=[uid],
                                )
                                if "SUCCESS" in res:
                                    st.success("관리자 권한이 부여됐습니다.")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"실패: {res}")
                        with rc2:
                            if st.button(
                                "권한 해제",
                                use_container_width=True,
                                key="revoke_admin",
                            ):
                                uid = int(target_role_user.split(":")[0])
                                res = run_remote_sql(
                                    server_ip,
                                    "UPDATE users SET role = 'user' WHERE id = %s",
                                    args=[uid],
                                )
                                if "SUCCESS" in res:
                                    st.warning("관리자 권한이 해제됐습니다.")
                                    time.sleep(1)
                                    st.rerun()
                                else:
                                    st.error(f"실패: {res}")

            else:
                st.warning(
                    "회원 데이터를 불러올 수 없습니다. 서버 상태를 확인해주세요."
                )

    # =========================================================================
    # =========================================================================
    # 2. 서비스 설정
    # =========================================================================
    elif "서비스 설정" in menu:

        import yaml
        import os

        st.markdown(
            """
        <div class="page-title-block">
            <h2 class="page-title">서비스 설정</h2>
            <p class="page-subtitle">AIWORK 서비스 전반에 걸친 운영 설정을 관리합니다.</p>
        </div>
        """,
            unsafe_allow_html=True,
        )

        settings_path = os.path.join(
            os.path.dirname(__file__), "..", "utils", "admin_settings.yaml"
        )

        def load_settings():
            if os.path.exists(settings_path):
                with open(settings_path, "r", encoding="utf-8") as f:
                    return yaml.safe_load(f) or {}
            return {
                "maintenance_mode": False,
                "system_notice": "",
                "notice_enabled": False,
            }

        def save_settings(data):
            with open(settings_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True)

        gs = load_settings()
        is_maint = gs.get("maintenance_mode", False)
        cur_notice = gs.get("system_notice", "")
        cur_notice_on = gs.get("notice_enabled", False)

        # ── A: 서비스 운영 상태 ──
        s_label = "점검 중" if is_maint else "정상 운영"
        s_color = "#dc2626" if is_maint else "#16a34a"
        s_bg = "#fee2e2" if is_maint else "#dcfce7"
        with st.container(border=True):
            st.markdown(
                f"""
            <div style="display:flex;align-items:center;justify-content:space-between;">
                <p class="card-title" style="margin:0 !important;">서비스 운영 상태</p>
                <span class="settings-badge" style="color:{s_color};background:{s_bg};">{s_label}</span>
            </div>
            """,
                unsafe_allow_html=True,
            )

            mc1, mc2 = st.columns([6, 1])
            with mc1:
                st.markdown(
                    """
                <p class="settings-label">점검 모드</p>
                <p class="settings-desc">켜면 관리자를 제외한 모든 사용자의 접속이 차단됩니다.</p>
                """,
                    unsafe_allow_html=True,
                )
            with mc2:
                new_maint = st.toggle(
                    "점검",
                    value=is_maint,
                    key="toggle_maint",
                    label_visibility="collapsed",
                )

            if new_maint != is_maint:
                gs["maintenance_mode"] = new_maint
                save_settings(gs)
                st.toast("점검 모드 ON" if new_maint else "점검 모드 OFF")
                st.rerun()

        # ── B: 공지사항 배너 ──
        n_label = "노출 중" if cur_notice_on else "비활성"
        n_color = "#059669" if cur_notice_on else "#6b7280"
        n_bg = "#d1fae5" if cur_notice_on else "#f3f4f6"
        with st.container(border=True):
            st.markdown(
                f"""
            <div style="display:flex;align-items:center;justify-content:space-between;">
                <p class="card-title" style="margin:0 !important;">공지사항 배너</p>
                <span class="settings-badge" style="color:{n_color};background:{n_bg};">{n_label}</span>
            </div>
            <p class="settings-desc" style="margin:4px 0 0 0 !important;">홈 화면 상단 배너에 표시됩니다. 내용 입력 후 저장하세요.</p>
            """,
                unsafe_allow_html=True,
            )

            nc1, nc2, nc3 = st.columns([5, 1, 1])
            with nc1:
                notice_text = st.text_input(
                    "공지",
                    value=cur_notice,
                    placeholder="공지사항 내용을 입력하세요",
                    label_visibility="collapsed",
                )
            with nc2:
                is_notice = st.toggle(
                    "노출",
                    value=cur_notice_on,
                    key="toggle_notice",
                    label_visibility="collapsed",
                )
            with nc3:
                if st.button(
                    "저장", type="primary", use_container_width=True, key="save_notice"
                ):
                    gs["system_notice"] = notice_text
                    gs["notice_enabled"] = is_notice
                    save_settings(gs)
                    st.toast("공지사항이 저장되었습니다.")
                    st.rerun()

        # ── C: 시스템 정보 ──
        with st.container(border=True):
            st.markdown('<p class="card-title">시스템 정보</p>', unsafe_allow_html=True)
            st.markdown(
                """
            <div class="settings-row">
                <div>
                    <p class="settings-label">서비스 버전</p>
                    <p class="settings-desc">현재 배포 중인 버전</p>
                </div>
                <span class="settings-badge" style="color:#3b82f6;background:#eff6ff;">v1.0.0</span>
            </div>
            <div class="settings-row">
                <div>
                    <p class="settings-label">운영 환경</p>
                    <p class="settings-desc">현재 서비스 환경</p>
                </div>
                <span class="settings-badge" style="color:#059669;background:#ecfdf5;">Production</span>
            </div>
            """,
                unsafe_allow_html=True,
            )

            sc1, sc2 = st.columns([5, 1])
            with sc1:
                st.markdown(
                    """
                <p class="settings-label">시스템 캐시</p>
                <p class="settings-desc">데이터 갱신이 느릴 때 초기화하세요.</p>
                """,
                    unsafe_allow_html=True,
                )
            with sc2:
                if st.button(
                    "캐시 초기화", use_container_width=True, key="clear_cache"
                ):
                    st.cache_data.clear()
                    st.cache_resource.clear()
                    st.toast("캐시가 초기화되었습니다.")

        # ── D: 계정 (위험 영역) ──
        with st.container(border=True):
            st.markdown(
                '<p class="card-title" style="color:#dc2626 !important;">계정</p>',
                unsafe_allow_html=True,
            )

            lc1, lc2 = st.columns([5, 1])
            with lc1:
                st.markdown(
                    """
                <p class="settings-label">관리자 로그아웃</p>
                <p class="settings-desc">현재 세션을 종료하고 로그인 화면으로 이동합니다.</p>
                """,
                    unsafe_allow_html=True,
                )
            with lc2:
                if st.button("로그아웃", use_container_width=True, key="admin_logout"):
                    st.session_state.clear()
                    st.switch_page("app.py")
