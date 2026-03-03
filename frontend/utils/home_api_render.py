import random

import streamlit as st

from utils.api_utils import api_create_memo, api_get_home_news, api_get_memos


def render_memo_board(current_user_name="익명"):
    import random
    import sys
    import os
    import streamlit as st

    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    if project_root not in sys.path:
        sys.path.append(project_root)

    try:
        from backend.db.database import save_memo, get_all_memos
    except Exception as e:
        st.error(f"DB Import Error: {e}")
        return

    try:
        memos = get_all_memos(limit=30)
    except Exception as e:
        st.warning(f"Load Error: {e}")
        memos = []

    if not memos:
        default_memos = [
            {"author": "시스템", "content": "AIWORK에 오신 것을 환영합니다! 자유롭게 발자취를 남겨주세요.", "color": "linear-gradient(135deg, #fdf4ff 0%, #ffffff 100%)", "border": "#fae8ff", "text_color": "#bb38d0"},
            {"author": "김다빈", "content": "다들 프로젝트 준비 화이팅입니다!! 💻", "color": "linear-gradient(135deg, #fffbf0 0%, #ffffff 100%)", "border": "#fef08a", "text_color": "#92400e"},
            {"author": "사자개🦁", "content": "크르르르르릉클르컹커커컹ㅋ컬ㅋ", "color": "linear-gradient(135deg, #f0f7ff 0%, #ffffff 100%)", "border": "#dbeafe", "text_color": "#0056b3"},
        ]
        
        for m in default_memos:
            try:
                save_memo(
                    author=m["author"],
                    content=m["content"],
                    color=m["color"],
                    border=m["border"],
                    text_color=m["text_color"]
                )
            except Exception as e:
                st.error(f"Init DB Error: {e}")
                
        try:
            memos = get_all_memos(limit=30)
        except Exception:
            memos = default_memos

        st.markdown(
        """
        <style>
        div[data-testid="stForm"] {
            border: 2px solid #fae8ff !important;
            border-radius: 20px !important;
            padding: 24px !important;
            background: #ffffff !important;
            box-shadow: 0 10px 30px rgba(187, 56, 208, 0.05) !important;
            margin-bottom: 10px !important;
        }
        
        div[data-testid="stForm"] > div > p {
            font-size: 16px !important; font-weight: 800 !important; color: #111 !important; margin-bottom: 8px !important;
        }
        
        div[data-testid="stForm"] input {
            border-radius: 12px !important; border: 1px solid #e2e8f0 !important;
            background: #f8f9fa !important; font-size: 15px !important; padding: 12px !important;
            transition: all 0.2s ease !important;
        }
        div[data-testid="stForm"] input:focus {
            border-color: #bb38d0 !important; box-shadow: 0 0 0 2px rgba(187, 56, 208, 0.1) !important; background: #fff !important;
        }
        
        div[data-testid="stForm"] button {
            background-color: #bb38d0 !important; /* 보라색 배경 */
            border: none !important; 
            border-radius: 10px !important;
            height: 40px !important; 
            min-height: 40px !important;
            padding: 0 16px !important;
            box-shadow: 0 4px 15px rgba(187, 56, 208, 0.2) !important; 
            transition: all 0.2s ease !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
        }
        
        div[data-testid="stForm"] button * {
            color: #ffffff !important; 
            font-weight: 800 !important; 
            font-size: 15px !important;
            margin: 0 !important;
        }
        
        div[data-testid="stForm"] button:hover {
            transform: translateY(-2px) !important; 
            box-shadow: 0 8px 25px rgba(187, 56, 208, 0.3) !important; 
            filter: brightness(1.1);
        }
        div[data-testid="stForm"] button:active {
            transform: translateY(0) !important; 
            box-shadow: 0 4px 10px rgba(187, 56, 208, 0.2) !important;
        }
        </style>
        """, unsafe_allow_html=True
    )

    with st.container():
        with st.form("memo_form", clear_on_submit=True):
            st.markdown("<p><strong>응원의 한마디 남기기</strong></p>", unsafe_allow_html=True)
            c1, c2 = st.columns([8, 2])
            with c1:
                new_memo_text = st.text_input("메모 내용", placeholder="자유롭게 응원의 메시지나 팁을 남겨보세요!", label_visibility="collapsed")
            with c2:
                submit_btn = st.form_submit_button("보내기", use_container_width=True)
                
            if submit_btn and new_memo_text.strip():
                colors = [
                    {"color": "linear-gradient(135deg, #fffbf0 0%, #ffffff 100%)", "border": "#fef08a", "text_color": "#92400e"},
                    {"color": "linear-gradient(135deg, #f2fcf5 0%, #ffffff 100%)", "border": "#d1fae5", "text_color": "#166534"},
                    {"color": "linear-gradient(135deg, #fdf4ff 0%, #ffffff 100%)", "border": "#fae8ff", "text_color": "#872a96"},
                    {"color": "linear-gradient(135deg, #f0f7ff 0%, #ffffff 100%)", "border": "#dbeafe", "text_color": "#0056b3"}
                ]
                picked_color = random.choice(colors)
                
                try:
                    save_memo(
                        author=current_user_name,
                        content=new_memo_text,
                        color=picked_color["color"],
                        border=picked_color["border"],
                        text_color=picked_color["text_color"]
                    )
                except Exception as e:
                    st.error(f"Save Error: {e}")
                
                st.rerun()

    memo_html = """
    <style>

    .scrollable-memo-container {
        padding: 5px 10px 20px 5px; 
        margin-top: 10px;
    }
    
    .memo-board { 
        display: grid; 
        grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); 
        gap: 20px; 
    }
    
    .memo-card {
        padding: 22px;
        border-radius: 20px; 
        box-shadow: 0 8px 24px rgba(0,0,0,0.04);
        position: relative; 
        transition: all 0.3s cubic-bezier(0.25, 0.8, 0.25, 1);
        display: flex;
        flex-direction: column;
        gap: 14px;
        overflow: hidden;
    }
    .memo-card::before {
        content: ''; position: absolute; top: 0; left: 0; width: 100%; height: 4px;
        background: rgba(255,255,255,0.6);
    }
    .memo-card:hover { 
        transform: translateY(-6px); 
        box-shadow: 0 16px 32px rgba(0,0,0,0.08); 
    }
    
    .memo-author {
        font-size: 13px; font-weight: 800; 
        display: inline-flex; align-items: center; gap: 6px;
        background: rgba(255,255,255,0.7); 
        padding: 6px 12px; 
        border-radius: 12px;
        width: fit-content;
        box-shadow: 0 2px 8px rgba(0,0,0,0.02);
    }
    
    .memo-content { 
        font-size: 15px; line-height: 1.6; font-weight: 600; 
        word-break: keep-all; padding-left: 2px;
    }
    </style>
    
    <div class="scrollable-memo-container">
        <div class="memo-board">
    """

    for memo in memos:
        memo_html += f"""
            <div class="memo-card" style="background: {memo['color']}; border: 1px solid {memo['border']}; color: {memo['text_color']};">
                <div class="memo-author">
                    <span>{memo['author']}</span>
                </div>
                <div class="memo-content">{memo['content']}</div>
            </div>
        """

    memo_html += """
        </div>
    </div>
    """

    with st.container(height=275, border=False):
        st.html(memo_html)



@st.cache_data(ttl=3600, show_spinner=False)
def _get_cached_news_content(job_role=None):
    if job_role:
        success, result = api_get_home_news(f"latest AI and {job_role} trends")
    else:
        success, result = api_get_home_news("latest AI and backend trends")
    return result.get("content", "") if success else ""


def render_realtime_ai_news(job_role=None):
    raw_news = _get_cached_news_content(job_role)

    if not raw_news:
        st.info("No news is available right now.")
        return

    news_items = [item.strip() for item in raw_news.split("---") if item.strip()]
    with st.container(height=350, border=True):
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
