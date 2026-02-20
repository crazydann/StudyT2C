# services/supabase_client.py
import streamlit as st
from supabase import create_client, Client

import config


@st.cache_resource
def _cached_client(url: str, key: str) -> Client:
    """
    (url, key) 조합으로 Supabase Client를 캐시.
    ✅ key가 바뀌면 Streamlit 캐시 키도 바뀌어서 자동으로 새 클라이언트를 만든다.
    """
    return create_client(url, key)


def get_supabase_anon() -> Client:
    """
    앱 전역에서 사용할 기본 Supabase(anon) 클라이언트.
    """
    url = config.get_supabase_url()
    key = config.get_supabase_anon_key()
    return _cached_client(url, key)


def get_supabase_service() -> Client | None:
    """
    선택: service role 클라이언트.
    - 키가 없으면 None 반환
    """
    url = config.get_supabase_url()
    service_key = config.get_supabase_service_role_key()
    if not service_key:
        return None
    return _cached_client(url, service_key)


# v2.5 코드 호환: 기존 import 스타일 유지
supabase = get_supabase_anon()
supabase_anon = supabase
supabase_service = get_supabase_service()