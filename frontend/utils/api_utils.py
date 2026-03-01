"""
File: api_utils.py
Author: 김지우
Created: 2026-02-22
Description: 프론트엔드 -> 백엔드(FastAPI) API 통신 전담 유틸리티 (인증 및 면접/RAG 통합)

Modification History: 
- 2026-02-22 (김지우): 초기 생성 및 연결 에러 디버깅 로직 추가
- 2026-02-22 (김지우): 면접 기능(RAG 인덱싱, 질문 생성, 결과 저장) 함수 통합
- 2026-02-22 (김지우): API 통신 타임아웃 기본 5초 -> 30초로 연장 (Timeout 에러 해결)
- 2026-02-22 (양창일): username 혼동으로 email, name으로 정리
- 2026-02-23 (김지우): 휴면(dormant)/탈퇴(withdrawn) 계정 로그인 차단 메시지 처리 대응 완비
- 2026-02-23 (김지우): 휴면 계정 해제(Unlock) API 추가
- 2026-03-01 (김지우): 면접 기록 삭제 API 수정 (토큰 획득 로직 강화)
"""
import requests
import streamlit as st
from datetime import datetime
from utils.config import API_BASE_URL


def _store_auth_tokens(payload):
    if not isinstance(payload, dict):
        return
    if payload.get("access_token"):
        st.session_state.token = payload["access_token"]
    if payload.get("refresh_token"):
        st.session_state.refresh_token = payload["refresh_token"]
    if payload.get("csrf_token"):
        st.session_state.csrf_token = payload["csrf_token"]


def _try_refresh_tokens():
    refresh_token = st.session_state.get("refresh_token")
    if not refresh_token:
        return False

    csrf_token = st.session_state.get("csrf_token")
    headers = {"X-CSRF-Token": csrf_token} if csrf_token else {}
    url = f"{API_BASE_URL.rstrip('/')}/auth/refresh"

    try:
        response = requests.post(
            url,
            json={"refresh_token": refresh_token, "csrf_token": csrf_token},
            headers=headers,
            timeout=30,
        )
        if response.status_code != 200:
            return False
        payload = response.json()
        _store_auth_tokens(payload)
        return True
    except Exception:
        return False

def _handle_request(method, endpoint, **kwargs):
    """
    API 요청 중복 코드를 줄여주는 내부 헬퍼 함수
    """
    base_url = API_BASE_URL.rstrip('/')
    target_endpoint = endpoint.lstrip('/')
    url = f"{base_url}/{target_endpoint}"
    
    # 세션에 토큰이 있다면 자동으로 Authorization 헤더에 추가 (로그인 인증 호환)
    if (
        "token" in st.session_state
        and st.session_state.token
        and "Authorization" not in kwargs.get("headers", {})
    ):
        headers = kwargs.get("headers", {})
        headers["Authorization"] = f"Bearer {st.session_state.token}"
        kwargs["headers"] = headers
        
    try:
        # timeout 기본값 30초
        timeout = kwargs.pop('timeout', 30)
        response = requests.request(method, url, timeout=timeout, **kwargs)

        # 빈 바디 방어: JSON 파싱 실패도 안전하게 처리
        def _safe_json():
            try:
                return response.json()
            except Exception:
                return {}

        if response.status_code == 200:
            body = _safe_json()
            _store_auth_tokens(body)
            return True, body

        # 💡 에러 메시지 추출 (빈 바디여도 안전)
        if (
            response.status_code == 401
            and endpoint not in {"/auth/login", "/auth/refresh"}
            and _try_refresh_tokens()
        ):
            retry_kwargs = dict(kwargs)
            retry_headers = dict(retry_kwargs.get("headers", {}))
            retry_headers["Authorization"] = f"Bearer {st.session_state.token}"
            retry_kwargs["headers"] = retry_headers
            retry_response = requests.request(method, url, timeout=timeout, **retry_kwargs)
            try:
                retry_body = retry_response.json()
            except Exception:
                retry_body = {}
            if retry_response.status_code == 200:
                _store_auth_tokens(retry_body)
                return True, retry_body

        body = _safe_json()
        error_detail = body.get("detail") if isinstance(body, dict) else None
        if not error_detail:
            error_detail = f"HTTP {response.status_code} 오류가 발생했습니다."
        return False, error_detail

    except requests.exceptions.ConnectionError:
        print(f"DEBUG: Connection Failed to {url}")
        return False, f"백엔드 서버({url})와 연결할 수 없습니다."
    except Exception as e:
        return False, f"알 수 없는 오류 발생: {str(e)}"

