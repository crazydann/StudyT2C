# ui/teacher/console.py
import streamlit as st

from ui.ui_common import get_role_state
from ui.teacher.data_loaders import fetch_teacher_student_ids, fetch_user_handles_by_ids
from ui.teacher.student_list import render_student_list
from ui.teacher.student_detail import render_student_detail
from ui.teacher.class_dashboard_tab import render_class_dashboard_tab
from services.demo_seed import seed_demo_basic, delete_demo_data
from ui.layout import render_top_bar_with_tabs


def render_teacher_console(supabase, user):
    if "dev_mode" not in st.session_state:
        st.session_state["dev_mode"] = False
    with st.sidebar:
        with st.expander("설정", expanded=False):
            st.toggle("개발 모드", key="dev_mode")
        if bool(st.session_state.get("dev_mode", False)):
            with st.expander("개발자 도구", expanded=False):
                if st.button("데모 데이터 생성", key="t_seed_demo"):
                    try:
                        info = seed_demo_basic()
                        st.success(f"완료: {info['teacher']['handle']} 등")
                    except Exception as e:
                        st.error(str(e))
                if st.button("데모 데이터 삭제", key="t_delete_demo", type="secondary"):
                    try:
                        result = delete_demo_data()
                        st.success(result.get("message", "삭제 완료.")) if result.get("ok") else st.error(result.get("message", "실패"))
                    except Exception as e:
                        st.error(str(e))

    teacher_id = user.get("id")
    teacher_handle = user.get("handle") or "teacher"
    selected = render_top_bar_with_tabs("선생님", teacher_handle, ["학생별 상세", "반 요약"], key="teacher_main_tab")

    state = get_role_state("teacher", teacher_id)
    state.setdefault("selected_student", None)
    student_ids = fetch_teacher_student_ids(supabase, teacher_id)
    handle_map = fetch_user_handles_by_ids(supabase, student_ids)

    if selected == "학생별 상세":
        if state["selected_student"] is None:
            render_student_list(state, student_ids, handle_map)
        else:
            render_student_detail(supabase, teacher_id, state, handle_map)
    else:
        # 반 요약: 학원 관리가 아닌 학생별 개인화 맥락의 요약
        render_class_dashboard_tab(state, student_ids, handle_map)