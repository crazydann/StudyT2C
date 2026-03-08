# ui/mvp_student_view.py
"""
로그인학생 화면: 문제 채점기 + AI 튜터만 노출.
(대시보드 전체·숙제·오답노트·기록 탭은 숨김)
"""
import streamlit as st

import config
from ui.student_dashboard.panels_center import render_center_panel
from ui.student_dashboard.panels_grading import render_grading_panel
from ui.student_dashboard.focus_tracker_component import render_focus_tracker


def _make_image_renderer():
    def _render(img, caption=None):
        try:
            st.image(img, caption=caption, use_container_width=True)
        except TypeError:
            st.image(img, caption=caption, use_column_width=True)
    return _render


def render_mvp_student_view(supabase, user: dict):
    """
    로그인한 MVP 학생 전용: AI 튜터 + 문제 채점기만 표시.
    """
    student_id = (user or {}).get("id")
    student_handle = (user or {}).get("handle") or "student"

    state = st.session_state.get("mvp_student_state") or {}
    state.setdefault("messages", [])
    state.setdefault("graded_items", [])
    state.setdefault("pending_save", None)
    state.setdefault("upload_rotation", {})
    st.session_state["mvp_student_state"] = state

    st.markdown("### 로그인학생 화면")
    st.caption(f"**{student_handle}** · 문제 채점기와 AI 튜터만 사용할 수 있어요.")

    # 로그아웃
    if st.button("로그아웃", key="mvp_logout"):
        st.session_state.pop("mvp_user", None)
        st.session_state.pop("current_user", None)
        st.rerun()

    st.divider()

    try:
        supabase_url = config.get_supabase_url()
        anon_key = config.get_supabase_anon_key()
        if supabase_url and anon_key:
            render_focus_tracker(str(student_id), supabase_url, anon_key)
    except Exception:
        pass

    # AI 튜터 | 문제 채점기 2열
    col_chat, col_grading = st.columns([2, 1])

    with col_chat:
        st.markdown("#### 🤖 AI 튜터")
        render_center_panel(user, str(student_id), state)

    with col_grading:
        st.markdown("#### 📝 문제 채점기")
        render_grading_panel(user, str(student_id), state, _make_image_renderer())
