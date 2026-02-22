"""
File: api_utils.py
Author: 김지우
Created: 2026-02-22
Description: 프론트엔드 -> 백엔드(FastAPI) API 통신 전담 유틸리티 (인증 및 면접/RAG 통합)

Modification History: 
- 2026-02-22 (김지우): 초기 생성 및 연결 에러 디버깅 로직 추가
- 2026-02-22 (김지우): 면접 기능(RAG 인덱싱, 질문 생성, 결과 저장) 함수 통합
- 2026-02-22 (김지우): API 통신 타임아웃 기본 5초 -> 30초로 연장 (Timeout 에러 해결)
"""
import requests
import streamlit as st
from datetime import datetime
from utils.config import API_BASE_URL

def _handle_request(method, endpoint, **kwargs):
    """
    API 요청 중복 코드를 줄여주는 내부 헬퍼 함수
    """
    base_url = API_BASE_URL.rstrip('/')
    target_endpoint = endpoint.lstrip('/')
    url = f"{base_url}/{target_endpoint}"
    
    # 세션에 토큰이 있다면 자동으로 Authorization 헤더에 추가 (로그인 인증 호환)
    if "token" in st.session_state and st.session_state.token:
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {st.session_state.token}"
        kwargs["headers"] = headers
        
    try:
        # 🔥 timeout 기본값을 5초에서 30초로 대폭 늘렸습니다!
        timeout = kwargs.pop('timeout', 30)
        response = requests.request(method, url, timeout=timeout, **kwargs)
        
        if response.status_code == 200:
            return True, response.json()
        
        error_detail = response.json().get("detail", "서버 요청에 실패했습니다.")
        return False, error_detail
        
    except requests.exceptions.ConnectionError:
        print(f"DEBUG: Connection Failed to {url}")
        return False, f"백엔드 서버({url})와 연결할 수 없습니다."
    except Exception as e:
        return False, f"알 수 없는 오류 발생: {str(e)}"

# ==========================================
# 1. 인증 및 계정 관련 (Auth)
# ==========================================
def api_login(email, password):
    return _handle_request("POST", "/auth/login", json={"email": email, "password": password})

def api_verify_token(token):
    return _handle_request("GET", "/auth/verify", headers={"Authorization": f"Bearer {token}"})

def api_check_email(email):
    success, result = _handle_request("GET", "/auth/check-email", params={"email": email})
    if success:
        exists = result.get("exists") if isinstance(result, dict) else True
        return True, exists
    return False, result

def api_send_signup_email(email, auth_code):
    return _handle_request("POST", "/auth/send-signup-email", json={"email": email, "auth_code": auth_code})

def api_signup(email, password):
    return _handle_request("POST", "/auth/signup", json={"username": email, "password": password})

def api_send_reset_email(email, auth_code):
    return _handle_request("POST", "/auth/send-reset-email", json={"email": email, "auth_code": auth_code})

def api_reset_password(email, new_password):
    return _handle_request("POST", "/auth/reset-password", json={"email": email, "new_password": new_password})


# ==========================================
# 2. 면접 및 RAG 관련 (Inference)
# ==========================================
def api_ingest_resume(file):
    """이력서 PDF를 백엔드에 업로드하여 벡터 DB에 인덱싱
    ※ OpenAI 임베딩 처리 시간을 고려해 timeout=120s 적용
    """
    url   = f"{API_BASE_URL.rstrip('/')}/infer/ingest"
    files = {"file": (file.name, file.getvalue(), "application/pdf")}
    try:
        response = requests.post(url, files=files, timeout=120)
        if response.status_code == 200:
            return True, "학습 성공"
        # 빈 응답 방어: response.json()이 빈 바디에서 JSONDecodeError를 냄
        try:
            detail = response.json().get("detail", "학습 실패")
        except Exception:
            detail = response.text or f"HTTP {response.status_code} 오류"
        return False, detail
    except requests.exceptions.Timeout:
        return False, "이력서 학습 시간이 초과되었습니다. (120초) 파일 크기를 줄이거나 다시 시도해주세요."
    except requests.exceptions.ConnectionError:
        return False, "백엔드 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요."
    except Exception as e:
        return False, f"알 수 없는 오류: {str(e)}"

def api_start_interview(job_role):
    """새 면접 세션을 시작하여 백엔드 DB에서 정수형 session_id를 발급받아 반환"""
    return _handle_request("POST", "/infer/start", json={"job_role": job_role})

def api_get_next_question_v2(payload):
    """사용자 답변, 소요 시간, 직무, 난이도 등 전체 데이터를 RAG 기반 다음 질문 API에 전달"""
    return _handle_request("POST", "/infer/ask", json=payload)

def api_save_interview_result(session_id, messages, settings):
    """면접 종료 후 전체 대화 내역과 결과를 일반 DB에 저장"""
    payload = {
        "session_id": session_id,
        "messages": messages,
        "settings": settings,
        "end_time": datetime.now().isoformat()
    }
    return _handle_request("POST", "/infer/save", json=payload)


def api_stt_whisper(audio_file):
    """
    사용자의 음성 파일을 백엔드로 전달하여 텍스트(STT)로 변환합니다.
    """
    try:
        url = f"{API_BASE_URL.rstrip('/')}/infer/stt"
        files = {"file": (audio_file.name, audio_file.getvalue(), "audio/wav")}
        # 🔥 파일 전송 및 처리 시간을 고려해 명시적으로 30초 타임아웃 추가
        response = requests.post(url, files=files, timeout=30)
        
        if response.status_code == 200:
            return response.json().get("text", "음성을 인식하지 못했습니다.")
        else:
            return f"STT 오류: {response.status_code}"
    except Exception as e:
        return f"서버 연결 실패: {str(e)}"

def api_tts_service(text):
    """
    OpenAI TTS 기반 음성 데이터(바이너리)를 백엔드에서 받아옵니다.
    """
    try:
        url = f"{API_BASE_URL.rstrip('/')}/infer/tts"
        # 🔥 기존 15초에서 30초로 넉넉하게 연장
        response = requests.post(url, json={"text": text}, timeout=30)
        
        if response.status_code == 200:
            return response.content
        else:
            print(f"TTS Error [HTTP {response.status_code}]")
            return None
    except Exception as e:
        print(f"TTS 요청 실패: {e}")
        return None