# ui/student/console.py
import streamlit as st

import config
from ui.ui_common import get_role_state
from ui.ui_errors import show_error

from ui.student_dashboard import render_student_dashboard
from ui.student_dashboard.focus_tracker_component import render_focus_tracker
from ui.student_homework import render_student_homework
from ui.student_wrongnote import render_student_wrongnote
from ui.student_history import render_student_history
from ui.layout import render_top_bar_with_tabs


def _safe_call(fn, *args, **kwargs):
    """
    student 탭 함수들의 시그니처가 제각각이어도 깨지지 않게 호출.
    1) kwargs 포함 호출
    2) TypeError면 kwargs 제거 후 재시도
    """
    try:
        return fn(*args, **kwargs)
    except TypeError:
        return fn(*args)


def _ensure_student_state_defaults(state: dict):
    # 채팅 메시지
    if "messages" not in state:
        if isinstance(st.session_state.get("messages"), list):
            state["messages"] = st.session_state.get("messages", [])
        else:
            state["messages"] = []

    # 최소 안전 키들
    state.setdefault("active_tab", "dashboard")
    state.setdefault("graded_items", [])
    state.setdefault("pending_save", None)
    state.setdefault("upload_rotation", {})  # {upload_key: degrees}

    # 과거 코드 호환
    if "messages" not in st.session_state or not isinstance(st.session_state.get("messages"), list):
        st.session_state["messages"] = state["messages"]


def _make_st_image_helper():
    """
    st_image_fullwidth 처럼 '함수'로 전달할 헬퍼.
    - Streamlit 버전에 따라 use_container_width / use_column_width 호환 처리
    - st.session_state["st_image_fullwidth"] 토글에 따라 동작
    """
    def _st_image(img, caption=None):
        wide = bool(st.session_state.get("st_image_fullwidth", True))
        try:
            st.image(img, caption=caption, use_container_width=wide)
        except TypeError:
            st.image(img, caption=caption, use_column_width=wide)

    return _st_image


def render_student_console(supabase, user):
    student_id = (user or {}).get("id")
    student_handle = (user or {}).get("handle") or "student"

    state = get_role_state("student", student_id)
    _ensure_student_state_defaults(state)

    if "dev_mode" not in st.session_state:
        st.session_state["dev_mode"] = False
    if "st_image_fullwidth" not in st.session_state:
        st.session_state["st_image_fullwidth"] = True
    with st.sidebar:
        with st.expander("설정", expanded=False):
            st.toggle("개발 모드", key="dev_mode")
            st.toggle("이미지 크게 보기", key="st_image_fullwidth")

    # 상단 한 줄: 학습(메인) | 숙제·오답·기록(서브) — 오프라인 보조 본질에 맞게 학습이 메인
    tab_labels = ["학습", "숙제·오답·기록"]
    selected_label = render_top_bar_with_tabs("학생", student_handle, tab_labels, key="student_main_tab")
    state["active_tab"] = "dashboard" if selected_label == "학습" else "sub"

    st_image_fullwidth = _make_st_image_helper()

    try:
        supabase_url = config.get_supabase_url()
        anon_key = config.get_supabase_anon_key()
        if supabase_url and anon_key and student_id:
            render_focus_tracker(str(student_id), supabase_url, anon_key)
    except Exception:
        pass

    if state["active_tab"] == "dashboard":
        try:
            _safe_call(
                render_student_dashboard,
                supabase,
                user,
                student_id,
                state,
                st_image_fullwidth=st_image_fullwidth,
            )
        except Exception as e:
            show_error("대시보드 로드 실패", e, context="render_student_dashboard", show_trace=bool(st.session_state.get("dev_mode", False)))
    else:
        # 숙제·오답·기록: 서브 메뉴에서 선택
        sub_label = st.radio("", options=["숙제", "오답노트", "기록"], horizontal=True, key="student_sub_tab", label_visibility="collapsed")
        if sub_label == "숙제":
            try:
                _safe_call(render_student_homework, supabase, user, student_id, state, st_image_fullwidth=st_image_fullwidth)
            except Exception as e:
                show_error("내 숙제 로드 실패", e, context="render_student_homework", show_trace=bool(st.session_state.get("dev_mode", False)))
        elif sub_label == "오답노트":
            try:
                _safe_call(render_student_wrongnote, supabase, user, student_id, state, st_image_fullwidth=st_image_fullwidth)
            except Exception as e:
                show_error("오답노트 로드 실패", e, context="render_student_wrongnote", show_trace=bool(st.session_state.get("dev_mode", False)))
        else:
            try:
                _safe_call(render_student_history, supabase, user, student_id, state, st_image_fullwidth=st_image_fullwidth)
            except Exception as e:
                show_error("기록 로드 실패", e, context="render_student_history", show_trace=bool(st.session_state.get("dev_mode", False)))