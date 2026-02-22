"""
File: chatbot.py
Author: 김다빈
Created: 2026-02-21
Description: AI 면접관 채팅 페이지 (카카오톡 스타일 UI)
             - 텍스트 면접 모드: OpenAI GPT 직접 호출 (STT/TTS 포함)
             - 실시간 음성 면접 모드: OpenAI Realtime API + WebRTC (streamlit-realtime-audio)

Modification History:
- 2026-02-21 (김다빈): 초기 생성 — 카카오톡 스타일 UI, OpenAI GPT 면접 로직
- 2026-02-22 (김다빈): STT(Whisper)/TTS(onyx) 음성 입출력 연동, 면접 종료 시 GPT-4o 피드백
- 2026-02-22 (김다빈): 실시간 음성 면접 모드 추가 (streamlit-realtime-audio + OpenAI Realtime API)
"""

import streamlit as st
import os
import sys
import time
import io

# 외부 패키지 경로
_EXT_PKG_PATH = "/tmp/fw_pkg"
if os.path.isdir(_EXT_PKG_PATH) and _EXT_PKG_PATH not in sys.path:
    sys.path.insert(0, _EXT_PKG_PATH)

from openai import OpenAI

# streamlit-realtime-audio 임포트 (실시간 모드용)
try:
    from st_realtime_audio import realtime_audio_conversation

    _REALTIME_AVAILABLE = True
except ImportError:
    _REALTIME_AVAILABLE = False

# --- 기본 페이지 설정 ---
st.set_page_config(page_title="AI 면접관", page_icon="🤖", layout="centered")

