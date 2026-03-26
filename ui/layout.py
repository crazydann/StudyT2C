import streamlit as st
from typing import List, Optional

from ui.service_intro_dialog import render_service_intro_button_inline


def _avatar_circle(handle: str | None) -> None:
    name = (handle or "").strip() or "User"
    initials = name[:2].upper()
    # 이름 기반 색상 (일관성 있게)
    colors = [
        ("2563eb", "dbeafe"),
        ("7c3aed", "ede9fe"),
        ("db2777", "fce7f3"),
        ("d97706", "fef3c7"),
        ("059669", "d1fae5"),
    ]
    idx = sum(ord(c) for c in name) % len(colors)
    fg, bg = colors[idx]
    st.markdown(
        f"""
        <div style="
            width:34px; height:34px; border-radius:999px;
            background:#{bg};
            border: 2px solid #{fg}33;
            display:flex; align-items:center; justify-content:center;
            color:#{fg}; font-size:12px; font-weight:700;
            letter-spacing:-0.02em;
        ">
            {initials}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_app_header(role_label: str, user_handle: str | None = "") -> None:
    """상단 공통 헤더: 로고 + 역할 + 아바타."""
    st.markdown(
        """
        <style>
        .app-header-bar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 0 10px;
            border-bottom: 1px solid #f1f5f9;
            margin-bottom: 12px;
        }
        .app-header-logo {
            font-size: 1.1rem;
            font-weight: 800;
            color: #2563eb;
            letter-spacing: -0.04em;
        }
        .app-header-role {
            font-size: 0.75rem;
            color: #94a3b8;
            margin-left: 8px;
            font-weight: 500;
        }
        .app-header-sub {
            font-size: 0.72rem;
            color: #cbd5e1;
            margin-left: 6px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container():
        left, right = st.columns([6, 1])
        with left:
            st.markdown(
                f"<span class='app-header-logo'>StudyT2C</span>"
                f"<span class='app-header-sub'>오프라인 수업 개인화 보조</span>"
                f"<span class='app-header-role'>· {role_label}</span>",
                unsafe_allow_html=True,
            )
            if not st.session_state.get("_admin_flow"):
                render_service_intro_button_inline()
        with right:
            _avatar_circle(user_handle)
    st.markdown("<div style='height:2px'></div>", unsafe_allow_html=True)


def render_top_bar_with_tabs(
    role_label: str,
    user_handle: str | None,
    tab_labels: List[str],
    key: str = "main_tab",
) -> str:
    """
    상단 한 줄: 로고 + 역할 | 탭(브라우저 탭 느낌) | 아바타.
    반환: 선택된 탭 라벨.
    """
    st.markdown(
        """
        <style>
        .top-bar-wrap {
            border-bottom: 2px solid #f1f5f9;
            margin-bottom: 10px;
            padding-bottom: 2px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    with st.container():
        col_logo, col_tabs, col_avatar = st.columns([1, 3, 0.7])
        with col_logo:
            st.markdown(
                f"<span style='font-size:1rem;font-weight:800;color:#2563eb;letter-spacing:-0.04em;'>StudyT2C</span>"
                f"<br><span style='font-size:0.68rem;color:#94a3b8;'>{role_label}</span>",
                unsafe_allow_html=True,
            )
            if not st.session_state.get("_admin_flow"):
                render_service_intro_button_inline()
        with col_tabs:
            selected = st.radio(
                "탭",
                options=tab_labels,
                horizontal=True,
                key=key,
                label_visibility="collapsed",
            )
        with col_avatar:
            st.markdown("<div style='padding-top:4px;'>", unsafe_allow_html=True)
            _avatar_circle(user_handle)
            st.markdown("</div>", unsafe_allow_html=True)
    return selected


def page_card():
    """메인 콘텐츠 감싸기 (테두리 없이 여백만)."""
    return st.container(border=False)
