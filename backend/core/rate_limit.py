"""
File: rate_limit.py
Author: 양창일
Created: 2026-02-16
Description: # 로그인 시도 기록 저장용 (메모리 기반)

Modification History:
- 2026-02-15: 초기 생성
"""
from datetime import datetime, timedelta

login_attempts = {}  # {ip: {"count": int, "blocked_until": datetime}}

MAX_ATTEMPTS = 5  # 최대 실패 횟수
BLOCK_MINUTES = 10  # 차단 시간

def check_block(ip: str):
    data = login_attempts.get(ip)

    if not data:
        return

    if data.get("blocked_until") and data["blocked_until"] > datetime.now():
        raise Exception("Too many login attempts. Try later.")

def record_failure(ip: str):
    now = datetime.now()
    data = login_attempts.get(ip)

    if not data:
        login_attempts[ip] = {"count": 1}
        return

    data["count"] += 1

    if data["count"] >= MAX_ATTEMPTS:
        data["blocked_until"] = now + timedelta(minutes=BLOCK_MINUTES)

def reset_attempts(ip: str):
    if ip in login_attempts:
        del login_attempts[ip]
