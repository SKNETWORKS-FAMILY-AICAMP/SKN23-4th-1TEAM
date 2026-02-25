"""
File: services/llm_service.py
Description: OpenAI GPT 호출 헬퍼
             - ai/prompt.py의 강력한 평가 프롬프트(JSON Schema, Rubric) 완벽 내장
             - 영문 DB 질문을 자연스러운 한국어 구어체로 자동 번역
             - 4점 이하 시에만 꼬리질문(최대 2회) 허용 통제
             - 할루시네이션 방지 특별 원칙 적용
"""

import os
import json
import re
from openai import OpenAI
from services.rag_service import get_resume_context_for_question

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

# ─── 페르소나 설명 맵 ─────────────────────────────────────────
PERSONA_MAP = {
    "깐깐한 기술팀장": "당신은 10년 경력의 깐깐한 기술팀장입니다. 의심 많고 세부사항을 완벽하게 파고드는 직설적인 스타일입니다.",
    "부드러운 인사담당자": "당신은 경험 많은 HR 매니저입니다. 부드럽고 공감하는 톤으로 대화를 이끌지만, 동기를 깊게 파고듭니다.",
    "스타트업 CTO": "당신은 성장지향적인 스타트업 CTO입니다. 실용성과 비즈니스 임팩트를 중시합니다.",
}

# ==============================================================================
# 💡 지우님의 ai/prompt.py 핵심 프롬프트 (이 파일에 직접 내장!)
# ==============================================================================

SYSTEM_PROMPT_EVAL = """
너는 실무 중심의 기술 면접관이자 채점기다. 말투는 간결하고 단정하며, 객관적으로 평가한다.

[🚨 데이터 기반 제약 및 할루시네이션 방지 특별 원칙 🚨]
- 반드시 CONTEXT(예: RAG 결과)와 QUESTION_LIST에 포함된 정보만 근거로 사용한다.
- CONTEXT/QUESTION_LIST에 없는 사실, 정의, 모범답안을 절대 임의로 지어내지 않는다. (외부 사전 지식 개입 금지)
- 근거가 부족하면 반드시 "근거 부족"이라고 명시하고, evidence는 []로 둔다.
- 사용자의 답변이 본인의 모르는 것을 인정하는 것이 아닌, 질문과 전혀 다른 주제의 엉뚱한 답변일 경우 엄격하게 감점을 부여한다.

[평가 기준(루브릭)]
- correctness(정확성): 핵심 개념/용어/논리의 정확성, 오개념/모순 여부
- depth(깊이): 트레이드오프, 예시/근거, 경계조건, 실무 관점
- structure(구조): 서론-본론-결론, 단계적 설명, 포인트 우선순위
- clarity(명확성): 문장 명료성, 애매한 표현 최소화, 핵심 요약
"""

EVAL_JSON_SCHEMA_INSTRUCTIONS = """
너의 출력은 반드시 JSON 객체 1개만 반환한다. (추가 텍스트/설명/코드블록 절대 금지)
반드시 아래 스키마를 정확히 따른다.

{
    "question_id": "<입력으로 받은 question_id 그대로>",
    "score": <0-100 정수>,
    "passed": <true|false>,
    "feedback": "<지원자에게 면접관이 직접 말하는 듯한 자연스러운 한국어 피드백 1~3문장>",
    "strengths": ["<좋았던 점 1>", "<좋았던 점 2>"],
    "weaknesses": ["<아쉬운 점 1>", "<아쉬운 점 2>"],
    "missing_points": ["<모범답안 대비 누락된 핵심 포인트>"],
    "follow_up_needed": <true|false>,
    "follow_up_question": "<follow_up_needed가 true면 1문장 1개, 아니면 빈 문자열>",
    "next_question_translated": "<follow_up_needed가 false일 때, 제공된 [NEXT_MAIN_QUESTION]의 영문/딱딱한 내용을 실제 면접관이 말하듯 아주 자연스러운 '한국어 구어체'로 번역한 문장. true면 빈 문자열>",
    "rubric_hits": {
        "clarity": <0-5 정수>,
        "correctness": <0-5 정수>,
        "depth": <0-5 정수>,
        "structure": <0-5 정수>
    }
}
"""

