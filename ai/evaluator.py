from __future__ import annotations

import json
import os
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

_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(dotenv_path=os.path.join(_base_dir, "backend", ".env"))
load_dotenv(dotenv_path=os.path.join(_base_dir, "frontend", ".env"))
load_dotenv(dotenv_path=os.path.join(_base_dir, ".env"))

_api_key = os.environ.get("OPENAI_API_KEY")
if not _api_key:
    # 에러 대신 빈 문자열로 초기화하여 일단 앱이 켜지도록 수정
    _api_key = ""

_client = OpenAI(api_key=_api_key)


def safe_json_parse(text: str) -> Dict[str, Any]:
    t = text.strip()
    start = t.find("{")
    end = t.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("No JSON object found")
    return json.loads(t[start : end + 1])


def evaluate_answer(
    question_row: Dict[str, Any],
    user_answer_text: str,
    rag_context: Dict[str, Any],
    *,
    model: str = "gpt-4.1-mini",
    max_output_tokens: int = 900,
) -> Tuple[Dict[str, Any], str, str]:
    user_prompt = build_eval_user_prompt(question_row, user_answer_text, rag_context)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT_EVAL},
        {"role": "system", "content": EVAL_JSON_SCHEMA_INSTRUCTIONS},
        {"role": "system", "content": EVAL_FEWSHOT},
        {"role": "user", "content": user_prompt},
    ]

    r = _client.responses.create(model=model, input=messages, max_output_tokens=max_output_tokens)
    out_text = getattr(r, "output_text", None) or str(r)

    try:
        parsed = safe_json_parse(out_text)
        return parsed, out_text, ""
    except Exception:
        r2 = _client.responses.create(
            model=model,
            input=[
                {"role": "system", "content": JSON_REPAIR_SYSTEM},
                {"role": "user", "content": out_text},
            ],
            max_output_tokens=max_output_tokens,
        )
        out_text2 = getattr(r2, "output_text", None) or str(r2)
        parsed2 = safe_json_parse(out_text2)
        return parsed2, out_text, out_text2