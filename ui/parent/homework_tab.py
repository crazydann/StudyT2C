# ui/parent/homework_tab.py
import streamlit as st

from ui.ui_errors import show_error
from ui.components.file_preview import render_file_preview
from ui.parent.data_loaders import fetch_homework_assignments, fetch_latest_homework_submission


def render_homework_tab(supabase, student_id: str):
    st.subheader("📦 제출 확인하기")

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
            try:
                render_file_preview(supabase, sub.get("storage_path") or "", key_prefix=f"p_hwprev_{aid}")
            except Exception as e:
                show_error("파일 미리보기 실패", e, context="render_file_preview", show_trace=False)