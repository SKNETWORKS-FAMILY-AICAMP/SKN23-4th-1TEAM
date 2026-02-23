"""
File: db_utils.py
Author: 김다빈, 김지우
Created: 2026-02-21
Description: 데이터베이스 연결 및 쿼리 실행 원격 제어 유틸리티

Modification History:
- 2026-02-21 (김다빈): 초기 생성 (SSH 터널링 기반 원격 SQLite 연동 스크립트 구축)
- 2026-02-23 (김지우): SSH 및 SQLite 방식 전면 폐기, AWS MySQL(pymysql) 다이렉트 연결 방식으로 아키텍처 개선 및 SQL Injection 방어 적용
"""
import os
import pymysql
from dotenv import load_dotenv

# .env 파일에서 환경 변수 불러오기 (sign_up.py와 동일한 방식)
_ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
load_dotenv(_ENV_PATH, override=True)

# 지우님의 AWS MySQL 접속 정보
DB_HOST     = os.getenv("DB_HOST", "localhost")
DB_PORT     = int(os.getenv("DB_PORT", 3306))
DB_USER     = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "")
DB_NAME     = os.getenv("DB_NAME", "ai_interview")

def get_db_connection():
    """AWS MySQL 데이터베이스 직접 연결 객체 생성"""
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def fetch_remote_db(ip, query_type="users"):
    """(구) SSH 방식을 버리고 다이렉트로 원격 MySQL DB 정보 조회"""
    # ip 인자는 이전 SSH 방식의 잔재로 남겨둠 (admin.py 코드 수정 최소화를 위해)
    
    if query_type == "users":
        sql = "SELECT * FROM users"
    elif query_type == "interviews":
        sql = "SELECT id, user_id, score, created_at FROM interviews ORDER BY id DESC LIMIT 10"
    else:
        return None

    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
        return result
    except Exception as e:
        # admin.py가 에러를 화면에 띄울 수 있도록 기존 딕셔너리 포맷 유지
        return [{"error": "DB Fetch Failed", "raw": str(e), "err": str(e)}]
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()

def run_remote_sql(ip, sql, args=None):
    """(구) SSH 방식을 버리고 다이렉트로 원격 MySQL 쿼리 실행 
    SQL 인젝션 방지를 위해 args 파라미터 전달 기능 지원 (pymysql 자체 기능 활용)
    """
    try:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            if args:
                # args가 넘어오면 pymysql이 알아서 안전하게 ?(포맷) 자리에 맵핑해줌
                cursor.execute(sql, args)
            else:
                cursor.execute(sql)
        conn.commit()
        return "SUCCESS"
    except Exception as e:
        return f"ERROR: {str(e)}"
    finally:
        if 'conn' in locals() and conn.open:
            conn.close()