import os


# 앱 전역 설정 값 상수화
REMOTE_DB_PATH = "3team/AI_Interviewer/db/interview.db"
REMOTE_APP_DIR = "~/3team/app"
REMOTE_APP_FILE = "app.py"
STREAMLIT_PORT = 8502


# 추가 부분
# 백엔드 API 기본 주소 (배포 시 이 부분만 실제 도메인으로 변경)
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api")

# 소셜 로그인 환경 변수 (프론트 버튼 링크용)
GOOGLE_URI = f"{API_BASE_URL}/auth/google/start"
KAKAO_URI = f"{API_BASE_URL}/auth/kakao/start"