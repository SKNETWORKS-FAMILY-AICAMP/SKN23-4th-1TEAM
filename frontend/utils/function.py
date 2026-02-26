# 파일 경로: utils/function.py

import streamlit as st
import random
import time 
import sys
import os


# 1. 프로젝트 루트 경로 및 backend 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(frontend_dir)
backend_dir = os.path.join(project_root, "backend")

if project_root not in sys.path:
    sys.path.append(project_root)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# 2. 서비스 모듈 임포트
try:
    from backend.services.tavily_service import get_web_context
except ImportError as e:
    st.error(f"서비스를 불러오는 중 에러가 발생했습니다: {e}")

# Gemini/OpenAI 설정 (직접 번역용)
from openai import OpenAI
try:
    client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
except Exception:
    pass



def render_memo_board(current_user_name="익명"):
    """
    모두의 메모장 (방명록) UI를 렌더링하는 함수입니다.
    현재는 st.session_state를 이용해 프론트엔드 단에서만 임시 저장됩니다.
    """
    
    # --- 1. 메모장 데이터 초기화 ---
    if "memos" not in st.session_state:
        st.session_state.memos = [
            {"author": "시스템", "content": "🎉 AIWORK에 오신 것을 환영합니다! 자유롭게 발자취를 남겨주세요.", "color": "#FDF4FF", "border": "#FAE8FF", "text_color": "#BB38D0"},
            {"author": "김다빈", "content": "다들 프로젝트 준비 화이팅입니다!! 💻", "color": "#FFF9C4", "border": "#FFF59D", "text_color": "#5D4037"},
            {"author": "익명", "content": "어제 백엔드 직무 모의면접 해봤는데 꼬리질문 진짜 매섭네요... 덜덜", "color": "#E1F5FE", "border": "#B3E5FC", "text_color": "#01579B"},
        ]

    # --- 2. 메모 입력 폼 ---
    with st.container(border=True):
        st.markdown("<p style='font-size:16px; font-weight:700; color:#111; margin-bottom:10px;'>댓글</p>", unsafe_allow_html=True)
        
        with st.form("memo_form", clear_on_submit=True):
            c1, c2 = st.columns([8, 2])
            with c1:
                new_memo_text = st.text_input("메모 내용", placeholder="자유롭게 응원의 메시지나 팁을 남겨보세요!", label_visibility="collapsed")
            with c2:
                submit_btn = st.form_submit_button("보내기", use_container_width=True)
                
            if submit_btn and new_memo_text.strip():
                # 랜덤 포스트잇 색상 지정
                colors = [
                    {"color": "#FFF9C4", "border": "#FFF59D", "text_color": "#5D4037"},
                    {"color": "#E8F5E9", "border": "#C8E6C9", "text_color": "#1B5E20"},
                    {"color": "#FCE4EC", "border": "#F8BBD0", "text_color": "#880E4F"},
                    {"color": "#E3F2FD", "border": "#BBDEFB", "text_color": "#0D47A1"}
                ]
                picked_color = random.choice(colors)
                
                # 새 메모를 리스트의 맨 앞(0번 인덱스)에 추가
                st.session_state.memos.insert(0, {
                    "author": current_user_name,
                    "content": new_memo_text,
                    "color": picked_color["color"],
                    "border": picked_color["border"],
                    "text_color": picked_color["text_color"]
                })
                
                # ✨ 선입선출 (FIFO): 메모가 30개를 초과하면 가장 오래된(맨 뒤에 있는) 메모 삭제
                if len(st.session_state.memos) > 30:
                    st.session_state.memos = st.session_state.memos[:30]
                    
                st.rerun()

    # --- 3. 메모장 게시판 렌더링 (HTML/CSS) ---
    memo_html = """
    <style>
    /* ✨ 스크롤이 가능한 전체 컨테이너 설정 */
    .scrollable-memo-container {
        max-height: 450px; /* 이 높이를 넘어가면 스크롤이 생깁니다 */
        overflow-y: auto;
        padding-right: 12px;
        margin-top: 10px;
    }
    
    /* 스크롤바 예쁘게 다듬기 (Webkit 브라우저 전용) */
    .scrollable-memo-container::-webkit-scrollbar {
        width: 8px;
    }
    .scrollable-memo-container::-webkit-scrollbar-track {
        background: transparent;
    }
    .scrollable-memo-container::-webkit-scrollbar-thumb {
        background-color: #e2e8f0;
        border-radius: 10px;
    }
    .scrollable-memo-container::-webkit-scrollbar-thumb:hover {
        background-color: #cbd5e1;
    }

    .memo-board {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        padding-bottom: 20px;
    }
    .memo-card {
        flex: 1 1 calc(33.333% - 16px);
        min-width: 220px;
        padding: 16px;
        border-radius: 2px 16px 16px 16px;
        box-shadow: 2px 4px 12px rgba(0,0,0,0.05);
        position: relative;
        transition: transform 0.2s;
    }
    .memo-card:hover {
        transform: translateY(-4px) rotate(-1deg);
        box-shadow: 4px 8px 16px rgba(0,0,0,0.08);
    }
    .memo-author {
        font-size: 12px;
        font-weight: 700;
        margin-bottom: 8px;
        border-bottom: 1px dashed rgba(0,0,0,0.1);
        padding-bottom: 4px;
        display: flex;
        justify-content: space-between;
    }
    .memo-content {
        font-size: 14px;
        line-height: 1.5;
        font-weight: 500;
        word-break: keep-all;
    }
    </style>
    
    <div class="scrollable-memo-container">
        <div class="memo-board">
    """

    for memo in st.session_state.memos:
        memo_html += f"""
            <div class="memo-card" style="background-color: {memo['color']}; border: 1px solid {memo['border']}; color: {memo['text_color']};">
                <div class="memo-author">
                    <span>👤 {memo['author']}</span>
                </div>
                <div class="memo-content">{memo['content']}</div>
            </div>
        """

    memo_html += """
        </div>
    </div>
    """
    st.html(memo_html)
    st.write("")


