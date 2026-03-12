import html
from datetime import datetime

import requests
import streamlit as st

from utils.config import API_BASE_URL
from utils.function import inject_custom_header, require_login


st.set_page_config(page_title="AIWORK Board", page_icon=":memo:", layout="wide")

require_login()
inject_custom_header()


def _auth_headers() -> dict:
    token = st.session_state.get("token")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _safe_text(value: str) -> str:
    return html.escape(str(value or ""))


def _fmt_dt(value: str) -> str:
    if not value:
        return "-"
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(value)


def fetch_questions():
    try:
        res = requests.get(f"{API_BASE_URL.rstrip('/')}/board/questions", timeout=15)
        if res.status_code == 200:
            return True, res.json().get("items", [])
        return False, res.text
    except Exception as e:
        return False, str(e)


def fetch_question_detail(question_id: int, limit: int = 10, offset: int = 0):
    try:
        res = requests.get(
            f"{API_BASE_URL.rstrip('/')}/board/questions/{question_id}",
            params={"limit": limit, "offset": offset},
            headers=_auth_headers(),
            timeout=15,
        )
        if res.status_code == 200:
            return True, res.json()
        return False, res.text
    except Exception as e:
        return False, str(e)


def submit_answer(question_id: int, content: str):
    try:
        res = requests.post(
            f"{API_BASE_URL.rstrip('/')}/board/questions/{question_id}/answers",
            json={"content": content},
            headers=_auth_headers(),
            timeout=15,
        )
        if res.status_code == 200:
            return True, res.json()
        try:
            detail = res.json().get("detail", res.text)
        except Exception:
            detail = res.text
        return False, detail
    except Exception as e:
        return False, str(e)


def toggle_like(answer_id: int):
    try:
        res = requests.post(
            f"{API_BASE_URL.rstrip('/')}/board/answers/{answer_id}/like",
            headers=_auth_headers(),
            timeout=15,
        )
        if res.status_code == 200:
            return True, res.json()
        try:
            detail = res.json().get("detail", res.text)
        except Exception:
            detail = res.text
        return False, detail
    except Exception as e:
        return False, str(e)


if "board_questions" not in st.session_state:
    st.session_state.board_questions = []


st.markdown(
    """
<style>
.board-compose {
    background: #ffffff;
    border: 2px solid #f0ddf5;
    border-radius: 28px;
    padding: 28px 32px;
    margin-bottom: 28px;
}
.compose-title {
    font-size: 20px;
    font-weight: 800;
    color: #111111;
    margin-bottom: 12px;
}
.compose-desc {
    font-size: 15px;
    line-height: 1.8;
    color: #7b8190;
}
.question-card-hook {
    display: none;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.question-card-hook.card-blue) {
    border: 1.5px solid #cfe1ff;
    background: #f7fbff;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.question-card-hook.card-yellow) {
    border: 1.5px solid #f6e189;
    background: #fffdf5;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.question-card-hook.card-pink) {
    border: 1.5px solid #efd6f6;
    background: #fff9ff;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.question-card-hook.card-green) {
    border: 1.5px solid #d5edd7;
    background: #f8fff8;
}
div[data-testid="stVerticalBlockBorderWrapper"]:has(.question-card-hook) {
    border-radius: 28px;
    padding: 24px;
    min-height: 240px;
    margin-bottom: 26px;
    box-shadow: none;
}
.question-badge {
    display: inline-block;
    background: rgba(255,255,255,0.92);
    padding: 12px 18px;
    border-radius: 20px;
    font-size: 14px;
    font-weight: 800;
    color: #111111;
    margin-bottom: 22px;
}
.question-body {
    font-size: 17px;
    font-weight: 800;
    line-height: 1.65;
    color: #111111;
    margin-bottom: 18px;
}
.question-meta {
    font-size: 13px;
    color: #7b8190;
    line-height: 1.6;
}
.question-button-wrap {
    display: block;
}
.question-button-wrap div[data-testid="stButton"] > button {
    min-height: 42px;
    border-radius: 999px;
    border: 1px solid rgba(17,17,17,0.08);
    background: rgba(255,255,255,0.95);
    color: #111111;
    font-weight: 800;
    box-shadow: 0 6px 18px rgba(0,0,0,0.04);
}
.question-button-wrap div[data-testid="stButton"] > button:hover {
    background: #ffffff;
    border-color: #111111;
    color: #111111;
}
.answer-note {
    border-radius: 22px;
    padding: 18px 20px;
    margin-bottom: 14px;
    border: 1px solid #eadff0;
    background: #fffefe;
}
.answer-top {
    border: 2px solid #f0ddf5;
    background: #fff8ff;
}
.answer-author {
    font-size: 13px;
    font-weight: 800;
    color: #111111;
    margin-bottom: 10px;
}
.answer-text {
    font-size: 15px;
    line-height: 1.7;
    color: #222222;
    white-space: pre-wrap;
}
.answer-meta {
    margin-top: 12px;
    font-size: 12px;
    color: #8b95a1;
}
</style>
""",
    unsafe_allow_html=True,
)

ok, result = fetch_questions()
if ok:
    st.session_state.board_questions = result

questions = st.session_state.get("board_questions", [])

if not ok:
    st.error(f"게시판 질문을 불러오지 못했습니다. {result}")
    st.stop()

st.markdown(
    """
<div class="board-compose">
  <div class="compose-title">인성면접 질문 둘러보기</div>
  <div class="compose-desc">
    실제 면접에서 사용했던 표현, 고민 포인트, 답변 방식을 자유롭게 공유해보세요.
    좋아요가 많은 상위 답변을 먼저 보여줍니다.
  </div>
</div>
""",
    unsafe_allow_html=True,
)


