# ui/parent/student_detail.py
import streamlit as st

from ui.ui_errors import show_error
from shared_summary import render_shared_summary
from ui.parent.consult_tab import render_consult_tab
from ui.parent.homework_tab import render_homework_tab


def render_student_detail(supabase, parent_id: str, state: dict):
    sel = state.get("selected_student") or {}
    sid = sel.get("id")
    shandle = sel.get("handle") or "student"

    if not sid:
        st.warning("자녀가 선택되지 않았습니다.")
        state["selected_student"] = None
        return

    top_bar = st.columns([1, 3, 1])
    with top_bar[0]:
        if st.button("🔙 목록으로", key="p_back"):
            state["selected_student"] = None
            st.rerun()

    with top_bar[1]:
        st.markdown(f"## 🎓 {shandle} (자녀 상세)")

    st.divider()

    t1, t2, t3 = st.tabs(["🧾 상담 리포트", "📦 숙제 제출", "📌 Shared Summary"])
    with t1:
        render_consult_tab(supabase, str(sid))
    with t2:
        render_homework_tab(supabase, str(sid))
    with t3:
        try:
            render_shared_summary(supabase, str(sid), shandle, "parent", parent_id)
        except Exception as e:
            show_error("Shared Summary 로드 실패", e, context="render_shared_summary", show_trace=False)