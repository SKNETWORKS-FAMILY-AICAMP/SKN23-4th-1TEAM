"""
File: frontend/components/chatbot_modal.py
Author: 김지우
Created: 2026-03-11
Description: 사자개(자비스) 가이드 챗봇 모달 컴포넌트 & FAB 버튼

Modification History:
- 2026-03-11 (김지우): home.py에 있던 가이드챗봇 분리 및 모달화
- 2026-03-11 (김지우): 백엔드 제어 신호에 따른 Zero-Click 라우팅 연동
- 2026-03-11 (김지우): 자소서 첨삭 마크다운 렌더링 및 다운로드 구현
- 2026-03-11 (김지우): 퀵 커맨드 칩 제거 및 카카오톡 챗봇 스타일의 인사말 가이드 버튼 UI로 개편
"""
import streamlit as st
import requests
import time

def inject_chatbot_styles():
    st.markdown(
        """
    <style>
    div[data-testid="stModal"] > div[data-testid="stDialog"] { margin: auto !important; }
    div[data-testid="stDialog"] > div > div { border-radius: 24px !important; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15) !important; border: 1px solid rgba(0,0,0,0.05) !important; overflow-y: auto !important; max-height: 85vh !important; }
    div[data-testid="stDialog"] > div > div > div { padding: 32px 36px 28px !important; }
    div[data-testid="stDialog"] h2 { font-weight: 800 !important; font-size: 1.5rem !important; letter-spacing: -0.5px !important; background: linear-gradient(135deg, #bb38d0 0%, #872a96 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 8px !important; }
    
    .advisor-badge { display: inline-flex; align-items: center; gap: 6px; background: #f5f5f7; border: 1px solid #e5e5ea; border-radius: 12px; padding: 4px 10px; font-size: 0.75rem; font-weight: 500; color: #8e8e93; margin-bottom: 24px; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; }
    .advisor-badge::before { content: ''; display: inline-block; width: 6px; height: 6px; border-radius: 50%; background: #34c759; box-shadow: 0 0 4px rgba(52,199,89,0.4); animation: pulse-dot 2s ease-in-out infinite; }
    @keyframes pulse-dot { 0%, 100% { opacity: 1; transform: scale(1); } 50% { opacity: 0.6; transform: scale(0.85); } }
    
    div[data-testid="stDialog"] div[data-testid="stVerticalBlockBorderWrapper"] { background: #ffffff !important; border: none !important; padding: 0 !important; }
    @keyframes msg-pop { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    
    .ai-bubble { background: #f2f3f5; border-radius: 16px 16px 16px 4px; padding: 14px 18px; color: #111 !important; font-size: 15px; line-height: 1.5; white-space: pre-wrap; animation: msg-pop 0.3s ease-out both; display: inline-block; max-width: 100%; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04); border: 1px solid #ebecef; }
    .user-bubble { background: #bb38d0; border-radius: 16px 16px 4px 16px; padding: 14px 18px; color: #ffffff !important; font-size: 15px; line-height: 1.5; white-space: pre-wrap; animation: msg-pop 0.3s ease-out both; display: inline-block; max-width: 100%; box-shadow: 0 4px 14px rgba(187, 56, 208, 0.2); }
    
    /* 가이드 버튼 컨테이너 전용 스타일 (카카오톡 스타일) */
    .guide-btn-wrapper { margin-top: -8px; margin-bottom: 16px; display: flex; flex-direction: column; gap: 6px; }
    .guide-btn-wrapper button { 
        background-color: #ffffff !important; border: 1px solid #e5e8eb !important; color: #333d4b !important;
        border-radius: 12px !important; padding: 12px !important; font-size: 14px !important; font-weight: 600 !important;
        transition: all 0.2s ease !important; text-align: center !important; width: 100% !important; box-shadow: 0 2px 6px rgba(0,0,0,0.02) !important;
    }
    .guide-btn-wrapper button:hover { background-color: #fcf0fc !important; border-color: #bb38d0 !important; color: #bb38d0 !important; transform: translateY(-1px); }
    
    div[data-testid="stChatInput"] { border-radius: 20px !important; border: 1px solid #d1d1d6 !important; background: #ffffff !important; padding: 0px 10px 0px 5px !important; margin-top: 10px !important; margin-bottom: 10px !important; transition: all 0.2s ease-in-out !important; }
    div[data-testid="stChatInput"]:focus-within { border-color: #bb38d0 !important; box-shadow: 0 0 0 1px #bb38d0 !important; }
    div[data-testid="stChatInput"] > div, div[data-testid="stChatInput"] div[data-baseweb="textarea"], div[data-testid="stChatInput"] div[data-baseweb="base-input"] { background-color: transparent !important; border: none !important; }
    div[data-testid="stChatInput"] textarea { background-color: transparent !important; color: #000000 !important; font-size: 15px !important; font-weight: 400 !important; caret-color: #bb38d0 !important; }
    div[data-testid="stChatInput"] textarea::placeholder { color: #adb5bd !important; }
    button[data-testid="stChatInputSubmitButton"] { background: #bb38d0 !important; color: white !important; border-radius: 50% !important; width: 32px !important; height: 32px !important; min-width: 32px !important; display: flex !important; align-items: center !important; justify-content: center !important; transition: all 0.2s ease !important; margin-top: 4px !important; margin-bottom: 4px !important; }
    button[data-testid="stChatInputSubmitButton"]:hover { filter: brightness(1.1) !important; }
    button[data-testid="stChatInputSubmitButton"]:active { transform: scale(0.9) !important; }
    button[data-testid="stChatInputSubmitButton"] svg { fill: #ffffff !important; color: #ffffff !important; width: 18px !important; height: 18px !important; filter: drop-shadow(0 1px 2px rgba(0,0,0,0.2)) !important; }
    </style>
    """,
        unsafe_allow_html=True,
    )