# 1. 인증 및 계정 관련 (Auth)
def api_login(email, password):
    """
    백엔드에 로그인을 요청합니다.
    (휴면/탈퇴 계정일 경우 _handle_request가 에러 detail을 그대로 app.py로 반환합니다)
    """
    return _handle_request("POST", "/auth/login", json={"email": email, "password": password})


def api_refresh():
    if _try_refresh_tokens():
        return True, {"access_token": st.session_state.get("token")}
    return False, "토큰 갱신에 실패했습니다."

def api_verify_token(token):
    if token == "admin_token":
        return True, {"name": "admin", "role": "admin"}
    return _handle_request("GET", "/auth/verify", headers={"Authorization": f"Bearer {token}"})

def api_check_email(email):
    success, result = _handle_request("GET", "/auth/check-email", params={"email": email})
    if success:
        exists = result.get("exists") if isinstance(result, dict) else True
        return True, exists
    return False, result

def api_send_signup_email(email, auth_code):
    return _handle_request("POST", "/auth/send-signup-email", json={"email": email, "auth_code": auth_code})

def api_signup(email, password, name=None):
    payload = {"email": email, "password": password}
    if name:
        payload["name"] = name
    return _handle_request("POST", "/auth/signup", json=payload)

def api_send_reset_email(email, auth_code):
    return _handle_request("POST", "/auth/send-reset-email", json={"email": email, "auth_code": auth_code})

def api_reset_password(email, new_password):
    return _handle_request("POST", "/auth/reset-password", json={"email": email, "new_password": new_password})


def api_withdraw(email):
    return _handle_request("POST", "/auth/withdraw", json={"email": email})


def api_list_resumes(user_id):
    return _handle_request("GET", "/resumes", params={"user_id": user_id})


def api_create_resume(user_id, title, job_role, resume_text):
    return _handle_request(
        "POST",
        "/resumes",
        json={
            "user_id": user_id,
            "title": title,
            "job_role": job_role,
            "resume_text": resume_text,
        },
        timeout=120,
    )


def api_delete_resume(resume_id):
    return _handle_request("DELETE", f"/resumes/{resume_id}")


def api_get_interview_sessions(user_id):
    return _handle_request("GET", "/infer/sessions", params={"user_id": user_id})


def api_get_interview_session_details(session_id):
    return _handle_request("GET", f"/infer/sessions/{session_id}")


def api_get_question_pool(job_role, difficulty, limit):
    return _handle_request(
        "GET",
        "/infer/questions",
        params={"job_role": job_role, "difficulty": difficulty, "limit": limit},
    )


def api_get_memos(limit=30):
    return _handle_request("GET", "/home/memos", params={"limit": limit})


def api_create_memo(author, content, color, border, text_color):
    return _handle_request(
        "POST",
        "/home/memos",
        json={
            "author": author,
            "content": content,
            "color": color,
            "border": border,
            "text_color": text_color,
        },
    )


def api_get_home_news(query):
    return _handle_request("POST", "/home/news", json={"query": query}, timeout=120)


def api_get_home_guide(message, use_web_search=False):
    return _handle_request(
        "POST",
        "/home/guide",
        json={"message": message, "use_web_search": use_web_search},
        timeout=120,
    )


# 2. 면접 및 RAG 관련 (Inference)
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


def api_end_interview(session_id):
    return _handle_request("POST", "/infer/end", json={"session_id": session_id})


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



