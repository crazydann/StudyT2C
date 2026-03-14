# ui/mvp_login.py
"""
studyt2c.streamlit.app 전용: 로그인 화면 (id/pwd).
로그인 성공 시 session_state.mvp_user 에 user dict 저장.
"""
import streamlit as st

from services.mvp_auth import verify_login, ensure_mvp_students


def render_login_page() -> bool:
    """
    로그인 폼 렌더링. 성공 시 True 반환하고 session_state.mvp_user 설정.
    실패/미제출 시 False.
    """
    ensure_mvp_students()

    st.markdown("## 로그인")
    login_id = st.text_input("아이디", key="mvp_login_id", placeholder="아이디")
    password = st.text_input("비밀번호", type="password", key="mvp_login_pwd", placeholder="비밀번호")

    with st.expander("비밀번호를 잊으셨나요?", expanded=False):
        st.caption("재설정이 필요하시면 로그인 후 우측 상단 **문의하기**로 연락 주세요.")

    if st.button("로그인", type="primary", use_container_width=True):
        if not (login_id and password):
            st.error("아이디와 비밀번호를 입력해 주세요.")
            return False
        # admin / admin → 계정 선택(admin) 화면으로 전환
        if login_id.strip().lower() == "admin" and password == "admin":
            st.session_state["_student_login_mode"] = False
            try:
                st.query_params["app"] = "admin"
            except Exception:
                try:
                    st.experimental_set_query_params(app="admin")
                except Exception:
                    pass
            st.rerun()
        user = verify_login(login_id, password)
        if user:
            st.session_state["mvp_user"] = user
            st.session_state["current_user"] = user
            st.rerun()
        else:
            st.error("아이디 또는 비밀번호가 올바르지 않습니다.")

    st.caption("관리자: **?app=admin** 또는 admin / admin")
    return False
