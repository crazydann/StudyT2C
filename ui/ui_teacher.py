import streamlit as st

# ✅ 우리가 만든 새 Teacher 콘솔 UI로 연결
from ui.teacher_console import render_teacher_console


def render(supabase, user):
    

    # 핵심: 새 콘솔 화면 렌더
    render_teacher_console(supabase, user)