def init_guide_chat_state():
    if "guide_chat" not in st.session_state:
        st.session_state.guide_chat = [
            {
                "role": "assistant",
                "content": "안녕하세요! AIWORK 수석 어드바이저 사자개입니다.\n\n챗봇 이용을 원하실 경우 사용법을 보시려면 아래 버튼을 눌러주세요!",
                "is_greeting": True 
            }
        ]

@st.dialog(" ", width="medium")
def chatbot_modal():
    init_guide_chat_state()
    inject_chatbot_styles()
    
    user_id = st.session_state.get("user", {}).get("id", "anonymous")

    st.markdown(
        """<div style="font-family: -apple-system, BlinkMacSystemFont, sans-serif; text-align: center; margin-bottom: 16px;"> 
        <h2 style="font-weight: 700; font-size: 24px; color: #1d1d1f; letter-spacing: -0.5px; margin: 0 0 8px 0; padding: 0;">AIWORK 가이드 봇</h2> 
        <div class="advisor-badge"> 제로 클릭 네비게이션 적용 </div> </div>""",
        unsafe_allow_html=True,
    )

    chat_container = st.container(height=520)
    clicked_guide = None

    for i, chat in enumerate(st.session_state.guide_chat):
        with chat_container:
            if chat["role"] == "assistant":
                # AI 말풍선 렌더링
                st.markdown(
                    f"""<div style="display:flex; align-items:flex-start; gap:10px; justify-content:flex-start; margin-bottom:8px;">
                        <div style="font-size: 32px; line-height: 1; margin-top: 4px;">🦁</div>
                        <div style="width: 100%; max-width: 85%;">
                            <div style="font-size: 12px; font-weight: 600; color: #888; margin-bottom: 4px; margin-left: 2px;">AI 사자개</div>
                            <div class="ai-bubble" style="width: 100%;">{chat["content"]}</div>
                        </div>
                    </div>""",
                    unsafe_allow_html=True,
                )
                
                if chat.get("is_greeting"):
                    col_spacer, col_btns = st.columns([0.12, 0.88]) 
                    with col_btns:
                        st.markdown('<div class="guide-btn-wrapper">', unsafe_allow_html=True)
                        if st.button("가이드 챗봇 사용법", key=f"guide1_{i}", use_container_width=True): clicked_guide = "가이드 챗봇 사용법 알려줘"
                        if st.button("웹/앱 검색", key=f"guide2_{i}", use_container_width=True): clicked_guide = "웹 검색 기능은 어떻게 사용해?"
                        if st.button("zero-click 사용법", key=f"guide3_{i}", use_container_width=True): clicked_guide = "제로 클릭 기능이 뭐야?"
                        if st.button("원하는 곳 이동법", key=f"guide4_{i}", use_container_width=True): clicked_guide = "원하는 페이지로 이동하는 방법 알려줘"
                        st.markdown('</div>', unsafe_allow_html=True)
                
                # 첨삭 액션일 경우 다운로드 버튼 생성
                if chat.get("action") == "provide_feedback" and chat.get("feedback_content"):
                    st.download_button(
                        label="첨삭 결과 다운로드 (TXT)",
                        data=chat["feedback_content"],
                        file_name="resume_feedback.txt",
                        mime="text/plain",
                        key=f"dl_history_{i}"
                    )
            else:
                # 사용자 말풍선 렌더링
                st.markdown(
                    f"""<div style="display:flex; justify-content:flex-end; margin-bottom:16px;">
                        <div class="user-bubble">{chat["content"]}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )

    # 텍스트 입력창 처리
    prompt = st.chat_input("이동할 곳이나 궁금한 점을 자연스럽게 입력하세요.")
    if clicked_guide:
        prompt = clicked_guide 

    if prompt:
        st.session_state.guide_chat.append({"role": "user", "content": prompt})
        
        # 버튼을 클릭한 경우 즉시 UI 업데이트를 위해 rerun
        if clicked_guide:
            st.rerun()

        with chat_container:
            if not clicked_guide: 
                st.markdown(f"""<div style="display:flex; justify-content:flex-end; margin-bottom:16px;"><div class="user-bubble">{prompt}</div></div>""", unsafe_allow_html=True)

            with st.spinner("요청을 처리 중입니다..."):
                try:
                    api_url = "http://localhost:8000/api/v1/agent/chat"
                    response = requests.post(api_url, json={"message": prompt, "session_id": str(user_id)})
                    response.raise_for_status()
                    data = response.json()
                    
                    action = data.get("action", "chat")
                    target_page = data.get("target_page", "")
                    session_params = data.get("session_params", {})
                    reply_message = data.get("message", "처리가 완료되었습니다.")

                    st.markdown(
                        f"""<div style="display:flex; align-items:flex-start; gap:10px; justify-content:flex-start; margin-bottom:8px;">
                            <div style="font-size: 32px; line-height: 1; margin-top: 4px;">🦁</div>
                            <div style="width: 100%; max-width: 85%;">
                                <div style="font-size: 12px; font-weight: 600; color: #888; margin-bottom: 4px; margin-left: 2px;">AI 사자개</div>
                                <div class="ai-bubble" style="width: 100%;">{reply_message}</div>
                            </div>
                        </div>""",
                        unsafe_allow_html=True,
                    )
                    
                    feedback_content = session_params.get("feedback_result", "")
                    
                    st.session_state.guide_chat.append({
                        "role": "assistant", 
                        "content": reply_message,
                        "action": action,
                        "feedback_content": feedback_content
                    })

                    if action == "provide_feedback" and feedback_content:
                        st.download_button(
                            label="첨삭 결과 다운로드 (TXT)",
                            data=feedback_content,
                            file_name="resume_feedback.txt",
                            mime="text/plain",
                            key=f"dl_new_{len(st.session_state.guide_chat)}"
                        )

                    # 페이지 라우팅 분기
                    if action == "navigate" and target_page:
                        st.success(f"{reply_message}")
                        time.sleep(1.2)
                        
                        if target_page == "interview":
                            st.session_state["job_role"] = session_params.get("job_role", "기본 직무")
                            st.session_state["difficulty"] = session_params.get("difficulty", "중")
                            st.session_state["persona"] = session_params.get("persona", "깐깐한 기술팀장")
                            st.session_state["use_resume"] = session_params.get("use_resume", False)
                            st.session_state["jarvis_trigger"] = True 
                            st.session_state["chatbot_started"] = False 
                            st.switch_page("pages/interview.py")
                            
                        elif target_page == "resume": st.switch_page("pages/resume.py")
                        elif target_page == "mypage": st.switch_page("pages/mypage.py")
                        elif target_page == "my_info": st.switch_page("pages/my_info.py")
                        elif target_page == "home": st.rerun()

                except Exception as e:
                    error_msg = f"서버 통신 오류가 발생했습니다: {e}"
                    st.error(error_msg)
                    st.session_state.guide_chat.append({"role": "assistant", "content": error_msg})

@st.fragment
def render_fab_button():
    st.markdown('<div id="fab-marker"></div>', unsafe_allow_html=True)
    if st.button("chatbot_trigger_btn", key="fab_btn"):
        chatbot_modal()