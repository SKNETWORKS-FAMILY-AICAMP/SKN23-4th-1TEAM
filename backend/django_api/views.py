from .view_modules.admin_views import admin_query, admin_sql
from .view_modules.agent import agent_chat
from .view_modules.auth import (
    auth_check_email,
    auth_login,
    auth_logout,
    auth_me,
    auth_profile_image,
    auth_refresh,
    auth_reset_password,
    auth_send_reset_email,
    auth_send_signup_email,
    auth_signup,
    auth_unlock,
    auth_upgrade,
    auth_verify,
    auth_withdraw,
    social_google_callback,
    social_google_start,
    social_kakao_callback,
    social_kakao_start,
    social_naver_callback,
    social_naver_start,
)
from .view_modules.board import (
    board_create_answer,
    board_delete_answer,
    board_feedback,
    board_question_resource,
    board_questions_collection,
    board_toggle_like,
)
from .view_modules.home import home_guide, home_memos, home_news, home_proofread_file
from .view_modules.infer import (
    attitude_infer,
    infer_evaluate_turn,
    infer_ingest,
    infer_proofread,
    infer_questions,
    infer_realtime_token,
    infer_start,
    infer_stt,
    infer_tts,
)
from .view_modules.interview import (
    interview_analyze_resume,
    interview_chat,
    interview_evaluate,
    interview_save_details,
    interview_session_resource,
    interview_sessions,
    interview_store_resume,
)
from .view_modules.jobs import jobs_search
from .view_modules.resumes import resumes_collection, resumes_delete, resumes_latest
