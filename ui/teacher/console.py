# ui/teacher/console.py
import streamlit as st

from ui.ui_common import get_role_state
from ui.teacher.data_loaders import fetch_teacher_student_ids, fetch_user_handles_by_ids
from ui.teacher.student_list import render_student_list
from ui.teacher.student_detail import render_student_detail
from ui.teacher.class_dashboard_tab import render_class_dashboard_tab
from services.demo_seed import seed_demo_basic, delete_demo_data
from ui.layout import render_app_header, page_card


def render_teacher_console(supabase, user):
    # 개발 모드 토글(상단에 항상 보이게)
    if "dev_mode" not in st.session_state:
        st.session_state["dev_mode"] = False
    st.toggle("🧪 개발 모드", key="dev_mode")

    teacher_id = user.get("id")
    teacher_handle = user.get("handle") or "teacher"

    render_app_header("Teacher Console", teacher_handle)

    # 메인 카드 컨테이너
    with page_card():
        st.markdown("#### 반 관리")

        # 개발 모드 전용: 데모 데이터 생성 / 삭제
        if bool(st.session_state.get("dev_mode", False)):
            c_seed, c_del = st.columns(2)
            with c_seed:
                if st.button("🧪 데모 데이터 생성", key="t_seed_demo"):
                    try:
                        info = seed_demo_basic()
                        st.success(
                            f"데모 유저 생성 완료: teacher={info['teacher']['handle']}, "
                            f"student={info['student']['handle']}, parent={info['parent']['handle']}"
                        )
                    except Exception as e:
                        st.error(f"데모 데이터 생성 실패: {e}")
            with c_del:
                if st.button("🗑️ 데모 데이터 모두 삭제", key="t_delete_demo", type="secondary"):
                    try:
                        result = delete_demo_data()
                        if result.get("ok"):
                            st.success(result.get("message", "삭제 완료."))
                            if result.get("deleted"):
                                st.caption(str(result["deleted"]))
                        else:
                            st.error(result.get("message", "삭제 실패."))
                    except Exception as e:
                        st.error(f"데모 데이터 삭제 실패: {e}")

        state = get_role_state("teacher", teacher_id)
        state.setdefault("selected_student", None)

        student_ids = fetch_teacher_student_ids(supabase, teacher_id)
        handle_map = fetch_user_handles_by_ids(supabase, student_ids)

        tab_dash, tab_students = st.tabs(["📊 반 대시보드", "👩‍🎓 학생별 상세"])

        with tab_dash:
            render_class_dashboard_tab(state, student_ids, handle_map)

        with tab_students:
            if state["selected_student"] is None:
                render_student_list(state, student_ids, handle_map)
            else:
                render_student_detail(supabase, teacher_id, state, handle_map)