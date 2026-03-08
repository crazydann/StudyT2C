# ui/parent/children_list.py
import streamlit as st


def render_children_list(state: dict, children_ids, handle_map):
    st.subheader("👨‍👩‍👧‍👦 자녀 선택")

    if not children_ids:
        st.info("연결된 자녀가 없습니다.")
        return

    options = ["(선택 안 함)"] + [str(sid) for sid in children_ids]

    def _label(sid: str) -> str:
        if sid == "(선택 안 함)":
            return sid
        return handle_map.get(sid) or sid

    current = state.get("selected_student")
    current_id = None
    if isinstance(current, dict):
        current_id = current.get("id")
    elif isinstance(current, str):
        current_id = current

    default_idx = 0
    if current_id and str(current_id) in options:
        default_idx = options.index(str(current_id))

    picked = st.radio(
        "자녀 목록",
        options,
        index=default_idx,
        format_func=_label,
        key="p_child_picker",
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("자녀 보기", key="p_open_child_detail"):
            if picked == "(선택 안 함)":
                st.warning("자녀를 먼저 선택해줘.")
            else:
                state["selected_student"] = {"id": picked, "handle": _label(picked)}
                st.rerun()

    with c2:
        if st.button("🧹 선택 초기화", key="p_clear_child_selection"):
            state["selected_student"] = None
            st.rerun()