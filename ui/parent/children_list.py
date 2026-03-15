# ui/parent/children_list.py
import streamlit as st


def render_children_list(state: dict, children_ids, handle_map):
    """자녀 선택: 드롭다운 + 현재 선택 강조 (MVP·투자자 데모용 정리)."""
    if not children_ids:
        st.info("연결된 자녀가 없습니다.")
        st.caption("👉 선생님/관리자에게 자녀 계정 연결을 요청해 주세요. 연결되면 여기서 자녀를 선택해 성취도·추이, 집중현황, 알림을 볼 수 있어요.")
        return

    options = ["(선택 안 함)"] + [str(sid) for sid in children_ids]

    def _label(sid: str) -> str:
        if sid == "(선택 안 함)":
            return "— 자녀 선택 —"
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

    # 현재 선택된 자녀 강조
    if current_id and str(current_id) in options:
        st.markdown(f"**선택된 자녀** · {_label(str(current_id))}")
        st.caption("아래에서 변경하거나 [상세 보기]로 이동하세요.")
    else:
        st.caption("자녀를 선택한 뒤 [상세 보기]를 누르세요.")

    picked = st.selectbox(
        "자녀",
        options,
        index=default_idx,
        format_func=_label,
        key="p_child_picker",
        label_visibility="collapsed",
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("상세 보기", key="p_open_child_detail", type="primary"):
            if picked == "(선택 안 함)":
                st.warning("자녀를 먼저 선택해 주세요.")
            else:
                state["selected_student"] = {"id": picked, "handle": _label(picked)}
                st.rerun()
    with c2:
        if st.button("선택 해제", key="p_clear_child_selection"):
            state["selected_student"] = None
            st.rerun()
