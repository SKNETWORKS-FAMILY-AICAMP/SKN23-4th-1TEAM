import os
import json
from typing import Any, Dict, Tuple

from dotenv import load_dotenv
from openai import OpenAI

from ai.prompts import (
    SYSTEM_PROMPT_EVAL,
    EVAL_JSON_SCHEMA_INSTRUCTIONS,
    EVAL_FEWSHOT,
    JSON_REPAIR_SYSTEM,
    build_eval_user_prompt,
)

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))

api_key = os.environ.get("OPENAI_API_KEY")
if not api_key:
    raise RuntimeError("OPENAI_API_KEY not found. Put it in root/.env")

client = OpenAI(api_key=api_key)

# 저장용 한글 키 변환
KEY_MAP = {
    "question_id": "질문_id",
    "score": "점수",
    "pass_threshold": "합격_기준점수",
    "passed": "합격여부",
    "feedback": "총평",
    "strengths": "잘한점",
    "weaknesses": "아쉬운점",
    "missing_points": "누락_핵심포인트",
    "follow_up_needed": "꼬리질문_필요여부",
    "follow_up_question": "꼬리질문",
    "rubric_hits": "루브릭_점수",
    "clarity": "명확성",
    "correctness": "정확성",
    "depth": "깊이",
    "structure": "구조",
    "metadata_used": "메타데이터",
    "difficulty": "난이도",
    "topic": "주제",
    "subcategory": "세부주제",
    "difficulty_score": "난이도_점수",
    "tags": "태그",
    "time_complexity": "시간복잡도",
    "space_complexity": "공간복잡도",
    "evidence": "근거",
    "claim": "판단",
    "support": "근거_요약",
}

def to_korean_keys(obj: Any) -> Any:
    """dict/list를 재귀적으로 순회하며 KEY_MAP에 있는 키만 한글로 변환(저장용)."""
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            nk = KEY_MAP.get(k, k)
            out[nk] = to_korean_keys(v)
        return out
    if isinstance(obj, list):
        return [to_korean_keys(x) for x in obj]
    return obj


def safe_json_parse(text: str) -> Dict[str, Any]:
    """모델이 JSON 앞뒤로 텍스트를 붙였을 때를 대비한 최소 방어 파서."""
    t = text.strip()
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found")
    return json.loads(t[start : end + 1])


def write_text(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def call_eval(
    question_list_row: dict,
    user_answer_text: str,
    rag_context: dict,
) -> Tuple[Dict[str, Any], str, str]:
    """
    return: (parsed_json, out_text, out_text2)
    - out_text: 1차 모델 원문
    - out_text2: 리페어 모델 원문(사용 안 했으면 "")
    """
    user_prompt = build_eval_user_prompt(question_list_row, user_answer_text, rag_context)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_EVAL},
        {"role": "system", "content": EVAL_JSON_SCHEMA_INSTRUCTIONS},
        {"role": "system", "content": EVAL_FEWSHOT},
        {"role": "user", "content": user_prompt},
    ]

    # 1차 호출
    r = client.responses.create(
        model="gpt-4.1-mini",
        input=messages,
        max_output_tokens=700,
    )
    out_text = getattr(r, "output_text", None) or str(r)

    # JSON 파싱 시도
    try:
        parsed = safe_json_parse(out_text)
        return parsed, out_text, ""
    except Exception:
        # JSON 깨졌으면 1회 리페어
        r2 = client.responses.create(
            model="gpt-4.1-mini",
            input=[
                {"role": "system", "content": JSON_REPAIR_SYSTEM},
                {"role": "user", "content": out_text},
            ],
            max_output_tokens=700,
        )
        out_text2 = getattr(r2, "output_text", None) or str(r2)
        parsed2 = safe_json_parse(out_text2)
        return parsed2, out_text, out_text2


def prompt_multiline_input(label: str) -> str:
    """
    여러 줄 입력 지원:
    - 빈 줄을 한 번 입력하면 종료
    """
    print(f"\n[{label}] 여러 줄 입력 가능. 빈 줄(Enter) 입력 시 종료")
    lines = []
    while True:
        line = input()
        if line == "":
            break
        lines.append(line)
    return "\n".join(lines).strip()


def main():
    # 테스트용 샘플(질문 row + RAG context)
    # 실제 프로젝트에서는 이 부분을 "CSV에서 id로 찾기"로 변경.
    question_list_row = {
        "id": "305",
        "question": "파이썬 GIL(Global Interpreter Lock)이 무엇이며 어떤 영향이 있나요?",
        "answer": "CPython에서 한 시점에 하나의 스레드만 바이트코드를 실행하도록 제한하는 락. "
                  "CPU-bound 작업에서 멀티스레딩 성능 이점이 제한될 수 있고, "
                  "I/O-bound에서는 유효할 수 있다. 멀티프로세싱으로 우회 가능.",
        "difficulty": "medium",
        "topic": "python_internals",
        "subcategory": "concurrency",
        "difficulty_score": 0.7,
        "tags": "GIL,CPython,threading,multiprocessing,IO-bound,CPU-bound",
        "code_example": "",
        "time_complexity": "",
        "space_complexity": "",
    }

    rag_context = {
        "rubric": {
            "correctness": "정확한 정의와 영향 범위 구분",
            "depth": "CPU-bound vs I/O-bound 차이, 우회 방법 언급",
            "structure": "정의→영향→대안 순서",
            "clarity": "핵심을 짧고 명확히",
        },
        "chunks": [],
    }

    print("\n=== QUESTION ===")
    print(f"[{question_list_row['id']}] {question_list_row['question']}")

    # STT/TTS 없으므로 콘솔에서 직접 답변 입력
    user_answer_text = prompt_multiline_input("USER_ANSWER_STT")
    if not user_answer_text:
        print("입력된 답변이 없습니다. 종료합니다.")
        return

    result_json, out_text, out_text2 = call_eval(question_list_row, user_answer_text, rag_context)

    # 모델 원문 저장(원인 분석용)
    write_text("ai/_debug_last_out_text.txt", out_text)
    if out_text2:
        write_text("./_debug_last_out_text2_repair.txt", out_text2)

    # 저장할 결과 JSON의 키만 한글로 변환 저장
    result_korean = to_korean_keys(result_json)

    with open("ai/평가결과_한글.json", "w", encoding="utf-8") as f:
        json.dump(result_korean, f, ensure_ascii=False, indent=2)

    # 영문 평가, 한글평가 둘다 반환
    return {'Eng':result_json, 'Kor':result_korean}

if __name__ == "__main__":
    main()