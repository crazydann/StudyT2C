import streamlit as st


def _avatar_circle(handle: str | None) -> None:
    name = (handle or "").strip() or "User"
    initials = name[:2]
    st.markdown(
        f"""
        <div style="
            width:32px;height:32px;border-radius:999px;
            background:linear-gradient(135deg,#2563eb,#38bdf8);
            display:flex;align-items:center;justify-content:center;
            color:white;font-size:14px;font-weight:600;
        ">
            {initials}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_app_header(role_label: str, user_handle: str | None = "") -> None:
    """상단 공통 헤더: 로고 + 역할 + 문의하기 + 아바타."""
    with st.container():
        left, mid, right = st.columns([5, 3, 2])
        with left:
            st.markdown(
                f"<span style='font-size:22px;font-weight:700;'>StudyT2C</span>"
                f" <span style='font-size:14px;color:#64748b;'>· {role_label}</span>",
                unsafe_allow_html=True,
            )
        with mid:
            st.markdown(
                "<a href='mailto:?subject=StudyT2C 문의' style='font-size:13px;color:#64748b;text-decoration:none;'>문의하기</a>",
                unsafe_allow_html=True,
            )
        with right:
            _avatar_circle(user_handle)


def page_card():
    """
    메인 콘텐츠를 감싸는 카드 컨테이너 helper.
    사용 예:
        with page_card():
            ...
    """
    return st.container(border=True)

