import streamlit as st

# ✅ 우리가 만든 새 Parent 콘솔 UI로 연결
from ui.parent_console import render_parent_console


def render(supabase, user):
    # 헤더는 유지(원하면 바꿔도 됨)
    st.title(f"👨‍👩‍👧 Parent Console - {user.get('handle', '')}")

    # 핵심: 새 콘솔 화면 렌더
    render_parent_console(supabase, user)