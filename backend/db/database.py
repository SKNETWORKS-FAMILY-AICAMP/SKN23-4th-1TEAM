"""
File: db/database.py
Author: 김지우
Created: 2026-02-27
Description: DB 모델들의 기본 뼈대

Modification History:
- 2026-02-24: 벡엔드 DB 모델 정의
- 2026-02-27 (김지우) :  기존 User 모델 외에 직무 분류, 질문 풀, 면접 기록 테이블 추가
"""

import os
import json
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from dotenv import load_dotenv

current_file_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_file_dir)
env_path = os.path.join(backend_dir, ".env")

load_dotenv(dotenv_path=env_path, override=True)

# DB 연결 설정 (.env에서 읽기)
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "port": int(os.getenv("DB_PORT", "3306")),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "db": os.getenv("DB_NAME", "ai_interview"),
    "charset": "utf8mb4",
    "cursorclass": DictCursor,
}

# DDL
DDL = """
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) COLLATE utf8mb4_unicode_ci NOT NULL UNIQUE,
    provider VARCHAR(20) COLLATE utf8mb4_unicode_ci DEFAULT NULL,          
    provider_user_id VARCHAR(128) COLLATE utf8mb4_unicode_ci DEFAULT NULL,  
    role VARCHAR(20) COLLATE utf8mb4_unicode_ci DEFAULT 'user',             
    name VARCHAR(100) COLLATE utf8mb4_unicode_ci NULL,                      
    password VARCHAR(255) COLLATE utf8mb4_unicode_ci NULL,                  
    tier VARCHAR(20) COLLATE utf8mb4_unicode_ci DEFAULT 'normal',           
    status VARCHAR(20) COLLATE utf8mb4_unicode_ci DEFAULT 'active',         
    profile_image_url VARCHAR(512) COLLATE utf8mb4_unicode_ci DEFAULT NULL COMMENT '소셜 프로필 이미지 URL 또는 로컬 경로',
    payment_status VARCHAR(20) DEFAULT NULL, -- ERD 반영용
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS refresh_tokens (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    jti VARCHAR(64) COLLATE utf8mb4_unicode_ci NOT NULL UNIQUE,
    token_hash VARCHAR(256) COLLATE utf8mb4_unicode_ci NOT NULL,
    expires_at DATETIME NOT NULL,
    revoked_at DATETIME DEFAULT NULL,
    CONSTRAINT fk_refresh_tokens_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS job_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    main_category VARCHAR(50) DEFAULT NULL,
    sub_category VARCHAR(50) DEFAULT NULL,
    target_role VARCHAR(50) DEFAULT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS question_pool (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT DEFAULT NULL,
    question_type VARCHAR(30) DEFAULT NULL,
    skill_tag VARCHAR(100) DEFAULT NULL,
    difficulty VARCHAR(20) DEFAULT NULL,
    content TEXT NOT NULL,
    reference_answer TEXT,
    keywords VARCHAR(255) DEFAULT NULL,
    CONSTRAINT fk_question_category FOREIGN KEY (category_id) REFERENCES job_categories(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS user_resumes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL, 
    title VARCHAR(255) NOT NULL,
    job_role VARCHAR(100) DEFAULT NULL,
    resume_text MEDIUMTEXT,
    analysis_result JSON DEFAULT NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_user_resumes FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS interview_sessions (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      INT DEFAULT NULL, 
    job_role     VARCHAR(100) DEFAULT NULL,
    difficulty   VARCHAR(20) DEFAULT NULL,
    persona      VARCHAR(50) DEFAULT NULL,
    total_score  FLOAT DEFAULT NULL,
    status       VARCHAR(20) DEFAULT 'START', 
    started_at   TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    ended_at     TIMESTAMP NULL DEFAULT NULL,
    resume_used  TINYINT(1) DEFAULT '0',
    resume_id    INT DEFAULT NULL,
    manual_tech_stack TEXT DEFAULT NULL,
    CONSTRAINT fk_session_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_session_resume FOREIGN KEY (resume_id) REFERENCES user_resumes(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS interview_details (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    session_id      INT NOT NULL,
    turn_index      INT NOT NULL,
    question        TEXT, 
    answer          TEXT, 
    is_followup     TINYINT(1) DEFAULT '0',
    response_time   INT DEFAULT NULL,  
    score           FLOAT DEFAULT NULL,
    feedback        TEXT,
    sentiment_score FLOAT DEFAULT NULL, 
    created_at      TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_detail_session FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS guestbook_memos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    author VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    color VARCHAR(200) DEFAULT NULL,
    border VARCHAR(50) DEFAULT NULL,
    text_color VARCHAR(50) DEFAULT NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS board_questions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    content TEXT NOT NULL,
    display_order INT NOT NULL,
    is_active TINYINT(1) DEFAULT '1',
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS board_answers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    question_id INT NOT NULL,
    user_id INT NOT NULL,
    author_name VARCHAR(100) NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_board_answer_question FOREIGN KEY (question_id) REFERENCES board_questions(id) ON DELETE CASCADE,
    CONSTRAINT fk_board_answer_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS board_answer_likes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    answer_id INT NOT NULL,
    user_id INT NOT NULL,
    created_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uq_board_answer_like (answer_id, user_id),
    CONSTRAINT fk_board_like_answer FOREIGN KEY (answer_id) REFERENCES board_answers(id) ON DELETE CASCADE,
    CONSTRAINT fk_board_like_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
"""

