# ui/teacher/student_list.py
import streamlit as st


def render_student_list(state, student_ids, handle_map):
    """
    학생 선택: 드롭다운 + 현재 선택 강조 (MVP·투자자 데모용 정리).
    학생을 선택하고 [상세 보기]를 눌러야 상세로 이동.
    """
    if not student_ids:
        st.info("연결된 학생이 없습니다.")
        st.caption("👉 관리자(admin) 화면에서 데모 데이터를 생성하거나, DB에 학생·선생 연결을 추가하면 여기에 표시됩니다.")
        return

    options = ["(선택 안 함)"] + [str(sid) for sid in student_ids]

    def _label(sid: str) -> str:
        if sid == "(선택 안 함)":
            return "— 학생 선택 —"
        return handle_map.get(sid) or sid

    current = state.get("selected_student")
    current_id = None
    if isinstance(current, dict):
        current_id = current.get("id")
    else:
        current_id = current

    default_idx = 0
    if current_id and str(current_id) in options:
        default_idx = options.index(str(current_id))

    # 현재 선택된 학생 강조
    if current_id and str(current_id) in options:
        st.markdown(f"**선택된 학생** · {_label(str(current_id))}")
        st.caption("아래에서 변경하거나 [상세 보기]로 이동하세요.")
    else:
        st.caption("학생을 선택한 뒤 [상세 보기]를 누르세요.")

    picked = st.selectbox(
        "학생",
        options,
        index=default_idx,
        format_func=_label,
        key="t_student_picker",
        label_visibility="collapsed",
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("상세 보기", key="t_open_student_detail", type="primary"):
            if picked == "(선택 안 함)":
                st.warning("학생을 먼저 선택해 주세요.")
            else:
                state["selected_student"] = picked
                st.rerun()
    with c2:
        if st.button("선택 해제", key="t_clear_student_selection"):
            state["selected_student"] = None
            st.rerun()
