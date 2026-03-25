from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from backend.db.database import get_connection

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
            "tags": self.tags,
            "code_example": self.code_example,
            "time_complexity": self.time_complexity,
            "space_complexity": self.space_complexity,
        }


class QuestionBank:
    def __init__(self):
        pass

    def pick_next(self, asked_ids: List[str]) -> QuestionRow:
        asked = [str(x) for x in (asked_ids or [])]
        placeholders = ",".join(["%s"] * len(asked)) if asked else "''"
        
        query = """
            SELECT id, content AS question, reference_answer AS answer, 
                   difficulty, skill_tag AS topic, 
                   question_type AS subcategory, keywords AS tags
            FROM question_pool
        """
        
        if asked:
            query += f" WHERE id NOT IN ({placeholders})"
            
        query += " ORDER BY RAND() LIMIT 1"
        
        with get_connection() as conn:
            with conn.cursor() as cur:
                if asked:
                    cur.execute(query, tuple(asked))
                else:
                    cur.execute(query)
                    
                row = cur.fetchone()
                
                if not row:
                    raise RuntimeError("No more questions available (all asked).")
                
                return QuestionRow(
                    id=str(row["id"]),
                    question=_as_str(row.get("question")),
                    answer=_as_str(row.get("answer")),
                    difficulty=_as_str(row.get("difficulty")),
                    topic=_as_str(row.get("topic")),
                    subcategory=_as_str(row.get("subcategory")),
                    difficulty_score=None,
                    tags=_split_tags(row.get("tags")),
                    code_example="",
                    time_complexity="",
                    space_complexity="",
                )


_bank: Optional[QuestionBank] = None


def get_bank() -> QuestionBank:
    global _bank
    if _bank is None:
        _bank = QuestionBank()
    return _bank
