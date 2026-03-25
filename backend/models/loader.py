"""
File: loader.py
Author: 양창일
Created: 2026-02-15
Description: AI 모델을 처음에 한 번 불러오는 파일

Modification History:
- 2026-02-15: 초기 생성
"""

def load_model():
    def fake_model(prompt: str):
        return f"AI 응답: {prompt}"
    return fake_model

model = load_model()
