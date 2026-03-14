# ui/teacher/student_list.py
import streamlit as st


def render_student_list(state, student_ids, handle_map):
    """
    학생 목록 화면 (자동으로 상세 진입하지 않게 설계)
    - 기본 선택값은 '선택 안 함'
    - 학생을 선택하고 '학생 보기' 버튼을 눌러야 상세로 이동
    """
    st.subheader("학생 선택")
    st.caption("👉 학생을 선택한 뒤 **학생 보기**를 누르면 AI 분석·상담·숙제·리포트를 볼 수 있어요.")

    if not student_ids:
        st.info("연결된 학생이 없습니다.")
        st.caption("👉 관리자(admin) 화면에서 데모 데이터를 생성하거나, DB에 학생·선생 연결을 추가하면 여기에 표시됩니다.")
        return

    options = ["(선택 안 함)"] + [str(sid) for sid in student_ids]

    def _label(sid: str) -> str:
        if sid == "(선택 안 함)":
            return sid
        return handle_map.get(sid) or sid

    current = state.get("selected_student")
    default_idx = 0
    if current and str(current) in options:
        default_idx = options.index(str(current))

    picked = st.radio(
        "학생 목록",
        options,
        index=default_idx,
        format_func=_label,
        key="t_student_picker",
    )

    c1, c2 = st.columns([1, 1])
    with c1:
        if st.button("학생 보기", key="t_open_student_detail"):
            if picked == "(선택 안 함)":
                st.warning("학생을 먼저 선택해줘.")
            else:
                state["selected_student"] = picked
                st.rerun()

    with c2:
        if st.button("🧹 선택 초기화", key="t_clear_student_selection"):
            state["selected_student"] = None
            st.rerun()