# ui/teacher/student_detail.py
import streamlit as st

from ui.ui_errors import show_error
from shared_summary import render_shared_summary

from ui.teacher.consult_tab import render_consult_tab
from ui.teacher.homework_tab import render_homework_tab
from ui.teacher.ai_report_tab import render_teacher_ai_report_tab
from ui.focus_ui import render_focus_section


def render_student_detail(supabase, teacher_id: str, state: dict, handle_map: dict):
    sel = state.get("selected_student")

    if isinstance(sel, dict):
        student_id = sel.get("id")
        student_handle = sel.get("handle") or (handle_map.get(student_id) if student_id else None) or "student"
    else:
        student_id = sel
        student_handle = handle_map.get(str(student_id)) or "student"

    if not student_id:
        st.warning("학생이 선택되지 않았습니다.")
        return

    # 학생 설정은 어드민 상단 '학생 설정' 팝오버에서 표시 (사이드바 제거)

    row = st.columns([1, 4])
    with row[0]:
        if st.button("🔙 목록으로", key="t_back"):
            state["selected_student"] = None
            st.rerun()
    with row[1]:
        st.markdown(f"<span style='font-size:16px;font-weight:600;'>{student_handle}</span>", unsafe_allow_html=True)

    tab_labels = ["맞춤 보강·성취도", "상담", "숙제", "집중현황", "요약"]
    selected = st.radio("탭", options=tab_labels, horizontal=True, key="teacher_detail_tab", label_visibility="collapsed")

    if selected == "맞춤 보강·성취도":
        render_teacher_ai_report_tab(str(student_id), student_handle)
    elif selected == "상담":
        render_consult_tab(supabase, teacher_id, str(student_id))
    elif selected == "숙제":
        render_homework_tab(supabase, str(student_id))
    elif selected == "집중현황":
        render_focus_section(str(student_id), student_handle)
    else:
        try:
            render_shared_summary(supabase, str(student_id), student_handle, "teacher", teacher_id)
        except Exception as e:
            show_error("Shared Summary 로드 실패", e, context="render_shared_summary", show_trace=False)