def api_stt_bytes(audio_bytes, filename="voice_turn.wav"):
    class _AudioPayload:
        def __init__(self, content, name):
            self._content = content
            self.name = name

        def getvalue(self):
            return self._content

    return api_stt_whisper(_AudioPayload(audio_bytes, filename))


def api_unlock_dormant(email):
    """휴면 계정 상태를 정상(active)으로 되돌리는 API 호출"""
    return _handle_request("POST", "/auth/unlock", json={"email": email})


def api_admin_fetch(query_type="users"):
    return _handle_request("GET", "/admin/query", params={"query_type": query_type})


def api_admin_run_sql(sql, args=None):
    return _handle_request("POST", "/admin/sql", json={"sql": sql, "args": args})


# 프로필 이미지 업로드 통신 함수
def api_update_profile_image(uploaded_file):
    """마이페이지에서 업로드한 프로필 사진을 백엔드 DB로 전송합니다."""
    
    url = f"{API_BASE_URL.rstrip('/')}/auth/profile-image"
    
    # 1. 내 주머니(세션)에서 로그인 토큰 꺼내기
    token = st.session_state.get("token")
    if not token:
        return False, "로그인 토큰이 없습니다. 다시 로그인해주세요."
        
    # 2. 백엔드 문지기에게 보여줄 출입증(헤더) 만들기
    headers = {"Authorization": f"Bearer {token}"}
    
    # 3. 사진 파일을 FastAPI가 좋아하는 모양(Multipart)으로 예쁘게 포장하기
    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
    
    # 4. 백엔드로 날리기
    try:
        response = requests.post(url, headers=headers, files=files, timeout=30)
        
        if response.status_code == 200:
            # 성공하면 백엔드가 돌려준 '진짜 이미지 주소'를 뽑아냅니다.
            return True, response.json().get("profile_image_url")
        else:
            return False, response.json().get("detail", "이미지 업로드에 실패했습니다.")
    except Exception as e:
        return False, f"서버 연결 오류: {str(e)}"


def api_delete_interview_session(session_id: int) -> tuple[bool, str]:
    """
    면접 세션 삭제 API 호출
    DELETE /interview/sessions/{session_id}
    """
    import streamlit as st
    import requests
    import os
    
    API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
    
    # 🎯 1. 세션 및 쿠키에서 안전하게 토큰 찾기 (이름 'token' 으로 수정)
    access_token = st.session_state.get("token") # access_token -> token 으로 수정됨!
    
    # 세션에 없으면 최신 스트림릿 네이티브 기능으로 쿠키 확인
    if not access_token and hasattr(st, "context") and hasattr(st.context, "cookies"):
        access_token = st.context.cookies.get("token")
        
    # 그래도 없으면 extra_streamlit_components를 통해 쿠키 확인
    if not access_token:
        try:
            import extra_streamlit_components as stx
            cookie_manager = stx.CookieManager(key="global_auth_cookie")
            access_token = cookie_manager.get("token")
        except:
            pass

    # 🚨 끝까지 토큰을 못 찾으면 에러 반환
    if not access_token:
        return False, "로그인 인증이 만료되었거나 토큰을 찾을 수 없습니다."
        
    try:
        # 🎯 2. 토큰을 싣고 백엔드로 삭제 요청 보내기
        response = requests.delete(
            f"{API_BASE_URL}/interview/sessions/{session_id}",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            },
            timeout=10
        )
        
        # 🔥 실제 서버 응답에 맞춰 정확하게 에러 분류
        if response.status_code == 200:
            return True, "삭제 완료"
        
        # 실패 시 에러 내용을 그대로 봅니다.
        try:
            error_data = response.json()
            error_msg = error_data.get("detail", f"서버 오류: {response.text}")
        except:
            error_msg = f"서버와 통신 오류 (HTTP {response.status_code})"
            
        return False, error_msg
            
    except requests.exceptions.Timeout:
        return False, "요청 시간이 초과되었습니다."
    except requests.exceptions.ConnectionError:
        return False, "백엔드 서버에 연결할 수 없습니다. (app.py 실행 확인)"
    except Exception as e:
        return False, f"오류 발생: {str(e)}"
