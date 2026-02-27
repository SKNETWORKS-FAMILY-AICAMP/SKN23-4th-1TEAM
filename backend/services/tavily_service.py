"""
File: services/tavily_service.py
Author: 김지우
Created: 2026-02-25
Description: Tavily 웹 검색 API 호출 헬퍼

Modification History:
- 2026-02-25 (김지우) : 초기 생성
"""
import os
from tavily import TavilyClient

def get_web_context_first(query: str) -> str:
    """사용자의 질문을 바탕으로 Tavily 웹 검색을 수행하고 요약 텍스트를 반환합니다."""
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        return ""
        
    tavily = TavilyClient(api_key=tavily_api_key)
    
    try:
        response = tavily.search(query=query, search_depth="basic", include_answer=True)
        return response.get("answer", "")
    except Exception as e:
        print(f"Tavily 검색 에러: {e}")
        return ""

def get_web_context_second(query: str) -> str:
    """사용자의 질문을 바탕으로 Tavily 웹 검색을 수행하고 요약 텍스트를 반환합니다."""
    tavily_api_key = os.getenv("TAVILY_API_KEY")
    if not tavily_api_key:
        return ""
        
    tavily = TavilyClient(api_key=tavily_api_key)
    
    try:
        response = tavily.search(query=query, search_depth="basic", include_answer=True)
        return response.get("answer", "")
    except Exception as e:
        print(f"Tavily 검색 에러: {e}")
        return ""
