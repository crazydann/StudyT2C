# ui/parent/console.py
import streamlit as st

from ui.ui_common import get_role_state
from ui.parent.data_loaders import fetch_children_ids, fetch_user_handles_by_ids
from ui.parent.children_list import render_children_list
from ui.parent.student_detail import render_student_detail


def render_parent_console(supabase, user):
    if "dev_mode" not in st.session_state:
        st.session_state["dev_mode"] = False
    with st.expander("설정", expanded=False):
        st.toggle("개발 모드", key="dev_mode")

    parent_id = user["id"]
    state = get_role_state("parent", parent_id)
    state.setdefault("selected_student", None)

    children_ids = fetch_children_ids(supabase, parent_id)
    if not children_ids:
        st.warning("연결된 자녀가 없습니다. (MVP: parent_student_links 테이블에 연결 필요)")
        return

    handle_map = fetch_user_handles_by_ids(supabase, children_ids)

    if state["selected_student"] is None:
        render_children_list(state, children_ids, handle_map)
    else:
        render_student_detail(supabase, parent_id, state)