BOARD_QUESTIONS = [
    "본인의 성격을 한 단어로 표현한다면 무엇인가요?",
    "팀 프로젝트에서 갈등이 생겼을 때 어떻게 해결했나요?",
    "실패했던 경험과 그 경험을 통해 배운 점을 말씀해주세요.",
    "본인이 생각하는 가장 큰 장점은 무엇인가요?",
    "본인이 생각하는 가장 보완해야 할 점은 무엇인가요?",
    "협업할 때 중요하게 생각하는 태도는 무엇인가요?",
    "스트레스를 받는 상황에서 어떻게 대처하나요?",
    "의견이 다른 팀원과 일해야 할 때 어떻게 행동하나요?",
    "리더 역할과 팔로워 역할 중 어느 쪽이 더 익숙한가요?",
    "예상치 못한 문제가 발생했을 때 어떻게 대응하나요?",
    "업무 우선순위가 충돌할 때 어떻게 정리하나요?",
    "최근 스스로를 성장시켰다고 느낀 경험은 무엇인가요?",
    "피드백을 받았을 때 어떻게 받아들이고 반영하나요?",
    "책임감 있게 행동했던 경험을 말씀해주세요.",
    "팀에 기여했다고 느낀 순간은 언제였나요?",
    "반대로 팀에 미안했던 경험이 있다면 무엇인가요?",
    "지원 직무와 무관해 보여도 본인에게 중요했던 경험은 무엇인가요?",
    "어려운 사람과 함께 일해야 한다면 어떻게 관계를 풀어가겠나요?",
    "회사 생활에서 가장 중요하다고 생각하는 가치는 무엇인가요?",
    "왜 우리가 당신과 함께 일해야 한다고 생각하나요?",
]


# 커넥션 컨텍스트 매니저
@contextmanager
def get_connection():
    env_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"
    )
    load_dotenv(dotenv_path=env_path, override=True)

    db_config = {
        "host": os.getenv("DB_HOST", "localhost"),
        "port": int(os.getenv("DB_PORT", "3306")),
        "user": os.getenv("DB_USER", "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "db": os.getenv("DB_NAME", "ai_interview"),
        "charset": "utf8mb4",
        "cursorclass": DictCursor,
    }
    conn = pymysql.connect(**db_config)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# DB 초기화
def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            for stmt in DDL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)
            # 기존 테이블 컬럼 크기 마이그레이션
            migrate_stmts = [
                "ALTER TABLE guestbook_memos MODIFY color VARCHAR(200)",
                "ALTER TABLE guestbook_memos MODIFY border VARCHAR(50)",
                "ALTER TABLE guestbook_memos MODIFY text_color VARCHAR(50)",
            ]
            for stmt in migrate_stmts:
                try:
                    cur.execute(stmt)
                except Exception:
                    pass
    seed_board_questions()


def seed_board_questions():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM board_questions")
            row = cur.fetchone() or {}
            if int(row.get("cnt", 0)) > 0:
                return
            cur.executemany(
                """INSERT INTO board_questions (content, display_order, is_active)
                   VALUES (%s, %s, 1)""",
                [
                    (content, idx)
                    for idx, content in enumerate(BOARD_QUESTIONS, start=1)
                ],
            )


# 세션 CRUD
def create_session(
    user_id: int,
    job_role: str,
    difficulty: str = "미들",
    persona: str = "깐깐한 기술팀장",
    resume_used: bool = False,
    resume_id: int | None = None,
    manual_tech_stack: str | None = None,
) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO interview_sessions
                   (user_id, job_role, difficulty, persona, resume_used, resume_id, manual_tech_stack)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (
                    user_id,
                    job_role,
                    difficulty,
                    persona,
                    int(resume_used),
                    resume_id,
                    manual_tech_stack,
                ),
            )
            return conn.insert_id()