EVAL_FEWSHOT = """
[FEW-SHOT #1: 영어 질문을 한국어로 번역하는 예시]
INPUT:
[QUESTION_LIST_ROW]: {"id": "101", "question": "Explain differences between List and Tuple in Python."}
[USER_ANSWER_STT]: "리스트는 값을 바꿀 수 있고 튜플은 못 바꿉니다."
[NEXT_MAIN_QUESTION]: "What is GIL in Python?"

OUTPUT:
{
  "question_id": "101",
  "score": 76,
  "passed": true,
  "feedback": "가변과 불변의 핵심 차이는 정확히 짚어주셨네요. 다만 튜플의 해시 가능성 같은 추가 포인트가 빠져서 조금 아쉽습니다.",
  "strengths": ["가변/불변 차이를 정확히 언급함"],
  "weaknesses": ["추가 핵심 포인트 누락"],
  "missing_points": ["튜플은 dict 키로 사용될 수 있음"],
  "follow_up_needed": false,
  "follow_up_question": "",
  "next_question_translated": "그럼 다음 질문 드리겠습니다. 혹시 파이썬에서 GIL(Global Interpreter Lock)이 무엇인지, 그리고 어떤 영향을 미치는지 설명해주실 수 있을까요?",
  "rubric_hits": {"clarity": 4, "correctness": 4, "depth": 2, "structure": 3}
}
"""

def build_eval_user_prompt(question_list_row: dict, user_answer_text: str, rag_context: dict) -> str:
    return f"""
    주어진 입력을 평가하라.

    [QUESTION_LIST_ROW]
    {json.dumps(question_list_row, ensure_ascii=False)}

    [CONTEXT (이력서 기반 RAG 결과)]
    {json.dumps(rag_context, ensure_ascii=False)}

    [USER_ANSWER_STT]
    "{user_answer_text}"
    """

# ==============================================================================
# 🚀 메인 평가 엔진 (점수 + 피드백 + 꼬리질문 + 영문DB번역 한방 처리!) - 
# ==============================================================================
def evaluate_and_respond(
    question: str, 
    answer: str, 
    job_role: str,
    difficulty: str,
    persona_style: str,
    user_id: str, 
    resume_text: str | None,
    next_main_question: str | None,
    followup_count: int
) -> dict:
    
    # 1. RAG 컨텍스트 추출
    rag_context_text = None
    if resume_text:
        rag_context_text = get_resume_context_for_question(answer, user_id)

    # 2. 긴급 통제 규칙 (4점 이하일 때만 꼬리물기, 최대 2회)
    control_rules = f"""
[🚨 긴급 통제 규칙 (매우 중요) 🚨]
1. 현재 이 문항에 대한 꼬리질문 누적 횟수: {followup_count}회
2. 만약 이번 답변의 score가 40점(100점 만점 기준 40점 = 10점 만점 기준 4점) 이하라면 꼬리질문(follow_up_needed=true)을 1회 생성하라.
3. 단, 꼬리질문 누적 횟수가 2회 이상이거나, score가 40점을 초과하여 양호하다면 절대 꼬리질문을 생성하지 마라 (follow_up_needed=false).
    """

    # 3. 시스템 프롬프트 조립
    persona_desc = PERSONA_MAP.get(persona_style, PERSONA_MAP["깐깐한 기술팀장"])
    sys_prompt = f"{persona_desc}\n\n{SYSTEM_PROMPT_EVAL}\n\n{EVAL_JSON_SCHEMA_INSTRUCTIONS}\n\n{EVAL_FEWSHOT}\n\n{control_rules}"

    # 4. 유저 프롬프트 조립
    question_row_dict = {"id": "current", "question": question, "answer": "모범 답안을 기준으로 평가하되 없으면 일반 기술 상식 활용"} 
    rag_context_dict = {"resume_context": rag_context_text} if rag_context_text else {"note": "이력서 관련 내용 없음"}
    
    user_prompt = build_eval_user_prompt(question_row_dict, answer, rag_context_dict)
    
    if next_main_question:
        user_prompt += f"\n\n[NEXT_MAIN_QUESTION]\n{next_main_question}\n(위 질문을 자연스러운 한국어 면접 말투로 번역하여 next_question_translated 필드에 넣을 것)"

    # 5. LLM 호출 (JSON 강제)
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": user_prompt}
            ],
            response_format={ "type": "json_object" },
            temperature=0.2,
        )
        
        raw_json = response.choices[0].message.content.strip()
        data = json.loads(raw_json)
        
        # 100점 만점을 우리 시스템 기준인 10점 만점으로 스케일링
        score = float(data.get("score", 50)) / 10.0 
        feedback = data.get("feedback", "답변 감사합니다.")
        follow_up_needed = data.get("follow_up_needed", False)
        follow_up_question = data.get("follow_up_question", "")
        next_q_trans = data.get("next_question_translated", "")

        # 6. 최종 텍스트 조립
        reply_text = f"{feedback}\n\n"
        
        if follow_up_needed and follow_up_question:
            # 꼬리질문 태그 강제 부착
            if "💡 추가 질문:" not in follow_up_question:
                reply_text += f"💡 추가 질문: {follow_up_question}"
            else:
                reply_text += follow_up_question
        else:
            if next_main_question:
                translated = next_q_trans if next_q_trans else next_main_question
                reply_text += f"{translated} [NEXT_MAIN]"
            else:
                reply_text += "수고하셨습니다. 준비된 모든 질문이 끝났습니다. [INTERVIEW_END]"

        return {
            "score": score,
            "feedback": feedback,
            "reply_text": reply_text.strip(),
            "is_followup": follow_up_needed
        }

    except Exception as e:
        return {
            "score": 5.0,
            "feedback": "평가 중 오류가 발생했습니다.",
            "reply_text": f"네, 알겠습니다. 다음 질문 드릴게요.\n**{next_main_question}** [NEXT_MAIN]" if next_main_question else "[INTERVIEW_END]",
            "is_followup": False
        }


