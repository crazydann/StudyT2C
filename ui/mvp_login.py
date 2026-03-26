# ui/mvp_login.py
"""
studyt2c.streamlit.app 전용: 로그인 화면 (id/pwd).
로그인 성공 시 session_state.mvp_user 에 user dict 저장.
"""
import streamlit as st

from services.mvp_auth import verify_login, ensure_mvp_students


def _apply_login_css():
    st.markdown(
        """
        <style>
        /* 로그인 페이지 전체 배경 */
        div.block-container {
            max-width: 100% !important;
            padding-top: 0 !important;
        }
        section[data-testid="stAppViewContainer"] > div:first-child {
            background: linear-gradient(160deg, #eef2ff 0%, #f8fafc 50%, #eff6ff 100%);
            min-height: 100vh;
        }
        /* 로그인 카드 안 border 컨테이너 */
        .login-card div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 16px !important;
            border: 1px solid #dde5f0 !important;
            box-shadow: 0 8px 32px rgba(37, 99, 235, 0.08), 0 1px 4px rgba(15,23,42,0.06) !important;
            padding: 1.5rem 0 !important;
            background: #ffffff;
        }
        /* 로그인 버튼 크게 */
        .login-card .stButton > button[kind="primary"] {
            height: 48px !important;
            font-size: 1rem !important;
            border-radius: 12px !important;
            letter-spacing: -0.01em;
        }
        /* input 크게 */
        .login-card .stTextInput > div > div > input {
            height: 48px !important;
            font-size: 1rem !important;
            border-radius: 12px !important;
            padding: 0 1rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_login_page() -> bool:
    """
    로그인 폼 렌더링. 성공 시 True 반환하고 session_state.mvp_user 설정.
    실패/미제출 시 False.
    """
    ensure_mvp_students()
    _apply_login_css()

    # 수직 여백
    st.markdown("<div style='height:6vh'></div>", unsafe_allow_html=True)

    # 가운데 정렬: 빈 열 | 폼 | 빈 열
    _, col, _ = st.columns([1, 1.1, 1])

    with col:
        # 로고 / 브랜딩
        st.markdown(
            """
            <div style="text-align:center; margin-bottom:1.8rem;">
                <div style="
                    display:inline-flex; align-items:center; justify-content:center;
                    width:56px; height:56px; border-radius:16px;
                    background:linear-gradient(135deg,#2563eb,#38bdf8);
                    box-shadow:0 4px 16px rgba(37,99,235,0.3);
                    margin-bottom:14px;
                ">
                    <span style="font-size:1.6rem;">📚</span>
                </div>
                <div style="font-size:1.75rem; font-weight:800; color:#1e293b; letter-spacing:-0.04em; line-height:1.1;">
                    StudyT2C
                </div>
                <div style="font-size:0.88rem; color:#64748b; margin-top:6px; font-weight:500;">
                    오프라인 수업 개인화 보조 서비스
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # 로그인 카드
        st.markdown('<div class="login-card">', unsafe_allow_html=True)
        with st.container(border=True):
            st.markdown(
                "<div style='font-size:1.1rem;font-weight:700;color:#1e293b;margin-bottom:0.2rem;'>로그인</div>"
                "<div style='font-size:0.82rem;color:#94a3b8;margin-bottom:1rem;'>계정 정보를 입력하세요</div>",
                unsafe_allow_html=True,
            )

            login_id = st.text_input(
                "아이디",
                key="mvp_login_id",
                placeholder="아이디",
                label_visibility="collapsed",
            )
            password = st.text_input(
                "비밀번호",
                type="password",
                key="mvp_login_pwd",
                placeholder="비밀번호",
                label_visibility="collapsed",
            )

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

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

            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)

            with st.expander("비밀번호를 잊으셨나요?", expanded=False):
                st.caption("재설정이 필요하시면 로그인 후 우측 상단 **문의하기**로 연락 주세요.")

        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown(
            "<div style='text-align:center;margin-top:1.2rem;font-size:0.75rem;color:#94a3b8;'>"
            "관리자: <code>?app=admin</code> 또는 <code>admin / admin</code>"
            "</div>",
            unsafe_allow_html=True,
        )

    return False
