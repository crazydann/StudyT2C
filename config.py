import os
import streamlit as st
from dotenv import load_dotenv

# 로컬 환경인 경우 .env 파일을 읽어옵니다. (Streamlit Cloud에서는 무시됨)
load_dotenv()

def get_env_var(var_name):
    """OS 환경변수(.env)를 먼저 확인하고, 없으면 Streamlit secrets에서 가져옵니다."""
    # 1. 로컬 .env (os.environ)에서 먼저 찾기
    val = os.environ.get(var_name)
    if val:
        return val
    
    # 2. 없으면 Streamlit Cloud의 secrets에서 찾기 (파일이 없어도 에러 안 나게 예외 처리)
    try:
        if var_name in st.secrets:
            return st.secrets[var_name]
    except Exception:
        pass
        
    return None

# 환경 변수 맵핑
SUPABASE_URL = get_env_var("SUPABASE_URL")
SUPABASE_ANON_KEY = get_env_var("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = get_env_var("SUPABASE_SERVICE_ROLE_KEY")
GROQ_API_KEY = get_env_var("GROQ_API_KEY")

# 앱에서 공통으로 사용할 상수들
ROLES = ["student", "parent", "admin"]
STATUS = ["studying", "break"]
SUBJECTS = ["KOREAN", "ENGLISH", "MATH", "SCIENCE", "OTHER"]