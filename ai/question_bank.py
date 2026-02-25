from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


def _split_tags(tags: Any) -> List[str]:
    if tags is None:
        return []
    if isinstance(tags, list):
        return [str(x).strip() for x in tags if str(x).strip()]
    s = str(tags).strip()
    if not s:
        return []
    return [t.strip() for t in s.split(",") if t.strip()]


def _as_str(v: Any) -> str:
    return "" if v is None else str(v)


def _as_float(v: Any) -> Optional[float]:
    try:
        if v is None or str(v).strip() == "":
            return None
        return float(v)
    except Exception:
        return None


@dataclass(frozen=True)
class QuestionRow:
    id: str
    question: str
    answer: str
    difficulty: str
    topic: str
    subcategory: str
    difficulty_score: Optional[float]
    tags: List[str]
    code_example: str
    time_complexity: str
    space_complexity: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "question": self.question,
            "answer": self.answer,
            "difficulty": self.difficulty,
            "topic": self.topic,
            "subcategory": self.subcategory,
            "difficulty_score": self.difficulty_score,
            "tags": self.tags,  # list로 고정
            "code_example": self.code_example,
            "time_complexity": self.time_complexity,
            "space_complexity": self.space_complexity,
        }


class QuestionBank:
    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self.rows: List[QuestionRow] = []
        self.by_id: Dict[str, QuestionRow] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.csv_path):
            raise FileNotFoundError(f"Question CSV not found: {self.csv_path}")

        with open(self.csv_path, "r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            for r in reader:
                q = QuestionRow(
                    id=_as_str(r.get("id")),
                    question=_as_str(r.get("question")),
                    answer=_as_str(r.get("answer")),
                    difficulty=_as_str(r.get("difficulty")),
                    topic=_as_str(r.get("topic")),
                    subcategory=_as_str(r.get("subcategory")),
                    difficulty_score=_as_float(r.get("difficulty_score")),
                    tags=_split_tags(r.get("tags")),
                    code_example=_as_str(r.get("code_example")),
                    time_complexity=_as_str(r.get("time_complexity")),
                    space_complexity=_as_str(r.get("space_complexity")),
                )
                if not q.id:
                    continue
                self.rows.append(q)
                self.by_id[q.id] = q

    def pick_next(self, asked_ids: List[str]) -> QuestionRow:
        asked = set(str(x) for x in (asked_ids or []))
        for q in self.rows:
            if q.id not in asked:
                return q
        raise RuntimeError("No more questions available (all asked).")


_bank: Optional[QuestionBank] = None


def resolve_default_csv_path() -> str:
    env = os.environ.get("QUESTION_CSV_PATH")
    if env and os.path.exists(env):
        return env

    _base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    candidates = [
        os.path.join(os.getcwd(), "python_interview_questions_500.csv"),
        os.path.join(os.getcwd(), "data", "python_interview_questions_500.csv"),
        os.path.join(os.getcwd(), "backend", "data", "python_interview_questions_500.csv"),
        os.path.join(_base_dir, "backend", "data", "python_interview_questions_500.csv"), # 최상위 폴더 기준 절대경로 추가
    ]
    for p in candidates:
        if os.path.exists(p):
            return p

    return os.path.join(_base_dir, "backend", "data", "python_interview_questions_500.csv")


def get_bank() -> QuestionBank:
    global _bank
    if _bank is None:
        _bank = QuestionBank(resolve_default_csv_path())
    return _bank