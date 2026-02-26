"""
File: app.py
Author: 김지우
Created: 2026-02-26
Description: 메인 화면

Modification History:
- 2026-02-26 (김지우): 초기 생성 및 login.py로 바로 이동 세팅 
"""

import streamlit as st
st.set_page_config(page_title="AIWORK", page_icon="👾", layout="centered")

# login.py로 바로 이동
st.switch_page("pages/login.py")