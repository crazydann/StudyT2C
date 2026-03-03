# ui/teacher/student_detail.py
import streamlit as st

from ui.ui_errors import show_error
from shared_summary import render_shared_summary

from ui.teacher.consult_tab import render_consult_tab
from ui.teacher.homework_tab import render_homework_tab
from ui.teacher.ai_report_tab import render_teacher_ai_report_tab


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

    top = st.columns([1, 3, 1])
    with top[0]:
        if st.button("🔙 목록으로", key="t_back"):
            state["selected_student"] = None
            st.rerun()
    with top[1]:
        st.markdown(f"## 🎓 {student_handle} (학생 상세)")
    with top[2]:
        st.caption(" ")

    st.divider()

    t1, t2, t3, t4 = st.tabs(["🧾 상담 리포트", "📦 숙제 제출", "📌 Shared Summary", "🧠 AI 분석"])
    with t1:
        render_consult_tab(supabase, teacher_id, str(student_id))
    with t2:
        render_homework_tab(supabase, str(student_id))
    with t3:
        try:
            render_shared_summary(supabase, str(student_id), student_handle, "teacher", teacher_id)
        except Exception as e:
            show_error("Shared Summary 로드 실패", e, context="render_shared_summary", show_trace=False)
    with t4:
        render_teacher_ai_report_tab(str(student_id))