def end_session(session_id: int, total_score: float):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE interview_sessions SET total_score=%s, ended_at=NOW(), status='COMPLETED' WHERE id=%s",
                (total_score, session_id),
            )


def save_detail(
    session_id: int,
    turn_index: int,
    question: str,
    answer: str,
    is_followup: bool,
    score: float | None = None,
    feedback: str | None = None,
    response_time: int | None = None,
    sentiment_score: float | None = None,
):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO interview_details
                   (session_id, turn_index, question, answer, is_followup, score, feedback, response_time, sentiment_score)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (
                    session_id,
                    turn_index,
                    question,
                    answer,
                    int(is_followup),
                    score,
                    feedback,
                    response_time,
                    sentiment_score,
                ),
            )


def get_sessions_by_user(user_id: int) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, job_role, difficulty, persona, total_score, status,
                          started_at, ended_at, resume_used
                   FROM interview_sessions
                   WHERE user_id=%s
                   ORDER BY started_at DESC""",
                (user_id,),
            )
            return cur.fetchall()


def get_details_by_session(session_id: int) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT turn_index, question, answer, is_followup, response_time,
                          score, feedback, sentiment_score, created_at
                   FROM interview_details
                   WHERE session_id=%s
                   ORDER BY turn_index ASC""",
                (session_id,),
            )
            return cur.fetchall()


# question_pool 헬퍼
def get_questions_by_role(
    job_role: str, difficulty: str, q_type: str = "기술", limit: int = 3
) -> list[dict]:
    diff_map = {"주니어": "Easy", "미들": "Medium", "시니어": "Hard"}
    db_difficulty = diff_map.get(difficulty, difficulty)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT qp.id, qp.content AS question, qp.question_type, qp.difficulty
                   FROM question_pool qp
                   LEFT JOIN job_categories jc ON qp.category_id = jc.id
                   WHERE jc.target_role = %s AND qp.difficulty = %s AND qp.question_type = %s
                   ORDER BY RAND() LIMIT %s""",
                (job_role, db_difficulty, q_type, limit),
            )
            return cur.fetchall()


def get_common_questions(limit: int = 1) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, content AS question FROM question_pool
                   WHERE question_type='인성' OR question_type='공통'
                   ORDER BY RAND() LIMIT %s""",
                (limit,),
            )
            return cur.fetchall()


def get_questions_by_resume_keywords(
    job_role: str, difficulty: str, keywords: list[str], limit: int = 3
) -> list[dict]:
    if not keywords:
        return get_questions_by_role(job_role, difficulty, "기술", limit)

    diff_map = {"주니어": "Easy", "미들": "Medium", "시니어": "Hard"}
    db_difficulty = diff_map.get(difficulty, difficulty)

    with get_connection() as conn:
        with conn.cursor() as cur:
            likes_clauses = []
            params = [job_role, db_difficulty]
            for k in keywords:
                likes_clauses.append("(qp.content LIKE %s OR qp.keywords LIKE %s)")
                params.extend([f"%{k}%", f"%{k}%"])

            likes_sql = " OR ".join(likes_clauses)
            query = f"""
                SELECT qp.id, qp.content AS question, qp.question_type, qp.difficulty
                FROM question_pool qp
                LEFT JOIN job_categories jc ON qp.category_id = jc.id
                WHERE jc.target_role = %s AND qp.difficulty = %s AND ({likes_sql})
                ORDER BY RAND() LIMIT %s
            """
            params.append(limit)
            cur.execute(query, tuple(params))
            results = cur.fetchall()

            if len(results) < limit:
                needed = limit - len(results)
                fallback = get_questions_by_role(
                    job_role, difficulty, "기술", limit * 2
                )
                existing_ids = {r["id"] for r in results}
                for f in fallback:
                    if f["id"] not in existing_ids:
                        results.append(f)
                        existing_ids.add(f["id"])
                        if len(results) == limit:
                            break
            return results


# 이력서 보관함 CRUD
def save_user_resume(
    user_id: int, title: str, job_role: str, resume_text: str, analysis_result: dict
) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            json_str = json.dumps(analysis_result, ensure_ascii=False)
            cur.execute(
                """INSERT INTO user_resumes (user_id, title, job_role, resume_text, analysis_result)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, title, job_role, resume_text, json_str),
            )
            return conn.insert_id()


def get_user_resumes(user_id: int) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, title, job_role, resume_text, analysis_result, created_at 
                   FROM user_resumes 
                   WHERE user_id=%s ORDER BY created_at DESC""",
                (user_id,),
            )
            rows = cur.fetchall()
            for r in rows:
                if r["analysis_result"] and isinstance(r["analysis_result"], str):
                    r["analysis_result"] = json.loads(r["analysis_result"])
            return rows


