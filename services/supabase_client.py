import config
from supabase import create_client, Client
import streamlit as st

@st.cache_resource
def init_supabase() -> Client:
    """Supabase 클라이언트를 초기화하고 캐싱하여 앱 속도를 높입니다."""
    return create_client(config.SUPABASE_URL, config.SUPABASE_ANON_KEY)

supabase = init_supabase()