import streamlit as st
from typing import List, Optional


def _avatar_circle(handle: str | None) -> None:
    name = (handle or "").strip() or "User"
    initials = name[:2]
    st.markdown(
        f"""
        <div style="
            width:28px;height:28px;border-radius:999px;
            background:linear-gradient(135deg,#2563eb,#38bdf8);
            display:flex;align-items:center;justify-content:center;
            color:white;font-size:12px;font-weight:600;
        ">
            {initials}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_app_header(role_label: str, user_handle: str | None = "") -> None:
    """상단 공통 헤더: 로고 + 역할 (탭 없을 때)."""
    with st.container():
        left, right = st.columns([6, 1])
        with left:
            st.markdown(
                f"<span style='font-size:18px;font-weight:600;'>StudyT2C</span>"
                f" <span style='font-size:12px;color:#64748b;'>· {role_label}</span>",
                unsafe_allow_html=True,
            )
        with right:
            _avatar_circle(user_handle)


def render_top_bar_with_tabs(
    role_label: str,
    user_handle: str | None,
    tab_labels: List[str],
    key: str = "main_tab",
) -> str:
    """
    상단 한 줄: 로고 + 역할 | 탭(브라우저 탭 느낌) | 아바타.
    탭이 메인으로 보이게, 나머지는 작게.
    반환: 선택된 탭 라벨.
    """
    with st.container():
        col_logo, col_tabs, col_avatar = st.columns([1, 3, 1])
        with col_logo:
            st.markdown(
                f"<span style='font-size:16px;font-weight:600;'>StudyT2C</span>"
                f" <span style='font-size:11px;color:#64748b;'>· {role_label}</span>",
                unsafe_allow_html=True,
            )
        with col_tabs:
            selected = st.radio(
                "탭",
                options=tab_labels,
                horizontal=True,
                key=key,
                label_visibility="collapsed",
            )
        with col_avatar:
            _avatar_circle(user_handle)
    return selected


def page_card():
    """메인 콘텐츠 감싸기 (테두리 없이 여백만 — 내용 위주)."""
    return st.container(border=False)

