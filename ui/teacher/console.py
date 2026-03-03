# ui/teacher/console.py
import streamlit as st

from ui.ui_common import get_role_state
from ui.teacher.data_loaders import fetch_teacher_student_ids, fetch_user_handles_by_ids
from ui.teacher.student_list import render_student_list
from ui.teacher.student_detail import render_student_detail
from ui.teacher.class_dashboard_tab import render_class_dashboard_tab


def render_teacher_console(supabase, user):
    # 개발 모드 토글(상단에 항상 보이게)
    if "dev_mode" not in st.session_state:
        st.session_state["dev_mode"] = False
    st.toggle("🧪 개발 모드", key="dev_mode")

    teacher_id = user.get("id")
    teacher_handle = user.get("handle") or "teacher"

    st.title(f"Teacher Console - {teacher_handle}")

    state = get_role_state("teacher", teacher_id)
    state.setdefault("selected_student", None)

    student_ids = fetch_teacher_student_ids(supabase, teacher_id)
    handle_map = fetch_user_handles_by_ids(supabase, student_ids)

    tab_dash, tab_students = st.tabs(["📊 반 대시보드", "👩‍🎓 학생별 상세"])

    with tab_dash:
        render_class_dashboard_tab(state, student_ids, handle_map)

    with tab_students:
        if state["selected_student"] is None:
            render_student_list(state, student_ids, handle_map)
        else:
            render_student_detail(supabase, teacher_id, state, handle_map)