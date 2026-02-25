"""
File: db/database.py
Description: MySQL 연결 관리 + 테이블 초기화 + CRUD 헬퍼
             (시드 데이터 제거 및 CSV 마이그레이션 구조에 완벽 호환, 이력서 보관함 추가)
"""

import os
import json  # 🔥 AI 분석 결과(JSON) 저장을 위해 추가
import pymysql
from pymysql.cursors import DictCursor
from contextlib import contextmanager
from dotenv import load_dotenv

# 현재 파일(database.py) 위치를 기반으로 backend 폴더 안의 .env 경로 절대 지정
current_file_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.dirname(current_file_dir)
env_path = os.path.join(backend_dir, ".env")

load_dotenv(dotenv_path=env_path, override=True)

# ─── DB 연결 설정 (.env에서 읽기) ─────────────────────────────
DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "3306")),
    "user":     os.getenv("DB_USER",     "root"),
    "password": os.getenv("DB_PASSWORD", ""),
    "db":       os.getenv("DB_NAME",     "aiwork"),
    "charset":  "utf8mb4",
    "cursorclass": DictCursor,
}

# ─── DDL: 테이블 정의 (CSV 구조와 완벽 동기화 + 이력서 보관함) ────────────────
DDL = """
CREATE TABLE IF NOT EXISTS job_categories (
    id INT AUTO_INCREMENT PRIMARY KEY,
    main_category VARCHAR(50),
    sub_category VARCHAR(50),
    target_role VARCHAR(50) UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

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

CREATE TABLE IF NOT EXISTS interview_sessions (
    id           INT AUTO_INCREMENT PRIMARY KEY,
    user_id      VARCHAR(100),
    job_role     VARCHAR(100),
    difficulty   VARCHAR(20),
    persona      VARCHAR(50),
    total_score  FLOAT DEFAULT NULL,
    started_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at     TIMESTAMP NULL,
    resume_used  TINYINT(1) DEFAULT 0
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS interview_details (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    session_id      INT NOT NULL,
    turn_index      INT NOT NULL,
    question        TEXT,
    answer          TEXT,
    is_followup     TINYINT(1) DEFAULT 0,
    score           FLOAT DEFAULT NULL,
    feedback        TEXT,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 🔥 새롭게 추가된 이력서 및 AI 분석 결과 저장 테이블
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

# ─── 커넥션 컨텍스트 매니저 ───────────────────────────────────
@contextmanager
def get_connection():
    # 런타임에 최신 환경변수를 즉시 로딩하도록 함수 내부에서 설정
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    load_dotenv(dotenv_path=env_path, override=True)

    db_config = {
        "host":     os.getenv("DB_HOST",     "localhost"),
        "port":     int(os.getenv("DB_PORT", "3306")),
        "user":     os.getenv("DB_USER",     "root"),
        "password": os.getenv("DB_PASSWORD", ""),
        "db":       os.getenv("DB_NAME",     "aiwork"),
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


# ─── DB 초기화 (앱 시작 시 1회 호출) ─────────────────────────
def init_db():
    """테이블 껍데기만 생성합니다. 데이터는 python_question.py 로 넣습니다."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            for stmt in DDL.strip().split(";"):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)


# ─── 세션 CRUD ────────────────────────────────────
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
                "UPDATE interview_sessions SET total_score=%s, ended_at=NOW() WHERE id=%s",
                (total_score, session_id),
            )

def save_detail(session_id: int, turn_index: int, question: str,
                answer: str, is_followup: bool,
                score: float | None = None, feedback: str | None = None):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO interview_details
                   (session_id, turn_index, question, answer, is_followup, score, feedback)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                (session_id, turn_index, question, answer, int(is_followup), score, feedback),
            )

def get_sessions_by_user(user_id: str) -> list[dict]:
    """마이페이지용: 유저의 면접 세션 목록 조회 (최신순)"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, job_role, difficulty, persona, total_score,
                          started_at, ended_at, resume_used
                   FROM interview_sessions
                   WHERE user_id=%s
                   ORDER BY started_at DESC""",
                (user_id,),
            )
            return cur.fetchall()

def get_details_by_session(session_id: int) -> list[dict]:
    """특정 세션의 전체 질문-답변 내역 조회"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT turn_index, question, answer, is_followup,
                          score, feedback, created_at
                   FROM interview_details
                   WHERE session_id=%s
                   ORDER BY turn_index ASC""",
                (session_id,),
            )
            return cur.fetchall()


