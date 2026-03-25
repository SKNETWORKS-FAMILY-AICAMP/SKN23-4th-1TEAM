"""
File: services/agent_tools_service.py
Author: 김지우
Created: 2026-03-10
Description: LangGraph 에이전트 툴 (자비스 컨트롤 타워)

Modification History:
- 2026-03-10 (김지우): 초기 생성 및 행동 지침 프롬프트 강화
- 2026-03-11 (김지우): 4대 핵심 기능(네비게이션, 첨삭 등) 스키마 복구 및 필수 파라미터 보완
- 2026-03-19 (김지우): 네비게이션 보드(게시판) 추가, 헛소리 방지용 message 파라미터 강제, 웹 검색(Tavily) 툴 추가
"""

AGENT_TOOLS = [
    # 1. 스마트 면접 세팅 및 라우팅 (면접장 이동 툴 - 복구 완료!)
    {
        "type": "function",
        "function": {
            "name": "setup_and_navigate_interview",
            "description": "[행동 지침] 사용자가 '면접 세팅해줘', '시작해', '면접 볼래' 등 면접을 시작하겠다는 의지를 보이면 무조건 이 함수를 호출하세요. 조언으로 넘기지 말고 반드시 프론트엔드 네비게이션을 트리거해야 합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "job_role": {
                        "type": "string",
                        "description": "면접 직무. 사용자가 언급하지 않았으면 '기본 직무'로 설정."
                    },
                    "difficulty": {
                        "type": "string",
                        "enum": ["상", "중", "하"],
                        "description": "면접 난이도. 언급이 없으면 '중'으로 설정."
                    },
                    "persona": {
                        "type": "string",
                        "enum": ["깐깐한 기술팀장", "부드러운 인사담당자", "스타트업 CTO"],
                        "description": "면접관 스타일. 언급이 없으면 '깐깐한 기술팀장'으로 설정."
                    },
                    "use_resume": {
                        "type": "boolean",
                        "description": "사용자가 이력서/기술 스택을 기반으로 면접을 원하면 true, 언급이 없으면 false."
                    },
                    "message": {
                        "type": "string",
                        "description": "사용자에게 보여줄 안내 메시지. (예: '네, 준비를 마쳤습니다. 면접장으로 이동합니다.')"
                    }
                },
                "required": ["job_role", "difficulty", "persona", "use_resume", "message"] 
            }
        }
    },
    
    # 2. 이력서 정밀 분석 및 꼬리 질문 추출
    {
        "type": "function",
        "function": {
            "name": "analyze_resume_and_generate_questions",
            "description": "[행동 지침] 사용자가 이력서/포트폴리오를 업로드하거나 경험을 추가하며 '분석해줘', '예상 질문 뽑아줘'라고 할 때 호출합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "resume_content": {
                        "type": "string",
                        "description": "분석할 전체 이력서 텍스트 또는 새로 추가된 경험 내용"
                    },
                    "question_count": {
                        "type": "integer",
                        "description": "추출할 예상 질문의 개수. 기본값은 3."
                    }
                },
                "required": ["resume_content", "question_count"]
            }
        }
    },

    # 3. 페이지 다이렉트 이동 (게시판 추가 및 헛소리 방지)
    {
        "type": "function",
        "function": {
            "name": "navigate_to_page",
            "description": "[행동 지침] 사용자가 '내 정보 볼래', '이력서 관리 갈래', '게시판 갈래', '홈으로 가줘' 등 특정 화면/메뉴로 이동을 원할 때 즉시 호출합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_page": {
                        "type": "string",
                        "enum": ["home", "mypage", "resume", "my_info", "board"],
                        "description": "이동할 목적지 페이지. (home: 홈, mypage: 면접 기록, resume: 이력서 저장소, my_info: 내 정보, board:커뮤니티/게시판 로 구분)"
                    },
                    "message": {
                        "type": "string",
                        "description": "사용자에게 보여줄 안내 메시지. (예: '네, OO 페이지로 이동합니다.') ⚠️ 절대 '면접장으로 이동합니다'라는 말을 쓰지 마세요."
                    }
                },
                "required": ["target_page", "message"]
            }
        }
    },

    # 4. 웹 검색 툴 (Tavily 연동용 신규 추가)
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "[행동 지침] 사용자가 IT 트렌드, 기업 최신 동향, 뉴스 등 최신 웹 정보가 필요한 질문을 하면 무조건 이 툴을 호출하여 검색하세요.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Tavily 검색 API에 전달할 검색 키워드 또는 문장"
                    }
                },
                "required": ["query"]
            }
        }
    },

    # 5. 자소서/이력서 전문 첨삭
    {
        "type": "function",
        "function": {
            "name": "provide_resume_feedback",
            "description": "[행동 지침] 사용자가 자기소개서나 이력서의 피드백, 첨삭, 교정을 요청할 때 호출합니다. 마크다운 피드백 제공 및 다운로드 버튼 생성을 트리거합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "document_content": {
                        "type": "string",
                        "description": "첨삭을 요청한 자소서/이력서 원문"
                    },
                    "focus_area": {
                        "type": "string",
                        "description": "사용자가 특별히 피드백을 원하는 부분 (예: 직무 적합성, 문법, 성과 강조 등). 없으면 '전체'로 설정."
                    }
                },
                "required": ["document_content"]
            }
        }
    },

    # 6. 기업 면접 정보 검색
    {
        "type": "function",
        "function": {
            "name": "search_company_interview_info",
            "description": "[행동 지침] 사용자가 특정 기업의 면접 후기, 유형, 예상 질문 등을 물어보면 호출하세요.",
            "parameters": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "query_type": {
                        "type": "string",
                        "enum": ["면접 후기", "예상 질문", "코딩테스트", "인적성", "전반적 정보"]
                    }
                },
                "required": ["company", "query_type"]
            }
        }
    },

    # 7. 면접 브리핑 및 분석
    {
        "type": "function",
        "function": {
            "name": "get_interview_briefing",
            "description": "[행동 지침] 면접 종료 후 '브리핑 해줘', '피드백 줘' 등 단일 세션에 대한 결과를 요청할 때 호출합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                    "session_id": {"type": "string", "description": "모르면 'latest'로 설정"}
                },
                "required": ["session_id"]
            }
        }
    },
    
    # 8. 과거 면접 누적 성적 분석
    {
        "type": "function",
        "function": {
            "name": "fetch_interview_analytics",
            "description": "사용자의 과거 면접 누적 성적 및 약점 분석 브리핑을 제공합니다.",
            "parameters": {
                "type": "object",
                "properties": {
                     "period": {"type": "string", "description": "조회 기간 (예: 1주일, 1달)"}
                },
                "required": ["period"]
            }
        }
    }
]