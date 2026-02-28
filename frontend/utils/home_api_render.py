import random

import streamlit as st

from utils.api_utils import api_create_memo, api_get_home_news, api_get_memos


def render_memo_board(current_user_name="anonymous"):
    success, result = api_get_memos(limit=30)
    memos = result.get("items", []) if success else []

    if not memos:
        default_memos = [
            {"author": "AIWORK", "content": "Welcome to AIWORK.", "color": "#FDF4FF", "border": "#FAE8FF", "text_color": "#BB38D0"},
            {"author": "Team", "content": "Leave a short message here.", "color": "#FFF9C4", "border": "#FFF59D", "text_color": "#5D4037"},
        ]
        for memo in default_memos:
            api_create_memo(
                author=memo["author"],
                content=memo["content"],
                color=memo["color"],
                border=memo["border"],
                text_color=memo["text_color"],
            )
        reload_success, reload_result = api_get_memos(limit=30)
        memos = reload_result.get("items", []) if reload_success else default_memos

    with st.container(border=True):
        with st.form("memo_form", clear_on_submit=True):
            col1, col2 = st.columns([8, 2])
            with col1:
                new_memo_text = st.text_input("memo", placeholder="Write a short message", label_visibility="collapsed")
            with col2:
                submitted = st.form_submit_button("Send", use_container_width=True)

            if submitted and new_memo_text.strip():
                colors = [
                    {"color": "#FFF9C4", "border": "#FFF59D", "text_color": "#5D4037"},
                    {"color": "#E8F5E9", "border": "#C8E6C9", "text_color": "#1B5E20"},
                    {"color": "#FCE4EC", "border": "#F8BBD0", "text_color": "#880E4F"},
                    {"color": "#E3F2FD", "border": "#BBDEFB", "text_color": "#0D47A1"},
                ]
                picked = random.choice(colors)
                api_create_memo(
                    author=current_user_name,
                    content=new_memo_text,
                    color=picked["color"],
                    border=picked["border"],
                    text_color=picked["text_color"],
                )
                st.rerun()

    memo_html = "<div style='max-height:450px; overflow-y:auto; padding-top:10px;'>"
    for memo in memos:
        memo_html += (
            f"<div style='background:{memo['color']}; border:1px solid {memo['border']}; "
            f"color:{memo['text_color']}; border-radius:12px; padding:14px; margin-bottom:12px;'>"
            f"<div style='font-size:12px; font-weight:700; margin-bottom:6px;'>{memo['author']}</div>"
            f"<div style='font-size:14px; line-height:1.5;'>{memo['content']}</div>"
            "</div>"
        )
    memo_html += "</div>"
    st.markdown(memo_html, unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner=False)
def _get_cached_news_content():
    success, result = api_get_home_news("latest AI and backend trends")
    return result.get("content", "") if success else ""


def render_realtime_ai_news():
    raw_news = _get_cached_news_content()

    if not raw_news:
        st.info("No news is available right now.")
        return

    news_items = [item.strip() for item in raw_news.split("---") if item.strip()]
    with st.container(height=400, border=True):
        for i, news in enumerate(news_items[:10]):
            st.markdown(
                f"""
                <div style="display:flex; flex-direction:column; gap:4px; padding-bottom:12px; border-bottom:1px solid #f1f5f9; margin-bottom:12px;">
                    <div style="display:flex; align-items:center; gap:6px;">
                        <span style="background:#fdf4ff; color:#bb38d0; padding:2px 8px; border-radius:4px; font-size:10px; font-weight:700;">NEWS {i + 1}</span>
                    </div>
                    <p style="font-size:14px; font-weight:600; color:#111; margin:4px 0; line-height:1.5;">{news}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