# ─── 레거시 호환성 유지용 (혹시 모를 에러 방지) ──────────────────────────
def score_answer(question: str, answer: str, job_role: str) -> tuple[float, str]:
    return 5.0, "통합 평가 엔진(evaluate_and_respond)으로 대체되었습니다."

def get_ai_response(messages: list, *args, **kwargs) -> str:
    return "통합 평가 엔진(evaluate_and_respond)으로 대체되었습니다."


# ─── 이력서 핵심 키워드 추출 (DB 검색용) ──────────────────────
def extract_keywords_from_resume(resume_text: str) -> list[str]:
    if not resume_text:
        return []
    
    prompt = f"""다음 이력서 내용에서 지원자가 다룬 핵심 기술 스택, 프레임워크, 프로그래밍 언어를 딱 3개만 추출해서 쉼표(,)로 구분해 반환하세요.
    (예시: Python, FastAPI, MySQL)
    
    이력서 내용:
    {resume_text[:1500]}
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
        )
        raw = response.choices[0].message.content.strip()
        keywords = [k.strip() for k in raw.split(",") if k.strip()]
        return keywords[:3]
    except Exception:
        return []


# ─── 종합 리포트 생성 ─────────────────────────────────────────
def generate_evaluation(messages: list, job_role: str, difficulty: str, resume_text: str | None = None) -> str:
    conversation_log = "\n".join([f"[{'면접관' if m['role'] == 'assistant' else '지원자'}] {m['content']}" for m in messages])
    resume_section = f"\n지원자 이력서:\n{resume_text[:800]}\n" if resume_text else ""

    eval_prompt = f"""당신은 전문 컨설턴트입니다. 아래 {job_role} 대화를 분석해 마크다운 리포트를 쓰세요.
난이도: {difficulty} {resume_section}

[형식]
## 📊 종합 점수
**XX / 100점** — (총평)

## 🏆 BEST 답변
> 인용
**이유**: 설명

## ✅ 강점
1. **(키워드)**: 설명

## 🔧 개선 제안
| 질문 | 요약 | 모범 방향 |
|---|---|---|

## 🔑 키워드 체크리스트
| 키워드 | 여부 | 비고 |
|---|---|---|

## 📚 추천 학습
- **주제**: 이유

[면접 대화]
{conversation_log}"""
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[{"role": "user", "content": eval_prompt}],
            max_tokens=2000,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"평가 오류: {e}"


# ─── 이력서 종합 AI 분석 (이력서 대시보드용) ──────────────────────
def analyze_resume_comprehensive(resume_text: str, job_role: str) -> dict:
    """이력서를 분석하여 키워드, 예상 질문, 직무 매칭률을 한 번에 JSON으로 추출합니다."""
    if not resume_text:
        return {}

    prompt = f"""
당신은 {job_role} 전문 채용 담당자입니다.
지원자의 이력서를 분석하여 면접 전 프리뷰 데이터를 JSON 형식으로 작성해주세요.

[지원자 이력서]
{resume_text[:2000]}

[출력 JSON 스키마]
반드시 아래 스키마를 정확히 지켜서 출력하세요. 다른 텍스트는 불가합니다.
{{
    "keywords": ["핵심기술1", "핵심기술2", "핵심기술3", "핵심기술4"],
    "expected_questions": [
        "이력서 경험 기반의 날카로운 실무 압박 질문 1",
        "이력서 경험 기반의 날카로운 실무 압박 질문 2",
        "이력서 경험 기반의 날카로운 실무 압박 질문 3"
    ],
    "match_rate": <0~100 사이 정수 (직무 적합도 퍼센트)>,
    "match_feedback": "<{job_role} 직무 관점에서 이력서의 강점과 보완점 2문장 요약>"
}}
"""
    try:
        from openai import OpenAI
        import os
        import json
        import re
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={ "type": "json_object" },
            temperature=0.3,
        )
        raw_json = response.choices[0].message.content.strip()
        data = json.loads(raw_json)
        return data
    except Exception as e:
        print(f"이력서 분석 오류: {e}")
        return {
            "keywords": ["분석 실패"],
            "expected_questions": ["분석 서버에 일시적인 오류가 있습니다."],
            "match_rate": 0,
            "match_feedback": "현재 분석을 제공할 수 없습니다."
        }