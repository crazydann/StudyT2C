# ui/parent/student_detail.py
import streamlit as st

from ui.ui_errors import show_error
from shared_summary import render_shared_summary
from ui.parent.consult_tab import render_consult_tab
from ui.parent.homework_tab import render_homework_tab
from ui.parent.ai_report_tab import render_ai_report_tab
from ui.focus_ui import render_focus_section


def render_student_detail(supabase, parent_id: str, state: dict):
    sel = state.get("selected_student") or {}
    sid = sel.get("id")
    shandle = sel.get("handle") or "student"

    if not sid:
        st.warning("자녀가 선택되지 않았습니다.")
        state["selected_student"] = None
        return

    # 자녀 설정은 어드민 상단 '자녀 설정' 팝오버에서 표시 (사이드바 제거)

    # 상단 한 줄: 뒤로 | 자녀명
    row = st.columns([1, 4])
    with row[0]:
        if st.button("🔙 목록으로", key="p_back"):
            state["selected_student"] = None
            st.rerun()
    with row[1]:
        st.markdown(f"<span style='font-size:16px;font-weight:600;'>{shandle}</span>", unsafe_allow_html=True)

    tab_labels = ["성취도·추이", "상담", "숙제", "집중현황", "요약"]
    selected = st.radio("탭", options=tab_labels, horizontal=True, key="parent_detail_tab", label_visibility="collapsed")

    if selected == "성취도·추이":
        render_ai_report_tab(str(sid), shandle)
    elif selected == "상담":
        render_consult_tab(supabase, str(sid))
    elif selected == "숙제":
        render_homework_tab(supabase, str(sid))
    elif selected == "집중현황":
        render_focus_section(str(sid), shandle)
    else:
        try:
            render_shared_summary(supabase, str(sid), shandle, "parent", parent_id)
        except Exception as e:
            show_error("Shared Summary 로드 실패", e, context="render_shared_summary", show_trace=False)