# --- CSS 스타일 적용 (카카오톡 스타일) ---
st.markdown(
    """
<style>
.stApp { background-color: #b2c7d9; }

.ai-message {
    align-self: flex-start;
    background-color: #ffffff; color: #000000;
    padding: 10px 15px; border-radius: 15px; border-top-left-radius: 0;
    max-width: 70%; box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    margin-bottom: 10px; font-size: 15px; line-height: 1.5;
}
.user-message {
    align-self: flex-end;
    background-color: #fef01b; color: #000000;
    padding: 10px 15px; border-radius: 15px; border-top-right-radius: 0;
    max-width: 70%; box-shadow: 0 1px 2px rgba(0,0,0,0.1);
    margin-bottom: 10px; font-size: 15px; line-height: 1.5;
}
.sender-name { font-size: 12px; color: #4a4a4a; margin-bottom: 4px; }

.realtime-status {
    display: inline-block; padding: 6px 16px; border-radius: 20px;
    font-weight: 600; font-size: 14px; margin-bottom: 16px;
}
.status-recording { background: #fee2e2; color: #dc2626; }
.status-connected { background: #dcfce7; color: #16a34a; }
.status-speaking { background: #dbeafe; color: #2563eb; }
.status-idle { background: #f3f4f6; color: #6b7280; }

h1, h2, h3, p, div { color: #333333; }
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
    "interview_mode": None,  # "text" or "realtime"
    "chatbot_started": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ============================================================
# UI
# ============================================================
st.title("🤖 AI 면접관")


# ============================================================
# 면접 시작 전: 모드 선택 + 설정
# ============================================================
if not st.session_state.chatbot_started:
    st.markdown("### ⚙️ 면접 설정")

    mode = st.radio(
        "면접 방식을 선택하세요",
        ["💬 텍스트 면접", "🎙️ 실시간 음성 면접"],
        captions=[
            "타이핑 또는 음성녹음으로 답변. GPT-4o-mini 사용.",
            (
                "실시간 음성 대화. ~300ms 즉시 응답. 자동 턴테이킹. (OpenAI Realtime API)"
                if _REALTIME_AVAILABLE
                else "⚠️ streamlit-realtime-audio 미설치"
            ),
        ],
        index=0,
    )

    is_realtime = "실시간" in mode
    if is_realtime and not _REALTIME_AVAILABLE:
        st.error(
            "streamlit-realtime-audio가 설치되지 않았습니다. `pip install streamlit-realtime-audio`를 실행하세요."
        )
        st.stop()

    st.divider()

    job_role = st.selectbox(
        "💼 직무 선택",
        ["Python 백엔드 개발자", "Java 백엔드", "데이터 엔지니어", "프론트엔드 개발자"],
    )
    difficulty = st.select_slider(
        "🔥 난이도", options=["주니어", "미들", "시니어"], value="미들"
    )
    q_count = st.slider("🔢 문항 수", 3, 10, 5)

    if st.button("▶️ 면접 시작", type="primary", use_container_width=True):
        st.session_state.interview_mode = "realtime" if is_realtime else "text"
        st.session_state.chatbot_started = True
        st.session_state.job_role = job_role
        st.session_state.difficulty = difficulty
        st.session_state.q_count = q_count

        if not is_realtime:
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": "안녕하세요! 저는 AI 면접관입니다. 면접을 시작하기 전, 가볍게 자기소개를 부탁드립니다.",
                }
            )
        st.rerun()

    st.stop()


# ============================================================
# 🎙️ 실시간 음성 면접 모드
# ============================================================
if st.session_state.interview_mode == "realtime":
    job_role = st.session_state.get("job_role", "Python 백엔드 개발자")
    difficulty = st.session_state.get("difficulty", "미들")
    q_count = st.session_state.get("q_count", 5)

    st.markdown("### 🎙️ 실시간 음성 면접")
    st.info(
        "마이크 권한을 허용하면 면접이 시작됩니다. 말을 마치면 AI가 즉시 응답합니다."
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
5. 자연스럽고 전문적인 톤 유지"""

    result = realtime_audio_conversation(
        api_key=api_key,
        instructions=instructions,
        voice="onyx",
        temperature=0.7,
        turn_detection_threshold=0.5,
        auto_start=False,
        key="interview_realtime",
    )

    # 상태 인디케이터
    status = result.get("status", "idle")
    status_map = {
        "idle": ("대기 중", "status-idle"),
        "connecting": ("연결 중...", "status-idle"),
        "connected": ("연결됨 — 마이크 활성화", "status-connected"),
        "recording": ("듣는 중...", "status-recording"),
        "speaking": ("면접관이 말하는 중...", "status-speaking"),
    }
    label, css_class = status_map.get(status, ("알 수 없음", "status-idle"))
    st.markdown(
        f'<span class="realtime-status {css_class}">{label}</span>',
        unsafe_allow_html=True,
    )

    if result.get("error"):
        st.error(f"연결 오류: {result['error']}")

    # 실시간 트랜스크립트
    transcript = result.get("transcript", [])
    if transcript:
        st.markdown("---")
        st.markdown("#### 📝 대화 기록")
        for msg in transcript:
            if msg.get("type") == "user":
                st.markdown(
                    f'<div style="display:flex; justify-content:flex-end;">'
                    f'<div class="user-message">{msg.get("content", "")}</div></div>',
                    unsafe_allow_html=True,
                )
            else:
                content = msg.get("content", "")
                if content:
                    st.markdown(
                        f'<div style="display:flex; justify-content:flex-start;">'
                        f'<div style="display:flex;flex-direction:column;">'
                        f'<div class="sender-name">면접관</div>'
                        f'<div class="ai-message">{content}</div>'
                        f"</div></div>",
                        unsafe_allow_html=True,
                    )

    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🛑 면접 종료", use_container_width=True):
            st.session_state.interview_ended = True
            st.session_state.messages = [
                {"role": m.get("type", "user"), "content": m.get("content", "")}
                for m in transcript
                if m.get("content")
            ]
            st.rerun()
    with col2:
        if transcript:
            script = "\n".join(
                [
                    f"[{'AI 면접관' if m.get('type')=='assistant' else '본인'}] {m.get('content','')}"
                    for m in transcript
                    if m.get("content")
                ]
            )
            st.download_button(
                "📄 스크립트 다운로드",
                script.encode("utf-8"),
                file_name="interview_realtime.txt",
                mime="text/plain",
                use_container_width=True,
            )

    if st.session_state.interview_ended:
        st.success("🎉 면접이 종료되었습니다. 수고하셨습니다!")
        if st.button("🔄 다시 시작하기"):
            for k in defaults:
                st.session_state[k] = defaults[k]
            st.rerun()
    st.stop()


# ============================================================
# 💬 텍스트 면접 모드 (기존 코드 유지)
# ============================================================

# 상단: 토킹헤드 자리 (Placeholder)
with st.container():
    st.markdown("### 🎥 AI Interviewer Video")
    st.video(
        "https://www.w3schools.com/html/mov_bbb.mp4", format="video/mp4", start_time=0
    )
    st.caption("※ 실시간 AI 토킹헤드 및 립싱크 모델 연동 대기 중입니다.")
st.divider()

# 채팅 메시지 렌더링
st.markdown('<div class="chat-container">', unsafe_allow_html=True)
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(
            f'<div style="display:flex; justify-content:flex-end;"><div class="user-message">{message["content"]}</div></div>',
            unsafe_allow_html=True,
        )
    elif message["role"] == "assistant":
        st.markdown(
            f'<div style="display:flex; justify-content:flex-start;"><div style="display:flex; flex-direction:column;"><div class="sender-name">면접관</div><div class="ai-message">{message["content"]}</div></div></div>',
            unsafe_allow_html=True,
        )
st.markdown("</div>", unsafe_allow_html=True)

# TTS 재생
if "latest_audio_content" in st.session_state:
    st.audio(st.session_state.latest_audio_content, format="audio/mp3", autoplay=True)
    del st.session_state.latest_audio_content

# --- 하단 입력 영역 ---
if not st.session_state.interview_ended:
    st.divider()

    prompt = st.chat_input("텍스트로 메시지를 입력하세요.")

    with st.expander("🎙️ 마이크로 음성 답변하기", expanded=False):
        audio_val = st.audio_input(
            "녹음 버튼을 눌러 말씀하신 후 V(완료) 버튼을 눌러주세요."
        )

    user_input_text = ""

    # 1. 오디오 입력 → STT
    if audio_val is not None:
        audio_bytes = audio_val.getvalue()
        audio_hash = hash(audio_bytes)
        if st.session_state.get("last_processed_audio") != audio_hash:
            st.session_state.last_processed_audio = audio_hash
            with st.spinner("음성을 텍스트로 변환하는 중입니다..."):
                try:
                    if client:
                        audio_file = io.BytesIO(audio_bytes)
                        audio_file.name = "audio.wav"
                        transcript = client.audio.transcriptions.create(
                            model="whisper-1", file=audio_file, language="ko"
                        )
                        user_input_text = transcript.text
                    else:
                        user_input_text = "[STT 변환 실패: API 키 없음]"
                except Exception as e:
                    st.error(f"STT 에러: {e}")
                    user_input_text = "[음성 인식 실패]"

    # 2. 텍스트 입력
    elif prompt:
        user_input_text = prompt

    # 3. LLM 응답 + TTS
    if user_input_text:
        st.session_state.messages.append({"role": "user", "content": user_input_text})

        with st.spinner("AI 면접관이 답변을 생성 중입니다..."):
            job_role = st.session_state.get("job_role", "Python 백엔드 개발자")
            difficulty = st.session_state.get("difficulty", "미들")
            q_count = st.session_state.get("q_count", 5)

            system_prompt = {
                "role": "system",
                "content": f"당신은 {job_role} 전문 면접관입니다. 난이도: {difficulty}. "
                f"사용자의 답변에 꼬리질문을 1~2개 던집니다. "
                f"면접이 충분히 진행되면 (대략 {q_count}턴 이상) 마지막에 [INTERVIEW_END] 태그를 붙여주세요.",
            }
            api_messages = [system_prompt] + st.session_state.messages

            try:
                if client:
                    response = client.chat.completions.create(
                        model="gpt-4o-mini", messages=api_messages, max_tokens=500
                    )
                    ai_reply = response.choices[0].message.content
                else:
                    ai_reply = "LLM 연결 실패 (.env의 OPENAI_API_KEY 확인)"
            except Exception as e:
                ai_reply = f"응답 오류: {e}"

            if "[INTERVIEW_END]" in ai_reply:
                st.session_state.interview_ended = True
                ai_reply = ai_reply.replace("[INTERVIEW_END]", "").strip()

            st.session_state.messages.append({"role": "assistant", "content": ai_reply})

            # TTS
            if client:
                try:
                    tts_response = client.audio.speech.create(
                        model="tts-1", voice="onyx", input=ai_reply
                    )
                    st.session_state.latest_audio_content = tts_response.content
                except Exception as e:
                    st.error(f"TTS 오류: {e}")

            st.rerun()

    if st.button("🛑 면접 수동 종료"):
        st.session_state.interview_ended = True
        st.rerun()

else:
    # --- 면접 종료 후 결과 ---
    st.divider()
    st.success("🎉 면접이 종료되었습니다. 수고하셨습니다.")
    st.subheader("💡 면접 결과 및 피드백")

    with st.spinner("결과를 분석 중입니다..."):
        eval_prompt = "다음은 사용자와 AI 면접관의 대화 내역입니다. 합격/불합격, 총점(100점), 강점 2가지, 약점 2가지를 마크다운으로 정리해주세요.\n\n"
        for m in st.session_state.messages[1:]:
            role_str = "면접관" if m["role"] == "assistant" else "지원자"
            eval_prompt += f"{role_str}: {m['content']}\n"

        try:
            if client:
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": eval_prompt}],
                    max_tokens=1000,
                )
                evaluation = response.choices[0].message.content
            else:
                evaluation = "평가 결과 (임시): [API 연동 안됨]"
        except Exception as e:
            evaluation = f"평가 오류: {e}"

    st.markdown(evaluation)

    script_text = "\n".join(
        [
            f"[{'AI 면접관' if m['role']=='assistant' else '본인'}] {m['content']}"
            for m in st.session_state.messages
        ]
    )
    st.download_button(
        "📄 대화 스크립트 다운로드",
        script_text.encode("utf-8"),
        file_name="interview_script.txt",
        mime="text/plain",
    )

    if st.button("🔄 다시 시작하기"):
        for k in defaults:
            st.session_state[k] = defaults[k]
        st.rerun()
