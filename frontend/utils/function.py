"""
File: function.py
Author: 김지우
Created: 2026-02-26
Description: 기능 함수 모듈

Modification History:
- 2026-02-26 (김지우): 초기 틀 생성
"""
import streamlit as st
import random
import time 
import sys
import os
import base64


# 프로젝트 루트 경로 및 backend 경로 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
frontend_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(frontend_dir)
backend_dir = os.path.join(project_root, "backend")

if project_root not in sys.path:
    sys.path.append(project_root)
if backend_dir not in sys.path:
    sys.path.append(backend_dir)

# 서비스 모듈 임포트
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

# 로컬 이미지를 읽어서 Base64 문자열로 변환하는 함수
def get_image_base64(image_path):
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode("utf-8")

def inject_custom_header():
    import os
    current_dir = os.path.dirname(os.path.abspath(__file__))
    frontend_root = os.path.dirname(current_dir)
    image_path = os.path.join(frontend_root, "assets", "AIWORK.jpg")
    
    # Base64 문자열 생성
    try:
        img_base64 = get_image_base64(image_path)
        # JPEG 이미지일 경우 data:image/jpeg;base64, 를 붙여줍니다.
        img_src = f"data:image/jpeg;base64,{img_base64}"
    except FileNotFoundError:
        st.error(f"이미지 경로를 찾을 수 없습니다: {image_path}")
        img_src = "" # 에러 시 빈 문자열 처리

    # 파이썬 f-string을 사용하기 위해 기존 HTML 문자열을 f""" """ 로 감쌉니다.
    header_html = f"""
    <style>
    /* 상단 여백 조절 */
    .block-container {{
        padding-top: 100px !important; 
    }}
    
    /* 헤더 전체 컨테이너 */
    .custom-header {{
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        height: 72px;
        background-color: #ffffff;
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding: 0 40px;
        border-bottom: 1px solid #e2e8f0;
        z-index: 999999;
        font-family: 'Pretendard', sans-serif;
    }}

    /* 왼쪽 로고 영역 */
    .header-logo {{
        display: flex;
        align-items: center;
        text-decoration: none;
    }}
    .header-logo img {{
        height: 28px; 
        width: auto;
        object-fit: contain;
    }}

    /* 가운데 메뉴 영역 */
    .header-menu {{
        display: flex;
        gap: 40px;
        position: absolute;
        left: 50%;
        transform: translateX(-50%);
    }}
    .header-menu a {{
        text-decoration: none;
        color: #111111;
        font-size: 16px;
        font-weight: 600;
        transition: color 0.2s;
    }}
    .header-menu a:hover {{
        color: #bb38d0; 
    }}

    /* 오른쪽 유틸리티 영역 */
    .header-utils {{
        display: flex;
        align-items: center;
    }}
    .icon-group {{
        display: flex;
        font-size: 24px;
    }}
    .icon-group a {{
        text-decoration: none;
        color: #333333;
        transition: transform 0.2s;
        display: flex;
        align-items: center;
        justify-content: center;
    }}
    .icon-group a:hover {{
        transform: scale(1.1);
    }}
    </style>
    <div class="custom-header">
        <a href="/home" target="_self" class="header-logo">
            <img src="{img_src}" alt="AIWORK 로고">
        </a>
        <div class="header-menu">
            <a href="/interview" target="_self">AI면접</a>
            <a href="/resume" target="_self">이력서</a>
            <a href="/mypage" target="_self">내 기록</a>
            <a href="/my_info" target="_self">마이페이지</a>
        </div>
        <div class="header-utils">
            <div class="icon-group">
                <a href="/my_info" target="_self" title="마이페이지">👤</a>
            </div>
        </div>
    </div>
    """
    st.markdown(header_html, unsafe_allow_html=True)




# home.py (tab1)
def render_memo_board(current_user_name="익명"):
    """
    모두의 메모장 (방명록) UI를 렌더링하는 함수입니다.
    """
    import random
    import sys
    import os
    import streamlit as st

    # DB 경로 임포트 (파일 위치에 따라 조정)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(os.path.dirname(current_dir))
    if project_root not in sys.path:
        sys.path.append(project_root)

    try:
        from backend.db.database import save_memo, get_all_memos
    except Exception as e:
        st.error(f"DB 임포트 에러: {e}")
        return

    # --- 1. DB에서 실시간으로 메모 불러오기 ---
    try:
        memos = get_all_memos(limit=30) # 최신 30개만!
    except Exception as e:
        st.warning(f"메모를 불러오는 중 오류 발생: {e}")
        memos = []

    # DB가 완전히 비어있을 때 보여줄 웰컴 메시지
    if not memos:
        default_memos = [
            {"author": "시스템", "content": "🎉 AIWORK에 오신 것을 환영합니다! 자유롭게 발자취를 남겨주세요.", "color": "#FDF4FF", "border": "#FAE8FF", "text_color": "#BB38D0"},
            {"author": "김다빈", "content": "다들 프로젝트 준비 화이팅입니다!! 💻", "color": "#FFF9C4", "border": "#FFF59D", "text_color": "#5D4037"},
            {"author": "사자개🦁", "content": "크르르르르릉클르컹커커컹ㅋ컬ㅋ", "color": "#E1F5FE", "border": "#B3E5FC", "text_color": "#01579B"},
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
                st.error(f"초기 메모 DB 저장 실패: {e}")
                
        # DB에 저장이 끝났으니 새로 들어간 데이터를 포함해서 다시 불러옵니다!
        try:
            memos = get_all_memos(limit=30)
        except Exception:
            memos = default_memos
            
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
                
                try:
                    save_memo(
                        author=current_user_name,
                        content=new_memo_text,
                        color=picked_color["color"],
                        border=picked_color["border"],
                        text_color=picked_color["text_color"]
                    )
                except Exception as e:
                    st.error(f"메모 저장 실패: {e}")
                
                st.rerun() # 저장 후 즉시 화면 새로고침하여 반영

    # --- 3. 메모장 게시판 렌더링 (HTML/CSS) ---
    memo_html = """
    <style>
    .scrollable-memo-container {
        max-height: 450px; overflow-y: auto; padding-right: 12px; margin-top: 10px;
    }
    .scrollable-memo-container::-webkit-scrollbar { width: 8px; }
    .scrollable-memo-container::-webkit-scrollbar-track { background: transparent; }
    .scrollable-memo-container::-webkit-scrollbar-thumb { background-color: #e2e8f0; border-radius: 10px; }
    .scrollable-memo-container::-webkit-scrollbar-thumb:hover { background-color: #cbd5e1; }
    .memo-board { display: flex; flex-wrap: wrap; gap: 16px; padding-bottom: 20px; }
    .memo-card {
        flex: 1 1 calc(33.333% - 16px); min-width: 220px; padding: 16px;
        border-radius: 2px 16px 16px 16px; box-shadow: 2px 4px 12px rgba(0,0,0,0.05);
        position: relative; transition: transform 0.2s;
    }
    .memo-card:hover { transform: translateY(-4px) rotate(-1deg); box-shadow: 4px 8px 16px rgba(0,0,0,0.08); }
    .memo-author {
        font-size: 12px; font-weight: 700; margin-bottom: 8px;
        border-bottom: 1px dashed rgba(0,0,0,0.1); padding-bottom: 4px;
        display: flex; justify-content: space-between;
    }
    .memo-content { font-size: 14px; line-height: 1.5; font-weight: 500; word-break: keep-all; }
    </style>
    
    <div class="scrollable-memo-container">
        <div class="memo-board">
    """

    for memo in memos:
        # DB에서 가져온 최신 순 데이터로 카드 렌더링
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

        