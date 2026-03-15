# ui/teacher/console.py
import streamlit as st

from ui.ui_common import get_role_state, filter_student_ids_for_mvp
from ui.teacher.data_loaders import fetch_teacher_student_ids, fetch_user_handles_by_ids
from ui.teacher.student_list import render_student_list
from ui.teacher.student_detail import render_student_detail
from ui.teacher.class_dashboard_tab import render_class_dashboard_tab
from services.demo_seed import seed_demo_basic, delete_demo_data
from ui.layout import render_top_bar_with_tabs


def render_teacher_console(supabase, user):
    if "dev_mode" not in st.session_state:
        st.session_state["dev_mode"] = False

    teacher_id = user.get("id")
    teacher_handle = user.get("handle") or "teacher"
    selected = render_top_bar_with_tabs("선생님", teacher_handle, ["학생별 상세", "반 요약"], key="teacher_main_tab")

    state = get_role_state("teacher", teacher_id)
    state.setdefault("selected_student", None)
    student_ids = fetch_teacher_student_ids(supabase, teacher_id)
    handle_map = fetch_user_handles_by_ids(supabase, student_ids)
    student_ids = filter_student_ids_for_mvp(student_ids, handle_map)
    handle_map = {k: v for k, v in handle_map.items() if str(k) in {str(i) for i in student_ids}}

    if selected == "학생별 상세":
        if state["selected_student"] is None:
            if not student_ids:
                st.info("표시할 학생이 없습니다. (MVP: David, Joshua만 표시됩니다.)")
                return
            render_student_list(state, student_ids, handle_map)
        else:
            render_student_detail(supabase, teacher_id, state, handle_map)
    else:
        # 반 요약: 학원 관리가 아닌 학생별 개인화 맥락의 요약
        render_class_dashboard_tab(state, student_ids, handle_map)