@st.dialog("질문 답변 보기", width="large")
def question_dialog(question: dict):
    state_key = f"board_limit_{question['id']}"
    if state_key not in st.session_state:
        st.session_state[state_key] = 10

    limit = int(st.session_state[state_key])
    ok_detail, detail = fetch_question_detail(question["id"], limit=limit, offset=0)
    if not ok_detail:
        st.error(f"답변을 불러오지 못했습니다. {detail}")
        return

    q = detail.get("question", question)
    answers = detail.get("answers", [])
    total_count = int(detail.get("total_count", len(answers)))
    has_more = bool(detail.get("has_more", False))

    top_answers = answers[:2]
    other_answers = answers[2:]

    st.markdown(f"### Q{q.get('display_order', question['id'])}. {q.get('content', '')}")
    st.caption(f"답변 {total_count}개")

    if top_answers:
        st.markdown("#### 좋아요 상위 답변")
        for answer in top_answers:
            st.markdown(
                f"""
<div class="answer-note answer-top">
  <div class="answer-author">{_safe_text(answer.get('author_name', '익명'))} · 상위 답변</div>
  <div class="answer-text">{_safe_text(answer.get('content', ''))}</div>
  <div class="answer-meta">좋아요 {int(answer.get('like_count', 0))} · {_fmt_dt(answer.get('created_at', ''))}</div>
</div>
""",
                unsafe_allow_html=True,
            )
            button_label = "좋아요 취소" if int(answer.get("liked_by_me", 0)) else "좋아요"
            if st.button(button_label, key=f"like_top_{answer['id']}"):
                ok_like, like_result = toggle_like(answer["id"])
                if ok_like:
                    st.toast("좋아요를 반영했습니다.")
                    st.rerun()
                else:
                    st.error(f"좋아요 처리 실패: {like_result}")

    st.markdown("#### 전체 답변")
    if answers:
        render_answers = other_answers if top_answers else answers
        for answer in render_answers:
            st.markdown(
                f"""
<div class="answer-note">
  <div class="answer-author">{_safe_text(answer.get('author_name', '익명'))}</div>
  <div class="answer-text">{_safe_text(answer.get('content', ''))}</div>
  <div class="answer-meta">좋아요 {int(answer.get('like_count', 0))} · {_fmt_dt(answer.get('created_at', ''))}</div>
</div>
""",
                unsafe_allow_html=True,
            )
            button_label = "좋아요 취소" if int(answer.get("liked_by_me", 0)) else "좋아요"
            if st.button(button_label, key=f"like_{answer['id']}"):
                ok_like, like_result = toggle_like(answer["id"])
                if ok_like:
                    st.toast("좋아요를 반영했습니다.")
                    st.rerun()
                else:
                    st.error(f"좋아요 처리 실패: {like_result}")
    else:
        st.info("아직 등록된 답변이 없습니다.")

    if has_more:
        if st.button("답변 더 보기", key=f"more_{question['id']}"):
            st.session_state[state_key] += 10
            st.rerun()

    st.markdown("---")
    st.markdown("#### 답변 작성")
    answer_text = st.text_area(
        "답변 입력",
        key=f"answer_input_{question['id']}",
        height=140,
        placeholder="이 질문에 대한 경험이나 생각을 자유롭게 남겨보세요.",
        label_visibility="collapsed",
    )

    if st.button("보내기", key=f"submit_{question['id']}", use_container_width=True):
        content = (answer_text or "").strip()
        if len(content) < 5:
            st.warning("답변은 5자 이상 입력해주세요.")
        else:
            ok_submit, submit_result = submit_answer(question["id"], content)
            if ok_submit:
                st.toast("답변을 등록했습니다.")
                st.rerun()
            else:
                st.error(f"답변 등록 실패: {submit_result}")

    if st.button("닫기", key=f"close_dialog_{question['id']}"):
        st.rerun()


palette = ["card-blue", "card-yellow", "card-pink", "card-green"]
rows = [questions[i:i + 2] for i in range(0, len(questions), 2)]

for row_idx, row_questions in enumerate(rows):
    cols = st.columns(2)
    for col_idx, col in enumerate(cols):
        if col_idx >= len(row_questions):
            continue

        question = row_questions[col_idx]
        card_class = palette[(row_idx * 2 + col_idx) % len(palette)]
        latest_answer_at = question.get("latest_answer_at") or "아직 답변 없음"

        with col:
            with st.container(border=True):
                st.markdown(
                    f'<div class="question-card-hook {card_class}"></div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="question-badge">질문 {question.get("display_order", 0)}</div>',
                    unsafe_allow_html=True,
                )
                st.markdown(
                    f'<div class="question-body">{_safe_text(question.get("content", ""))}</div>',
                    unsafe_allow_html=True,
                )
                footer_cols = st.columns([3.2, 1.2], gap="medium")
                with footer_cols[0]:
                    st.markdown(
                        f'<div class="question-meta">답변 {int(question.get("answer_count", 0))}개 · 최근 답변 {_safe_text(latest_answer_at)}</div>',
                        unsafe_allow_html=True,
                    )
                with footer_cols[1]:
                    st.markdown('<div class="question-button-wrap">', unsafe_allow_html=True)
                    if st.button("답변 보기", key=f"open_question_{question['id']}", use_container_width=True):
                        question_dialog(question)
                    st.markdown("</div>", unsafe_allow_html=True)