def delete_user_resume(resume_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_resumes WHERE id=%s", (resume_id,))


# ─── 방명록(게시판) CRUD ────────────────────────────────────
def save_memo(author: str, content: str, color: str, border: str, text_color: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO guestbook_memos (author, content, color, border, text_color)
                   VALUES (%s, %s, %s, %s, %s)""",
                (author, content, color, border, text_color),
            )


def get_all_memos(limit: int = 30) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT author, content, color, border, text_color, created_at
                   FROM guestbook_memos
                   ORDER BY created_at DESC
                   LIMIT %s""",
                (limit,),
            )
            return cur.fetchall()


def get_board_questions() -> list[dict]:
    seed_board_questions()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT q.id, q.content, q.display_order, q.created_at,
                          COUNT(a.id) AS answer_count,
                          MAX(a.created_at) AS latest_answer_at
                   FROM board_questions q
                   LEFT JOIN board_answers a ON a.question_id = q.id
                   WHERE q.is_active = 1
                   GROUP BY q.id, q.content, q.display_order, q.created_at
                   ORDER BY q.display_order ASC"""
            )
            return cur.fetchall()


def get_board_question(question_id: int) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, content, display_order, created_at
                   FROM board_questions
                   WHERE id=%s AND is_active=1""",
                (question_id,),
            )
            return cur.fetchone()


def get_board_answers(
    question_id: int,
    limit: int = 10,
    offset: int = 0,
    viewer_id: int | None = None,
) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT a.id, a.question_id, a.user_id, a.author_name, a.content, a.created_at, a.updated_at,
                          COUNT(l.id) AS like_count,
                          MAX(CASE WHEN l.user_id = %s THEN 1 ELSE 0 END) AS liked_by_me
                   FROM board_answers a
                   LEFT JOIN board_answer_likes l ON l.answer_id = a.id
                   WHERE a.question_id=%s
                   GROUP BY a.id, a.question_id, a.user_id, a.author_name, a.content, a.created_at, a.updated_at
                   ORDER BY like_count DESC, a.created_at DESC
                   LIMIT %s OFFSET %s""",
                (viewer_id or 0, question_id, limit, offset),
            )
            return cur.fetchall()


def count_board_answers(question_id: int) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) AS cnt FROM board_answers WHERE question_id=%s",
                (question_id,),
            )
            row = cur.fetchone() or {}
            return int(row.get("cnt", 0))


def create_board_answer(
    question_id: int, user_id: int, author_name: str, content: str
) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO board_answers (question_id, user_id, author_name, content)
                   VALUES (%s, %s, %s, %s)""",
                (question_id, user_id, author_name, content),
            )
            return conn.insert_id()


def toggle_board_answer_like(answer_id: int, user_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM board_answer_likes WHERE answer_id=%s AND user_id=%s",
                (answer_id, user_id),
            )
            row = cur.fetchone()
            if row:
                cur.execute(
                    "DELETE FROM board_answer_likes WHERE answer_id=%s AND user_id=%s",
                    (answer_id, user_id),
                )
                return False

            cur.execute(
                "INSERT INTO board_answer_likes (answer_id, user_id) VALUES (%s, %s)",
                (answer_id, user_id),
            )
            return True


def get_board_answer(answer_id: int) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT a.id, a.question_id, a.user_id, a.author_name, a.content,
                          COUNT(l.id) AS like_count
                   FROM board_answers a
                   LEFT JOIN board_answer_likes l ON l.answer_id = a.id
                   WHERE a.id=%s
                   GROUP BY a.id, a.question_id, a.user_id, a.author_name, a.content""",
                (answer_id,),
            )
            return cur.fetchone()


# -------------------- 다빈 추가 ---------------------
def get_my_board_answer_by_question(question_id: int, user_id: int) -> dict | None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, content FROM board_answers WHERE question_id=%s AND user_id=%s",
                (question_id, user_id),
            )
            return cur.fetchone()


def upsert_board_answer(
    question_id: int, user_id: int, author_name: str, content: str
) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            existing = get_my_board_answer_by_question(question_id, user_id)
            if existing:
                cur.execute(
                    "UPDATE board_answers SET content=%s, updated_at=NOW() WHERE id=%s",
                    (content, existing["id"]),
                )
                return existing["id"]
            else:
                cur.execute(
                    "INSERT INTO board_answers (question_id, user_id, author_name, content) VALUES (%s, %s, %s, %s)",
                    (question_id, user_id, author_name, content),
                )
                return conn.insert_id()


# ----------------------------------------------------
