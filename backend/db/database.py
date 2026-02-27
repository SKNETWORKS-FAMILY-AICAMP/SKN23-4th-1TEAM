"""
File: db/database.py
Description: MySQL 연결 관리 + 테이블 초기화 + CRUD 헬퍼
             (users 테이블 및 신규 통계/상태 컬럼 완벽 통합 적용)
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
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "3306")),
    "user":     os.getenv("DB_USER",     "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "db":       os.getenv("DB_NAME",     "ai_interview"),
    "charset":  "utf8mb4",
    "cursorclass": DictCursor,
}

# DDL
DDL = """
-- 1. users 테이블 (ALTER 내용까지 한 번에 깔끔하게 생성)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    provider VARCHAR(20) DEFAULT NULL,          
    provider_user_id VARCHAR(255) DEFAULT NULL,  
    role VARCHAR(20) DEFAULT 'user',             
    name VARCHAR(100) NULL,                      
    password VARCHAR(255) NULL,                  
    tier VARCHAR(20) DEFAULT 'normal',           
    status VARCHAR(20) DEFAULT 'active',         
    profile_image_url VARCHAR(512) NULL,         
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. job_categories 테이블
CREATE TABLE IF NOT EXISTS job_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    main_category VARCHAR(50),
    sub_category VARCHAR(50),
    target_role VARCHAR(50) UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. question_pool 테이블
CREATE TABLE IF NOT EXISTS question_pool (
    id INT AUTO_INCREMENT PRIMARY KEY,
    category_id INT,
    question_type VARCHAR(30),
    skill_tag VARCHAR(100),
    difficulty VARCHAR(20),
    content TEXT NOT NULL,
    reference_answer TEXT,
    keywords VARCHAR(255),
    FOREIGN KEY (category_id) REFERENCES job_categories(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. interview_sessions 테이블
CREATE TABLE IF NOT EXISTS interview_sessions (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      VARCHAR(100),
    job_role     VARCHAR(100),
    difficulty   VARCHAR(20),
    persona      VARCHAR(50),
    total_score  FLOAT DEFAULT 0.0,
    status       VARCHAR(20) DEFAULT 'START', 
    started_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at     TIMESTAMP NULL,
    resume_used  TINYINT(1) DEFAULT 0
    -- FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. interview_details 테이블
CREATE TABLE IF NOT EXISTS interview_details (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    session_id      INT NOT NULL,
    turn_index      INT NOT NULL,
    question        TEXT, -- 기존 파이썬 변수명 호환 (question_text 대체)
    answer          TEXT, -- 기존 파이썬 변수명 호환 (answer_text 대체)
    is_followup     TINYINT(1) DEFAULT 0,
    response_time   INT DEFAULT NULL,  
    score           FLOAT DEFAULT NULL,
    feedback        TEXT,
    sentiment_score FLOAT DEFAULT NULL, 
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 6. user_resumes 테이블 (이력서 보관함)
CREATE TABLE IF NOT EXISTS user_resumes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id VARCHAR(100) NOT NULL,
    title VARCHAR(255) NOT NULL,
    job_role VARCHAR(100),
    resume_text MEDIUMTEXT,
    analysis_result JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
"""

# 커넥션 컨텍스트 매니저
@contextmanager
def get_connection():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(dotenv_path=env_path, override=True)

    db_config = {
        "host":     os.getenv("DB_HOST",     "localhost"),
        "port":     int(os.getenv("DB_PORT", "3306")),
        "user":     os.getenv("DB_USER",     "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "db":       os.getenv("DB_NAME",     "ai_interview"), # DB명 수정 적용됨
        "charset":  "utf8mb4",
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

# DB 초기화 (앱 시작 시 1회 호출) 
def init_db():
    with get_connection() as conn:
        with conn.cursor() as cur:
            for stmt in DDL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)

# 세션 CRUD
def create_session(user_id: str, job_role: str, difficulty: str = "미들",
                   persona: str = "깐깐한 기술팀장", resume_used: bool = False) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO interview_sessions
                   (user_id, job_role, difficulty, persona, resume_used)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, job_role, difficulty, persona, int(resume_used)),
            )
            return conn.insert_id()

def end_session(session_id: int, total_score: float):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE interview_sessions SET total_score=%s, ended_at=NOW(), status='COMPLETED' WHERE id=%s",
                (total_score, session_id),
            )

def save_detail(session_id: int, turn_index: int, question: str,
                answer: str, is_followup: bool,
                score: float | None = None, feedback: str | None = None,
                response_time: int | None = None, sentiment_score: float | None = None):
    # 🔥 파라미터에 response_time과 sentiment_score를 추가 지원하도록 업데이트했습니다.
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO interview_details
                   (session_id, turn_index, question, answer, is_followup, score, feedback, response_time, sentiment_score)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (session_id, turn_index, question, answer, int(is_followup), score, feedback, response_time, sentiment_score),
            )

def get_sessions_by_user(user_id: str) -> list[dict]:
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
def get_questions_by_role(job_role: str, difficulty: str,
                          q_type: str = "기술", limit: int = 3) -> list[dict]:
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

def get_questions_by_resume_keywords(job_role: str, difficulty: str, keywords: list[str], limit: int = 3) -> list[dict]:
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
                fallback = get_questions_by_role(job_role, difficulty, "기술", limit * 2) 
                existing_ids = {r['id'] for r in results}
                for f in fallback:
                    if f['id'] not in existing_ids:
                        results.append(f)
                        existing_ids.add(f['id'])
                        if len(results) == limit: break
            return results

# 이력서 보관함 CRUD 기능 추가
def save_user_resume(user_id: str, title: str, job_role: str, resume_text: str, analysis_result: dict) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            json_str = json.dumps(analysis_result, ensure_ascii=False)
            cur.execute(
                """INSERT INTO user_resumes (user_id, title, job_role, resume_text, analysis_result)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, title, job_role, resume_text, json_str)
            )
            return conn.insert_id()

def get_user_resumes(user_id: str) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, title, job_role, resume_text, analysis_result, created_at 
                   FROM user_resumes 
                   WHERE user_id=%s ORDER BY created_at DESC""",
                (user_id,)
            )
            rows = cur.fetchall()
            for r in rows:
                if r['analysis_result'] and isinstance(r['analysis_result'], str):
                    r['analysis_result'] = json.loads(r['analysis_result'])
            return rows

def delete_user_resume(resume_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_resumes WHERE id=%s", (resume_id,))


# 게시판 CRUD 기능
def save_memo(author: str, content: str, color: str, border: str, text_color: str):
    """새로운 메모를 DB에 저장합니다."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO guestbook_memos (author, content, color, border, text_color)
                   VALUES (%s, %s, %s, %s, %s)""",
                (author, content, color, border, text_color)
            )

def get_all_memos(limit: int = 30) -> list[dict]:
    """가장 최근에 작성된 메모들을 DB에서 불러옵니다 (기본 30개)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT author, content, color, border, text_color, created_at
                   FROM guestbook_memos
                   ORDER BY created_at DESC
                   LIMIT %s""",
                (limit,)
            )
            return cur.fetchall()

