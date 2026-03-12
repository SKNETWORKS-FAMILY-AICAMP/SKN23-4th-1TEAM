"""
File: ai/agent.py
Author: 김지우 (수석 엔지니어)
Created: 2026-03-10
Description: AI 에이전트 라우팅 중심부 (FastAPI 연동용)

Modification History:
- 2026-03-10 (김지우): 초기 생성
- 2026-03-11 (AI 에이전트): 4대 핵심 기능(Zero-Click Navigation, 첨삭 등) JSON 제어 신호 분기 처리 추가
"""
import json
import os
from dotenv import load_dotenv, find_dotenv  
from openai import OpenAI

# 백엔드 경로에 맞게 Import 
from backend.services.agent_tools_service import AGENT_TOOLS

_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 

def run_agent(user_message: str) -> dict:
    # 1. 환경변수 및 API 키 세팅
    load_dotenv(find_dotenv())
    load_dotenv(dotenv_path=os.path.join(_base_dir, ".env")) 
    
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    
    if not api_key:
        print("[Agent Error] OPENAI_API_KEY가 비어있습니다. .env 파일을 확인하세요.")
        return {
            "action": "chat",
            "message": "서버에 API Key가 설정되지 않았습니다. 백엔드의 .env 파일에 OPENAI_API_KEY가 있는지 확인해주세요.",
            "target_page": "",
            "session_params": {}
        }
        
    client = OpenAI(api_key=api_key)
    
    # 2. 시스템 프롬프트 설정 (사자개 페르소나)
    system_prompt = (
        "당신은 AIWORK 플랫폼의 중앙 컨트롤 타워 AI '사자개'입니다.\n"
        "사용자의 의도를 파악하고 제공된 함수(tools) 중 가장 적절한 것을 반드시 호출하여 플랫폼을 제어하세요.\n"
        "함수 호출이 필요 없는 단순 인사나 질문에만 텍스트로 대답하세요."
    )

    try:
        # 3. LLM 호출
        response = client.chat.completions.create(
            model="gpt-4o-mini", # 4.1-mini는 오타일 수 있어 4o-mini로 권장
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            tools=AGENT_TOOLS, 
            tool_choice="auto"
        )

        response_message = response.choices[0].message

        # 4. Function Calling 분기 처리 (프론트엔드로 보낼 JSON 명령 생성)
        if response_message.tool_calls:
            tool_call = response_message.tool_calls[0]
            function_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            # 면접 세팅 함수가 호출된 경우 (Zero-Click Navigation)
            if function_name == "setup_and_navigate_interview":
                return {
                    "action": "navigate", # 프론트에서 페이지 전환을 수행할 트리거
                    "target_page": "interview",
                    "session_params": {
                        "job_role": args.get("job_role", "기본 직무"),
                        "difficulty": args.get("difficulty", "중"),
                        "persona": args.get("persona", "깐깐한 기술팀장"),
                        "use_resume": args.get("use_resume", False)
                    },
                    "message": f"네, {args.get('job_role')} 대비용 '{args.get('difficulty')}' 난이도 면접을 준비했습니다. 면접장으로 이동합니다."
                }
            
            # 페이지 다이렉트 이동
            elif function_name == "navigate_to_page":
                target = args.get("target_page", "home")
                page_name_kr = {"home": "홈", "mypage": "면접 기록", "resume": "이력서 저장소", "my_info": "내 정보"}.get(target, target)
                return {
                    "action": "navigate",
                    "target_page": target,
                    "session_params": {},
                    "message": f"{page_name_kr} 페이지로 즉시 이동합니다."
                }

            # 이력서 분석 및 꼬리질문 추출
            elif function_name == "analyze_resume_and_generate_questions":
                return {
                    "action": "analyze_resume", # 프론트에서 업로드/분석 모달을 띄울 트리거
                    "target_page": "",
                    "session_params": {
                        "resume_content": args.get("resume_content", ""),
                        "question_count": args.get("question_count", 3)
                    },
                    "message": "업로드해주신 이력서를 시스템에 저장하고 분석 중입니다. 잠시만 기다려주세요..."
                }

            # 자소서/이력서 전문 첨삭
            elif function_name == "provide_resume_feedback":
                from backend.services.llm_service import generate_resume_feedback
                
                doc_content = args.get("document_content", "")
                focus = args.get("focus_area", "전체")
                
                # 첨삭 로직 실행
                feedback_markdown = generate_resume_feedback(doc_content, focus)
                
                return {
                    "action": "provide_feedback",
                    "target_page": "",
                    "session_params": {
                        "feedback_result": feedback_markdown
                    },
                    "message": feedback_markdown
                }

            # 기타 추가 기능들 (기업 검색, 브리핑 등)
            else:
                return {
                    "action": "chat",
                    "target_page": "",
                    "session_params": args,
                    "message": f"[{function_name}] 요청을 접수했습니다. 데이터를 불러오는 중입니다..."
                }

        # 5. 일반 대화인 경우 (action: "chat")
        return {
            "action": "chat",
            "message": response_message.content,
            "target_page": "",
            "session_params": {}
        }

    except Exception as e:
        print(f"[Agent Error] {e}")
        return {
            "action": "chat",
            "message": "AI 서버 연결이 불안정합니다. 잠시 후 다시 시도해주세요.",
            "target_page": "",
            "session_params": {}
        }