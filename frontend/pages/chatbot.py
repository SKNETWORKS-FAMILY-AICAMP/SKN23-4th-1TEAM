"""
File: chatbot.py
Author: 김다빈
Created: 2026-02-21
Description: AI 면접관 채팅 페이지
             - 텍스트 면접 모드: OpenAI GPT (텍스트 입력 전용)
             - 실시간 음성 면접 모드: OpenAI Realtime API + WebRTC (streamlit-realtime-audio)
               → CSS로 영어 UI 숨김, TTS 음성 자동 출력

Modification History:
- 2026-02-21 (김다빈): 초기 생성
- 2026-02-22 (김다빈): STT/TTS 연동, 면접 종료 시 GPT-4o 피드백
- 2026-02-22 (김다빈): 실시간 음성 면접 모드 추가
- 2026-02-23 (김다빈): 실시간 음성 면접 컴포넌트(JS) 한국어 번역 및 UI 개선
- 2026-02-23 (김다빈): 면접 종료 후 분석 결과 증발 이슈 해결 (세션 상태 캐싱 적용)
"""

import streamlit as st
import os
import sys
import io

# 외부 패키지 경로
_EXT_PKG_PATH = "/tmp/fw_pkg"
if os.path.isdir(_EXT_PKG_PATH) and _EXT_PKG_PATH not in sys.path:
    sys.path.insert(0, _EXT_PKG_PATH)

from openai import OpenAI

# streamlit-realtime-audio 임포트
try:
    from st_realtime_audio import realtime_audio_conversation

    _REALTIME_AVAILABLE = True
except ImportError:
    _REALTIME_AVAILABLE = False

# --- 페이지 설정 ---
st.set_page_config(page_title="AI 면접관", page_icon="🎯", layout="centered")

# ============================================================
# CSS — 라이트 테마 + 실시간 음성 컴포넌트 영어 UI 숨기기
# ============================================================
st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;700&display=swap');

* { font-family: 'Noto Sans KR', sans-serif !important; box-sizing: border-box; }

html, body, .stApp,
[data-testid="stAppViewContainer"],
[data-testid="stAppViewContainer"] > .main {
    background-color: #f5f5f5 !important;
}
[data-testid="stHeader"] { background: transparent !important; }
#MainMenu, footer, header { visibility: hidden; }
[data-testid="stToolbar"] { display: none; }

.block-container {
    max-width: 680px !important;
    padding-top: 1.5rem !important;
    padding-bottom: 5rem !important;
}

