import streamlit as st

from services.analytics_service import get_today_todo
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

    try:
        todo = get_today_todo(student_id)
        hw_n = todo.get("homework_count", 0)
        rev_n = todo.get("review_count", 0)
        st.markdown(
            f"<div style='font-size:0.9rem;color:#475569;padding:6px 10px;border-radius:6px;"
            f"background:#f8fafc;border:1px solid #e2e8f0;margin-bottom:8px;'>"
            f"📌 <strong>오늘 할 일</strong> — 숙제 <strong>{hw_n}</strong>건 · 복습 <strong>{rev_n}</strong>문항 "
            f"<span style='color:#64748b;font-size:0.85rem;'>(숙제·복습 데이터가 다음 수업 맞춤 보강에 활용돼요)</span></div>",
            unsafe_allow_html=True,
        )
    except Exception:
        pass

    st.markdown("### 숙제·복습")
    st.caption("숙제·채점·질문을 하면 강점/취약점이 정리되어 선생님의 다음 수업 맞춤 보강에 쓰여요. 왼쪽: 목표·복습 | 가운데: AI 튜터 | 오른쪽: 채점")

    render_image = _make_image_renderer(st_image_fullwidth)

    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_left:
        render_left_panel(supabase, student_id)

    with col_center:
        render_center_panel(user, student_id, state)

    with col_right:
        render_grading_panel(user, student_id, state, render_image)