# ─── question_pool 헬퍼 ───────────
def get_questions_by_role(job_role: str, difficulty: str,
                          q_type: str = "기술", limit: int = 3) -> list[dict]:
    """직무 + 난이도에 맞는 기술 질문 가져오기"""
    # 프론트엔드의 한글 난이도를 DB의 영문 난이도로 매핑
    diff_map = {
        "주니어": "Easy",
        "미들": "Medium",
        "시니어": "Hard"
    }
    db_difficulty = diff_map.get(difficulty, difficulty)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 프론트엔드 호환성을 위해 content를 question으로 별칭(AS) 지정
            cur.execute(
                """SELECT qp.id, qp.content AS question, qp.question_type, qp.difficulty
                   FROM question_pool qp
                   LEFT JOIN job_categories jc ON qp.category_id = jc.id
                   WHERE jc.target_role = %s
                     AND qp.difficulty = %s
                     AND qp.question_type = %s
                   ORDER BY RAND()
                   LIMIT %s""",
                (job_role, db_difficulty, q_type, limit),
            )
            return cur.fetchall()


def get_common_questions(limit: int = 1) -> list[dict]:
    """공통 질문(자기소개 등) 추출"""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, content AS question FROM question_pool
                   WHERE question_type='인성' OR question_type='공통'
                   ORDER BY RAND()
                   LIMIT %s""",
                (limit,),
            )
            return cur.fetchall()


def get_questions_by_resume_keywords(job_role: str, difficulty: str, keywords: list[str], limit: int = 3) -> list[dict]:
    """이력서에서 뽑은 키워드를 바탕으로 question_pool에서 맞춤형 메인 질문을 검색합니다."""
    # 키워드가 없으면 기존 랜덤 직무 추출 방식으로 fallback
    if not keywords:
        return get_questions_by_role(job_role, difficulty, "기술", limit)

    diff_map = {
        "주니어": "Easy",
        "미들": "Medium",
        "시니어": "Hard"
    }
    db_difficulty = diff_map.get(difficulty, difficulty)

    with get_connection() as conn:
        with conn.cursor() as cur:
            # 1. 키워드 기반 LIKE 쿼리 생성 (질문 내용이나 키워드 컬럼에 단어가 포함된 경우)
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
                WHERE jc.target_role = %s
                  AND qp.difficulty = %s
                  AND ({likes_sql})
                ORDER BY RAND()
                LIMIT %s
            """
            params.append(limit)
            cur.execute(query, tuple(params))
            results = cur.fetchall()

            # 2. 만약 키워드에 딱 맞는 질문이 부족하다면, 일반 직무 질문으로 빈자리 채우기
            if len(results) < limit:
                needed = limit - len(results)
                fallback = get_questions_by_role(job_role, difficulty, "기술", limit * 2) 
                existing_ids = {r['id'] for r in results}
                
                for f in fallback:
                    if f['id'] not in existing_ids:
                        results.append(f)
                        existing_ids.add(f['id'])
                        if len(results) == limit:
                            break
                            
            return results

# =====================================================================
# 🔥 이력서(Resume) 보관함 CRUD 기능 추가
# =====================================================================
def save_user_resume(user_id: str, title: str, job_role: str, resume_text: str, analysis_result: dict) -> int:
    """새로운 이력서 텍스트와 AI 분석 결과(JSON)를 영구 저장합니다."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            # dict를 JSON 문자열로 변환하여 저장
            json_str = json.dumps(analysis_result, ensure_ascii=False)
            cur.execute(
                """INSERT INTO user_resumes (user_id, title, job_role, resume_text, analysis_result)
                   VALUES (%s, %s, %s, %s, %s)""",
                (user_id, title, job_role, resume_text, json_str)
            )
            return conn.insert_id()

def get_user_resumes(user_id: str) -> list[dict]:
    """유저의 저장된 이력서 목록을 최신순으로 가져옵니다."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, title, job_role, resume_text, analysis_result, created_at 
                   FROM user_resumes 
                   WHERE user_id=%s 
                   ORDER BY created_at DESC""",
                (user_id,)
            )
            rows = cur.fetchall()
            # MySQL에서 꺼낸 JSON 문자열을 파이썬 dict로 변환
            for r in rows:
                if r['analysis_result'] and isinstance(r['analysis_result'], str):
                    r['analysis_result'] = json.loads(r['analysis_result'])
            return rows

def delete_user_resume(resume_id: int):
    """이력서를 보관함에서 삭제합니다."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM user_resumes WHERE id=%s", (resume_id,))