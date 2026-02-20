import streamlit as st

from ui.student_dashboard.panels_left import render_left_panel
from ui.student_dashboard.panels_center import render_center_panel
from ui.student_dashboard.panels_grading import render_grading_panel


def _make_image_renderer(st_image_fullwidth):
    if callable(st_image_fullwidth):
        return st_image_fullwidth

    wide = bool(st_image_fullwidth) if st_image_fullwidth is not None else True

    def _render(img, caption=None):
        try:
            st.image(img, caption=caption, use_container_width=wide)
        except TypeError:
            st.image(img, caption=caption, use_column_width=wide)

    return _render


def render_student_dashboard(
    supabase,
    user,
    student_id: str,
    state: dict,
    st_image_fullwidth=None,
    image_fullwidth=None,
    **kwargs,
):
    # 호환: 어떤 이름으로 오든 받기
    if st_image_fullwidth is None:
        st_image_fullwidth = image_fullwidth

    state.setdefault("messages", [])
    state.setdefault("upload_rotation", {})
    state.setdefault("graded_items", [])
    state.setdefault("pending_save", None)

    render_image = _make_image_renderer(st_image_fullwidth)

    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_left:
        render_left_panel(supabase, student_id)

    with col_center:
        render_center_panel(user, student_id, state)

    with col_right:
        render_grading_panel(user, student_id, state, render_image)