h1, h2, h3, p, div, span, label { color: #333 !important; }

/* ─── 카드 ─── */
.setup-card {
    background: #fff;
    border-radius: 16px;
    box-shadow: 0 2px 16px rgba(0,0,0,0.08);
    padding: 36px 32px;
    margin-bottom: 24px;
}
.page-title {
    font-size: 26px; font-weight: 700; color: #bb38d0 !important;
    text-align: center; margin-bottom: 6px;
}
.page-subtitle {
    font-size: 14px; color: #888 !important;
    text-align: center; margin-bottom: 0;
}

/* ─── 채팅 헤더 ─── */
.chat-header {
    display: flex; align-items: center; gap: 12px;
    background: #fff;
    border-radius: 14px;
    box-shadow: 0 1px 8px rgba(0,0,0,0.06);
    padding: 14px 20px;
    margin-bottom: 16px;
}
.chat-header-icon {
    width: 40px; height: 40px; border-radius: 10px;
    background: #bb38d0;
    display: flex; align-items: center; justify-content: center;
    font-size: 18px; color: #fff; flex-shrink: 0;
}
.chat-header-name { font-size: 16px; font-weight: 700; color: #333 !important; }
.chat-header-info { font-size: 12px; color: #999 !important; }

/* ─── 메시지 버블 ─── */
.ai-bubble {
    background: #fff;
    border: 1px solid #eee;
    border-radius: 16px; border-top-left-radius: 4px;
    padding: 14px 18px;
    max-width: 80%;
    color: #333 !important;
    font-size: 15px; line-height: 1.7;
    margin-bottom: 10px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}
.user-bubble {
    background: #bb38d0;
    border-radius: 16px; border-top-right-radius: 4px;
    padding: 14px 18px;
    max-width: 80%;
    color: #fff !important;
    font-size: 15px; line-height: 1.7;
    margin-bottom: 10px;
    box-shadow: 0 2px 8px rgba(187,56,208,0.2);
}
.sender-label {
    font-size: 11px; color: #bb38d0 !important;
    font-weight: 700; margin-bottom: 4px;
}

/* ─── 버튼 ─── */
[data-testid="stButton"] > button[kind="primary"] {
    background-color: #bb38d0 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 8px !important;
    height: 50px !important;
    font-size: 16px !important;
    font-weight: 700 !important;
    transition: background 0.15s;
}
[data-testid="stButton"] > button[kind="primary"]:hover {
    background-color: #a02db5 !important;
}
[data-testid="stButton"] > button[kind="secondary"],
[data-testid="stButton"] > button:not([kind="primary"]) {
    background: #fff !important;
    color: #555 !important;
    border: 1px solid #ddd !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
}

/* ─── 입력 필드 ─── */
[data-testid="stSelectbox"] > div > div {
    background-color: #fafafa !important;
    border: 1px solid #eee !important;
    border-radius: 8px !important;
}
label[data-testid="stWidgetLabel"] > div > p {
    font-size: 13px !important; color: #555 !important;
    font-weight: 500 !important;
}

/* ─── chat_input ─── */
[data-testid="stChatInput"] textarea {
    background: #fafafa !important;
    border: 1px solid #eee !important;
    border-radius: 10px !important;
    color: #333 !important;
}
[data-testid="stChatInput"] button {
    background: #bb38d0 !important;
    border-radius: 8px !important;
}

/* ─── 라디오 ─── */
[data-testid="stRadio"] label span { color: #333 !important; }
[data-testid="stRadio"] label p { color: #888 !important; font-size: 13px !important; }

/* ─── 결과 카드 ─── */
.result-card {
    background: #fff;
    border-radius: 14px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    padding: 28px 24px;
    margin-bottom: 16px;
}
.result-title {
    font-size: 22px; font-weight: 700;
    color: #bb38d0 !important;
    text-align: center; margin-bottom: 16px;
}

hr { border-color: #eee !important; }

/* ─── 상태 인디케이터 ─── */
.realtime-status {
    display: inline-flex; align-items: center; gap: 8px;
    padding: 8px 20px; border-radius: 24px;
    font-weight: 600; font-size: 14px;
    margin: 8px 0 16px 0;
}
.status-idle { background: #f3f4f6; color: #6b7280; }
.status-connected { background: #f0fdf4; color: #16a34a; }
.status-recording { background: #fdf4ff; color: #bb38d0; }
.status-speaking { background: #eff6ff; color: #2563eb; }

.pulse-dot {
    width: 8px; height: 8px; border-radius: 50%;
    background: currentColor; animation: pulse 1.2s infinite;
    display: inline-block;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
}

/* ─── TTS 오디오 플레이어 간소화 ─── */
audio {
    height: 36px !important;
    border-radius: 8px !important;
}

/* ============================================================
   실시간 음성 컴포넌트 영어 UI 숨기기 + 한국어 대체
   streamlit-realtime-audio의 내부 React 요소를 CSS로 덮어씌움
   ============================================================ */

/* iframe 내부 접근이 불가하므로, iframe 자체를 깔끔하게 스타일링 */
iframe[title="st_realtime_audio.realtime_audio_conversation"] {
    border: 2px solid #eee !important;
    border-radius: 14px !important;
    background: #fff !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06) !important;
    min-height: 120px !important;
    max-height: 200px !important;
}

/* 실시간 컴포넌트 안내 카드 */
.realtime-guide {
    background: #fff;
    border: 1px solid #eee;
    border-radius: 12px;
    padding: 16px 20px;
    margin-bottom: 12px;
    font-size: 14px;
    color: #555;
    line-height: 1.6;
}
.realtime-guide strong {
    color: #bb38d0 !important;
}
</style>
""",
    unsafe_allow_html=True,
)

# --- 인증 확인 ---
if "user" not in st.session_state or st.session_state.user is None:
    st.warning("로그인이 필요합니다.")
    st.stop()

# --- OpenAI 클라이언트 ---
try:
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))
except Exception:
    client = None
    st.error("OpenAI API 키가 설정되지 않았습니다.")

# --- Session State 초기화 ---
defaults = {
    "messages": [],
    "interview_ended": False,
    "last_processed_audio": None,
    "interview_mode": None,
    "chatbot_started": False,
    "evaluation_result": None,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v


def build_system_prompt(job_role, difficulty, q_count):
    return {
        "role": "system",
        "content": f"""당신은 {job_role} 포지션 전문 면접관입니다.
난이도: {difficulty} | 총 질문 수: {q_count}개

[면접 진행 규칙]
1. 첫 인사 후 "간단하게 자기소개 부탁드립니다"로 시작
2. 지원자 답변에 대해 짧은 리액션 후 다음 질문
   - 좋은 답변: "네, 좋은 답변이네요."
   - 보통: "네, 이해했습니다."
   - 부족: "조금 더 구체적으로 설명해주실 수 있을까요?"
3. 매 답변마다 꼬리질문 1개로 깊이 확인
4. 충분하면 자연스럽게 새 주제로 전환
5. 기술 질문과 경험 질문을 섞어 출제

[대화 스타일]
- 전문적이면서 따뜻한 톤
- 한 번에 하나의 질문만
- 답변 핵심을 짚어 꼬리질문

[종료 조건]
- {q_count}개 이상 메인 질문 완료 후 마무리
- 마지막에 간단한 총평 + 인사
- 마지막 메시지 끝에 [INTERVIEW_END] 태그 추가""",
    }


def render_message(role, content):
    if role == "user":
        st.markdown(
            f'<div style="display:flex;justify-content:flex-end;margin-bottom:4px;">'
            f'<div class="user-bubble">{content}</div></div>',
            unsafe_allow_html=True,
        )
    elif role == "assistant":
        st.markdown(
            f'<div style="display:flex;justify-content:flex-start;margin-bottom:4px;">'
            f'<div style="display:flex;flex-direction:column;">'
            f'<div class="sender-label">AI 면접관</div>'
            f'<div class="ai-bubble">{content}</div>'
            f"</div></div>",
            unsafe_allow_html=True,
        )


def get_ai_response(messages, job_role, difficulty, q_count):
    sys_prompt = build_system_prompt(job_role, difficulty, q_count)
    api_messages = [sys_prompt] + messages
    try:
        if client:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=api_messages,
                max_tokens=600,
                temperature=0.7,
            )
            return response.choices[0].message.content
        return "LLM 연결 실패 (OPENAI_API_KEY 확인)"
    except Exception as e:
        return f"응답 오류: {e}"


def generate_tts(text):
    if not client:
        return None
    try:
        tts_response = client.audio.speech.create(
            model="tts-1", voice="echo", input=text
        )
        return tts_response.content
    except Exception:
        return None


def generate_evaluation(messages, job_role, difficulty):
    conversation_log = ""
    for m in messages:
        role_str = "면접관" if m["role"] == "assistant" else "지원자"
        conversation_log += f"{role_str}: {m['content']}\n\n"

    eval_prompt = f"""다음은 {job_role} 포지션 기술 면접 대화입니다. 난이도: {difficulty}

아래 형식에 맞춰 면접 평가를 작성해주세요:

## 종합 평가
- **총점**: XX/100점
- **결과**: 합격 / 보류 / 불합격

## 강점
1. (구체적 강점)
2. (구체적 강점)

## 개선이 필요한 부분
1. (구체적 약점 + 개선 방법)
2. (구체적 약점 + 개선 방법)

## 추천 학습 주제
- (면접에서 부족했던 부분 관련 학습 주제 2~3가지)

---
대화 내용:
{conversation_log}"""

    try:
        if client:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": eval_prompt}],
                max_tokens=1200,
            )
            return response.choices[0].message.content
        return "평가 결과를 생성할 수 없습니다."
    except Exception as e:
        return f"평가 오류: {e}"


# ============================================================
# 면접 시작 전: 설정 화면
# ============================================================
if not st.session_state.chatbot_started:
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        """
    <div class="setup-card">
        <div class="page-title">AI 모의면접</div>
        <div class="page-subtitle">실전과 동일한 환경에서 기술 면접을 연습하세요</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    mode_options = ["💬 텍스트 면접"]
    mode_captions = ["타이핑으로 답변합니다. AI 면접관의 응답도 텍스트로 표시됩니다."]

    if _REALTIME_AVAILABLE:
        mode_options.append("🎙️ 실시간 음성 면접")
        mode_captions.append(
            "실시간 음성 대화. AI가 즉시 음성으로 응답합니다. (OpenAI Realtime API)"
        )
    else:
        mode_options.append("🎙️ 음성 면접 (설치 필요)")
        mode_captions.append(
            "streamlit-realtime-audio 미설치. pip install streamlit-realtime-audio"
        )

    mode = st.radio(
        "면접 방식을 선택하세요",
        mode_options,
        captions=mode_captions,
        index=0,
    )

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        job_role = st.selectbox(
            "직무 선택",
            [
                "Python 백엔드 개발자",
                "Java 백엔드 개발자",
                "데이터 엔지니어",
                "프론트엔드 개발자",
            ],
        )
    with col2:
        difficulty = st.selectbox(
            "난이도 선택",
            ["주니어", "미들", "시니어"],
            index=1,
        )

    q_count = st.slider("질문 수", 3, 10, 5)

    st.markdown("<br>", unsafe_allow_html=True)

    is_realtime = "실시간" in mode
    if is_realtime and not _REALTIME_AVAILABLE:
        st.error("streamlit-realtime-audio가 설치되지 않았습니다.")
        st.stop()

    if st.button("면접 시작하기", type="primary", use_container_width=True):
        st.session_state.interview_mode = "realtime" if is_realtime else "text"
        st.session_state.chatbot_started = True
        st.session_state.job_role = job_role
        st.session_state.difficulty = difficulty
        st.session_state.q_count = q_count

        if not is_realtime:
            greeting = (
                "안녕하세요, 반갑습니다. 저는 오늘 면접을 진행하게 된 AI 면접관입니다. "
                "편하게 답변해 주시면 됩니다. 먼저, 간단하게 자기소개를 부탁드립니다."
            )
            st.session_state.messages.append({"role": "assistant", "content": greeting})

        st.rerun()

    st.stop()


# ============================================================
# 면접 종료 — 결과 분석 (공통)
# ============================================================
if st.session_state.interview_ended:
    st.session_state.last_processed_audio = None

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(
        """
    <div class="result-card">
        <div class="result-title">면접 결과 분석</div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    if st.session_state.evaluation_result is None:
        with st.spinner("결과를 분석 중입니다..."):
            st.session_state.evaluation_result = generate_evaluation(
                st.session_state.messages,
                st.session_state.get("job_role", "개발자"),
                st.session_state.get("difficulty", "미들"),
            )

    st.markdown(st.session_state.evaluation_result)

    st.markdown("<br>", unsafe_allow_html=True)

    script_text = "\n".join(
        [
            f"[{'면접관' if m['role'] == 'assistant' else '지원자'}] {m['content']}"
            for m in st.session_state.messages
        ]
    )

    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "대화 스크립트 다운로드",
            script_text.encode("utf-8"),
            file_name="interview_script.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with col2:
        if st.button("다시 시작하기", type="primary", use_container_width=True):
            for k in defaults:
                st.session_state[k] = defaults[k]
            st.rerun()
    st.stop()


# ============================================================
# 🎙️ 실시간 음성 면접 모드 (OpenAI Realtime API)
# ============================================================
if st.session_state.interview_mode == "realtime":
    job_role = st.session_state.get("job_role", "Python 백엔드 개발자")
    difficulty = st.session_state.get("difficulty", "미들")
    q_count = st.session_state.get("q_count", 5)

    # 채팅 헤더
    st.markdown(
        f"""
    <div class="chat-header">
        <div class="chat-header-icon">🎙️</div>
        <div>
            <div class="chat-header-name">AI 면접관 · 실시간 음성</div>
            <div class="chat-header-info">{job_role} · {difficulty} · {q_count}문항</div>
        </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # 한국어 안내 카드 (영어 UI 위에 안내)
    st.markdown(
        """
    <div class="realtime-guide">
        <strong>사용 방법</strong><br>
        아래 <strong>Start</strong> 버튼을 누르면 연결됩니다.<br>
        마이크가 활성화되면 자유롭게 말씀하세요. AI 면접관이 즉시 음성으로 응답합니다.
    </div>
    """,
        unsafe_allow_html=True,
    )

    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        st.error("OPENAI_API_KEY 환경변수가 필요합니다.")
        st.stop()

    instructions = f"""당신은 {job_role} 전문 면접관입니다. 한국어로 기술 면접을 진행하세요.
난이도: {difficulty}. 총 {q_count}개 질문.

규칙:
1. "반갑습니다. 자기소개 부탁드립니다."로 시작
2. 답변에 대해 기술적 꼬리질문 1~2개
3. 각 답변에 간단한 피드백 후 다음 질문
4. {q_count}개 질문 완료 후 종합 평가
5. 자연스럽고 전문적인 톤 유지
6. 반드시 한국어로만 대화"""

    result = realtime_audio_conversation(
        api_key=api_key,
        instructions=instructions,
        voice="echo",
        temperature=0.7,
        turn_detection_threshold=0.5,
        auto_start=False,
        key="interview_realtime",
    )

    # 상태 인디케이터
    status = result.get("status", "idle") if result else "idle"
    status_map = {
        "idle": ("대기 중 — 아래 버튼을 눌러주세요", "status-idle"),
        "connecting": ("연결 중...", "status-idle"),
        "connected": ("연결 완료 — 마이크 활성화", "status-connected"),
        "recording": ("듣는 중...", "status-recording"),
        "speaking": ("면접관이 말하는 중...", "status-speaking"),
    }
    label, css_class = status_map.get(status, ("알 수 없음", "status-idle"))
    st.markdown(
        f'<div class="realtime-status {css_class}">'
        f'<span class="pulse-dot"></span> {label}</div>',
        unsafe_allow_html=True,
    )

    if result and result.get("error"):
        st.error(f"연결 오류: {result['error']}")

    # 실시간 대화 기록
    transcript = result.get("transcript", []) if result else []
    if transcript:
        st.markdown("---")
        st.markdown("**대화 기록**")
        for msg in transcript:
            if msg.get("type") == "user":
                render_message("user", msg.get("content", ""))
            else:
                content = msg.get("content", "")
                if content:
                    render_message("assistant", content)

    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        if st.button("면접 종료하기", use_container_width=True):
            st.session_state.interview_ended = True
            st.session_state.messages = [
                {
                    "role": "assistant" if m.get("type") == "assistant" else "user",
                    "content": m.get("content", ""),
                }
                for m in transcript
                if m.get("content")
            ]
            st.rerun()
    with col2:
        if transcript:
            script = "\n".join(
                [
                    f"[{'AI 면접관' if m.get('type') == 'assistant' else '지원자'}] {m.get('content', '')}"
                    for m in transcript
                    if m.get("content")
                ]
            )
            st.download_button(
                "스크립트 다운로드",
                script.encode("utf-8"),
                file_name="interview_realtime.txt",
                mime="text/plain",
                use_container_width=True,
            )

    st.stop()


# ============================================================
# 💬 텍스트 면접 모드
# ============================================================
job_role = st.session_state.get("job_role", "Python 백엔드 개발자")
difficulty = st.session_state.get("difficulty", "미들")
q_count = st.session_state.get("q_count", 5)

# 채팅 헤더
st.markdown(
    f"""
<div class="chat-header">
    <div class="chat-header-icon">🎯</div>
    <div>
        <div class="chat-header-name">AI 면접관</div>
        <div class="chat-header-info">{job_role} · {difficulty} · {q_count}문항</div>
    </div>
</div>
""",
    unsafe_allow_html=True,
)

# 메시지 렌더링
for message in st.session_state.messages:
    render_message(message["role"], message["content"])

# TTS 자동 재생
if "latest_audio_content" in st.session_state:
    st.audio(st.session_state.latest_audio_content, format="audio/mp3", autoplay=True)
    del st.session_state.latest_audio_content

# 텍스트 입력
prompt = st.chat_input("답변을 입력하세요...")

if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.spinner("면접관이 답변을 준비하고 있습니다..."):
        ai_reply = get_ai_response(
            st.session_state.messages, job_role, difficulty, q_count
        )

        if "[INTERVIEW_END]" in ai_reply:
            st.session_state.interview_ended = True
            ai_reply = ai_reply.replace("[INTERVIEW_END]", "").strip()

        st.session_state.messages.append({"role": "assistant", "content": ai_reply})

    st.rerun()

# 종료 버튼
st.markdown("<br>", unsafe_allow_html=True)
if st.button("면접 종료하기", use_container_width=True):
    st.session_state.interview_ended = True
    st.rerun()
