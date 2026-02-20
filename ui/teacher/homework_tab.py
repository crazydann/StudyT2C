# ui/teacher/homework_tab.py
import streamlit as st

from ui.teacher.data_loaders import fetch_homework_assignments, fetch_latest_homework_submission
from ui.components.file_preview import render_file_preview


def render_homework_tab(supabase, student_id: str):
    st.subheader("📦 숙제 제출/미리보기")

    assigns = fetch_homework_assignments(supabase, student_id, limit=30)
    if not assigns:
        st.caption("숙제 배정이 없습니다.")
        return

    for a in assigns:
        aid = a.get("id")
        title = a.get("title") or "숙제"
        with st.expander(f"{title}", expanded=False):
            if a.get("description"):
                st.write(a.get("description"))

            if not aid:
                st.warning("assignment_id가 없습니다.")
                continue

            sub = fetch_latest_homework_submission(supabase, aid)
            if not sub:
                st.warning("미제출")
                continue

            st.success("제출됨 ✅")
            render_file_preview(supabase, sub.get("storage_path") or "", key_prefix=f"t_hwprev_{aid}")