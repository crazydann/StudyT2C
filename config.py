import os
import streamlit as st
from dotenv import load_dotenv

# 로컬 환경인 경우 .env 파일을 읽어옵니다. (Streamlit Cloud에서는 무시됨)
load_dotenv()


def get_env_var(var_name: str):
    """
    OS 환경변수(.env)를 먼저 확인하고, 없으면 Streamlit secrets에서 가져옵니다.
    - 로컬: .env / export 환경변수
    - Streamlit: .streamlit/secrets.toml 또는 Cloud secrets
    """
    val = os.environ.get(var_name)
    if val:
        return val

    try:
        if var_name in st.secrets:
            return st.secrets[var_name]
    except Exception:
        pass

    return None


def get_supabase_url() -> str:
    url = get_env_var("SUPABASE_URL")
    if not url:
        raise ValueError("SUPABASE_URL이 설정되지 않았습니다. (.env 또는 .streamlit/secrets.toml 확인)")
    return url


def get_supabase_anon_key() -> str:
    """
    v2.5 호환:
    - 일부 코드/환경은 SUPABASE_KEY를 사용
    - 일부는 SUPABASE_ANON_KEY를 사용
    -> 둘 중 하나라도 있으면 anon key로 사용
    """
    key = get_env_var("SUPABASE_ANON_KEY") or get_env_var("SUPABASE_KEY")
    if not key:
        raise ValueError("SUPABASE_ANON_KEY 또는 SUPABASE_KEY가 설정되지 않았습니다. (.env 또는 secrets.toml 확인)")
    return key


def get_supabase_service_role_key() -> str | None:
    """
    선택: 서버 권한이 필요한 작업이 생길 때 사용(배포/운영 시 주의).
    로컬 개발에서는 없어도 동작하도록 None 허용.
    """
    return get_env_var("SUPABASE_SERVICE_ROLE_KEY")


# 환경 변수 맵핑 (기존 코드 호환용 상수)
SUPABASE_URL = get_env_var("SUPABASE_URL")
SUPABASE_ANON_KEY = get_env_var("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = get_env_var("SUPABASE_SERVICE_ROLE_KEY")
GROQ_API_KEY = get_env_var("GROQ_API_KEY")
RESEND_API_KEY = get_env_var("RESEND_API_KEY")

# ✅ V3 준비: 역할(role) 단일화 (app.py 라우팅과 DB users.role 기준)
ROLES = ["student", "parent", "teacher"]

# 기타 공통 상수
STATUS = ["studying", "break"]
SUBJECTS = ["KOREAN", "ENGLISH", "MATH", "SCIENCE", "OTHER"]


def is_student_login_app() -> bool:
    """
    studyt2c.streamlit.app 배포에서 True.
    이 모드에서는 로그인 화면 → 로그인학생 화면(문제 채점기 + AI 튜터만)만 노출.
    admin.studyt2c.streamlit.app 등 다른 배포에서는 False 로 두면 기존 계정 선택 화면 유지.
    """
    v = get_env_var("STUDENT_LOGIN_APP")
    if not v:
        return False
    return str(v).strip().lower() in ("1", "true", "yes")