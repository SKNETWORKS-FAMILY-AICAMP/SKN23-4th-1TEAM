"""
File: ai/agent.py
Author: 김지우
Created: 2026-03-10
Description: AI 에이전트 라우팅 중심부
"""
import json
import os
from dotenv import load_dotenv, find_dotenv  
from openai import OpenAI

from backend.services.agent_tools_service import AGENT_TOOLS
from backend.services.tavily_service import get_web_context_first

_base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) 

def run_agent(user_message: str) -> dict:
    load_dotenv(find_dotenv())
    load_dotenv(dotenv_path=os.path.join(_base_dir, ".env")) 
    
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    
    if not api_key:
        print("[Agent Error] OPENAI_API_KEY가 비어있습니다.")
        return {
            "action": "chat",
            "message": "서버에 API Key가 설정되지 않았습니다.",
            "target_page": "",
            "session_params": {}
        }
        
    client = OpenAI(api_key=api_key)
    
    system_prompt = (
        "당신은 AIWORK 플랫폼의 중앙 컨트롤 타워 AI '사자개'입니다.\n"
        "사용자의 의도를 파악하고 제공된 함수(tools) 중 가장 적절한 것을 반드시 호출하여 플랫폼을 제어하세요.\n"
        "함수 호출이 필요 없는 단순 인사나 질문에만 텍스트로 대답하세요."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", 
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            tools=AGENT_TOOLS, 
            tool_choice="auto"
        )

        response_message = response.choices[0].message

        if response_message.tool_calls:
            tool_call = response_message.tool_calls[0]
            function_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            
            # 면접 세팅
            if function_name == "setup_and_navigate_interview":
                return {
                    "action": "navigate", 
                    "target_page": "interview",
                    "session_params": {
                        "job_role": args.get("job_role", "기본 직무"),
                        "difficulty": args.get("difficulty", "중"),
                        "persona": args.get("persona", "깐깐한 기술팀장"),
                        "use_resume": args.get("use_resume", False)
                    },
                    "message": args.get("message", f"네, {args.get('job_role')} 대비용 '{args.get('difficulty')}' 난이도 면접을 준비했습니다. 면접장으로 이동합니다.")
                }
            
            # 일반 페이지 이동
            elif function_name == "navigate_to_page":
                target = args.get("target_page", "home")
                fallback_msg = f"{target} 페이지로 즉시 이동합니다."
                return {
                    "action": "navigate",
                    "target_page": target,
                    "session_params": {},
                    "message": args.get("message", fallback_msg)
                }

            # 이력서 분석
            elif function_name == "analyze_resume_and_generate_questions":
                return {
                    "action": "analyze_resume",
                    "target_page": "",
                    "session_params": {
                        "resume_content": args.get("resume_content", ""),
                        "question_count": args.get("question_count", 3)
                    },
                    "message": "업로드해주신 이력서를 시스템에 저장하고 분석 중입니다. 잠시만 기다려주세요..."
                }

            # 전문 첨삭
            elif function_name == "provide_resume_feedback":
                from backend.services.llm_service import generate_resume_feedback
                doc_content = args.get("document_content", "")
                focus = args.get("focus_area", "전체")
                feedback_markdown = generate_resume_feedback(doc_content, focus)
                
                return {
                    "action": "provide_feedback",
                    "target_page": "",
                    "session_params": {
                        "feedback_result": feedback_markdown
                    },
                    "message": feedback_markdown
                }

            # 일반 웹 검색 및 한국어 번역
            elif function_name == "web_search":
                query = args.get("query", "")
                raw_search_result = get_web_context_first(query)
                
                if not raw_search_result:
                    search_result = "웹 검색을 완료했지만 명확한 답변을 찾지 못했습니다."
                else:
                    trans_response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "주어진 웹 검색 결과를 한국어로 번역하고 가독성 좋게 요약해주세요. 전문적이고 친절한 AI 어드바이저 톤을 유지하세요."},
                            {"role": "user", "content": raw_search_result}
                        ]
                    )
                    search_result = trans_response.choices[0].message.content
                    
                return {
                    "action": "chat",
                    "target_page": "",
                    "session_params": {},
                    "message": search_result
                }

            # 누적 성적/브리핑 확인 시 내 기록(history) 이동
            elif function_name in ["fetch_interview_analytics", "get_interview_briefing"]:
                return {
                    "action": "navigate",
                    "target_page": "history",
                    "session_params": {},
                    "message": "네, 그동안의 면접 성적과 상세한 피드백을 확인하실 수 있도록 '내 기록' 페이지로 안내해 드릴게요!"
                }

            # 기업 면접 정보 검색 및 한국어 번역
            elif function_name == "search_company_interview_info":
                company = args.get("company", "")
                query_type = args.get("query_type", "예상 질문")
                search_query = f"{company} 신입 개발자 {query_type} 면접 후기"
                
                raw_search_result = get_web_context_first(search_query)
                
                if not raw_search_result:
                    search_result = f"{company}의 {query_type}에 대한 명확한 최신 정보를 찾지 못했습니다."
                else:
                    trans_response = client.chat.completions.create(
                        model="gpt-4o-mini",
                        messages=[
                            {"role": "system", "content": "주어진 기업 면접 검색 결과를 한국어로 번역하고 가독성 좋게 요약해주세요. 취업 준비생에게 도움이 되는 친절한 톤을 유지하세요."},
                            {"role": "user", "content": raw_search_result}
                        ]
                    )
                    search_result = f"[{company} {query_type} 검색 결과]\n\n{trans_response.choices[0].message.content}"
                    
                return {
                    "action": "chat",
                    "target_page": "",
                    "session_params": {},
                    "message": search_result
                }

            # 미구현 기능
            else:
                return {
                    "action": "chat",
                    "target_page": "",
                    "session_params": args,
                    "message": f"[{function_name}] 기능은 아직 개발 중이거나 연결되지 않았습니다."
                }

        # 일반 대화
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