# ================== (Tavily) 뉴스 데이터 가져오는거 실험중 =====================
def get_translated_news_summary(raw_news_data: str) -> str:
    """Tavily 검색 결과(주로 영문)를 한국어로 번역하고 요약하여 뉴스 대시보드 형태로 반환합니다."""
    prompt = f"""
당신은 IT 전문 뉴스 에디터입니다. 
아래 제공된 [검색 결과]를 바탕으로, 한국의 개발자들이 읽기 좋게 '최신 AI 및 백엔드 트렌드 10가지'를 작성해주세요.

[지침]:
1. 반드시 한국어로 작성할 것.
2. 검색 결과를 바탕으로 반드시 딱 10개의 핵심 뉴스를 추출할 것.
3. 각 뉴스는 2~3문장으로 핵심만 요약해서 퀄리티 있게 적어줄 것.
4. 기술적인 용어는 적절히 설명하거나 한국어 통용어로 번역할 것.
5. 절대로 마크다운 기호(**, # 등)나 번호 표기(1., 2.)를 쓰지 마세요. 
6. 오직 각 뉴스 항목들을 `---` 이라는 세 개의 하이픈으로만 구분해서 출력하세요.

예시 포맷:
내용 요약 문장 첫번째 블록입니다.
---
내용 요약 문장 두번째 블록입니다.
---

[검색 결과]:
{raw_news_data}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini", # 또는 사용하시는 모델명 (예: gpt-4o-mini)
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.6
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"LLM 번역 에러: {e}")
        return ""

def render_realtime_ai_news():
    """Tavily를 활용해 최신 AI 소식을 카드로 렌더링 (한글 + 스크롤 지원)"""
    import streamlit as st

    # 1. Tavily 검색 실행
    query = "2026년 최신 AI 및 백엔드 기술 트렌드 10가지"
    
    try:
        with st.spinner("실시간 AI 트렌드를 분석중 ..."):
            raw_news = get_web_context(query)
            
            # 2. 강력하게 제어된 프롬프트로 LLM에게 10개 번역/요약을 요청
            raw_news = get_translated_news_summary(raw_news)
            
        if raw_news:
            st.markdown(f"**2026년 2월 26일 실시간 브리핑**")
            
            # 텍스트를 LLM이 만들기로 약속한 '---' 구분자로 정확히 자릅니다.
            news_items = [item.strip() for item in raw_news.split('---') if len(item.strip()) > 5]
            
            # 💡 높이가 450px로 고정된 스크롤 컨테이너 생성!
            with st.container(height=450, border=True):
                
                # 최대 10개까지만 가져와서 반복문으로 그리기
                for i, news in enumerate(news_items[:10]): 
                    st.markdown(
                        f"""
                        <div style="display: flex; flex-direction: column; gap: 4px; padding-bottom: 12px; border-bottom: 1px solid #f1f5f9; margin-bottom: 12px;">
                            <div style="display: flex; align-items: center; gap: 6px;">
                                <span style="background: #fdf4ff; color: #bb38d0; padding: 2px 8px; border-radius: 4px; font-size: 10px; font-weight: 700;">NEWS {i+1}</span>
                            </div>
                            <p style="font-size: 14px; font-weight: 600; color: #111; margin: 4px 0; line-height: 1.5;">
                                {news}
                            </p>
                        </div>
                        """, unsafe_allow_html=True
                    )
        else:
            st.info("현재 새로운 소식이 없습니다. 잠시 후 다시 확인해주세요.")
            
    except Exception as e:
        st.error(f"뉴스 연결 실패: {e}")

        