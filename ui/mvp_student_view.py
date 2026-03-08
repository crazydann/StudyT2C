# ui/mvp_student_view.py
"""
로그인학생 화면: 문제 채점기 + AI 튜터만 노출.
질의개념복습: AI 튜터 Q&A 기반 객관식 출제·채점.
"""
import streamlit as st

import config
from ui.student_dashboard.panels_center import render_center_panel
from ui.student_dashboard.panels_grading import render_grading_panel
from ui.student_dashboard.focus_tracker_component import render_focus_tracker
from services.analytics_service import get_study_chat_history
from services.llm_service import generate_quiz_from_qa
from services.concept_review_service import save_attempt
from ui.quiz_weakness_ui import render_quiz_weakness_section
from ui.ui_errors import show_error


def _make_image_renderer():
    def _render(img, caption=None):
        try:
            st.image(img, caption=caption, use_container_width=True)
        except TypeError:
            st.image(img, caption=caption, use_column_width=True)
    return _render


def render_mvp_student_view(supabase, user: dict):
    """
    로그인한 MVP 학생 전용.
    상단: 로그인 학생 이름 | 가운데: AI 튜터 대화창 | 왼쪽: 질의개념복습 | 오른쪽: 문제 채점기
    """
    student_id = (user or {}).get("id")
    student_handle = (user or {}).get("handle") or "student"

    state = st.session_state.get("mvp_student_state") or {}
    state.setdefault("messages", [])
    state.setdefault("graded_items", [])
    state.setdefault("pending_save", None)
    state.setdefault("upload_rotation", {})
    st.session_state["mvp_student_state"] = state

    # 1. 윗 부분: 로그인 학생 이름 + 로그아웃
    top_col1, top_col2 = st.columns([3, 1])
    with top_col1:
        st.markdown(f"### 👤 {student_handle}")
        st.caption("로그인학생 화면 · AI 튜터와 질의개념복습, 문제 채점기를 사용할 수 있어요.")
    with top_col2:
        st.write("")
        if st.button("로그아웃", key="mvp_logout"):
            st.session_state.pop("mvp_user", None)
            st.session_state.pop("current_user", None)
            st.rerun()

    st.divider()

    try:
        supabase_url = config.get_supabase_url()
        anon_key = config.get_supabase_anon_key()
        if supabase_url and anon_key:
            render_focus_tracker(str(student_id), supabase_url, anon_key)
    except Exception:
        pass

    # 2. 가운데 AI 튜터 / 왼쪽 질의개념복습 / 오른쪽 문제 채점기 (1 : 2 : 1 비율)
    col_left, col_center, col_right = st.columns([1, 2, 1])

    with col_left:
        st.markdown("#### 📌 질의개념복습")
        _render_quiz_from_qa(str(student_id), student_handle)
        _render_quiz_weakness_analysis(str(student_id), student_handle)

    with col_center:
        st.markdown("#### 🤖 AI 튜터")
        st.caption("질문을 입력하면 AI가 답변해 줍니다. (일반 대화처럼 이어서 대화할 수 있어요)")
        render_center_panel(user, str(student_id), state)

    with col_right:
        st.markdown("#### 📝 문제 채점기")
        render_grading_panel(user, str(student_id), state, _make_image_renderer())


def _render_quiz_from_qa(student_id: str, student_handle: str = "학생") -> None:
    """질의개념복습: 최근 AI 튜터 Q&A로 5지선다 생성 → 선택 → 맞음/틀림 표시·저장."""
    st.markdown("#### 📌 질의개념복습")
    st.caption("AI 튜터에서 나눈 질문을 바탕으로 유사 문제를 풀어 보세요.")

    key_data = "mvp_quiz_data"
    key_submitted = "mvp_quiz_submitted"
    key_choice = "mvp_quiz_user_choice"

    if st.button("질의개념복습 문제 만들기", type="secondary", key="mvp_quiz_btn"):
        st.session_state.pop(key_data, None)
        st.session_state.pop(key_submitted, None)
        st.session_state.pop(key_choice, None)
        with st.spinner("최근 질문을 불러와 문제를 만드는 중..."):
            try:
                history = get_study_chat_history(student_id, lookback_days=7, limit=10)
                items = history.get("items") or []
                if not items:
                    st.warning("최근 AI 튜터에서 나눈 **공부 관련 질문**이 없어요. 먼저 AI 튜터로 질문해 보세요.")
                else:
                    item = items[0]
                    quiz = generate_quiz_from_qa(
                        item.get("question") or "",
                        item.get("answer") or "",
                    )
                    if quiz:
                        st.session_state[key_data] = {
                            **quiz,
                            "source_question": item.get("question") or "",
                            "source_answer": item.get("answer") or "",
                        }
                        st.session_state[key_submitted] = False
                        st.session_state[key_choice] = None
                        st.rerun()
                    else:
                        st.error("문제 생성에 실패했어요. 잠시 후 다시 시도해 주세요.")
            except Exception as e:
                show_error("질의개념복습 로드 실패", e, context="get_study_chat_history/generate_quiz", show_trace=False)

    data = st.session_state.get(key_data)
    if not data:
        return

    st.markdown("**문제**")
    st.write(data.get("question") or "(문제 없음)")
    options = data.get("options") or []
    correct_index = int(data.get("correct_index", 0))
    if correct_index < 0 or correct_index >= len(options):
        correct_index = 0

    submitted = st.session_state.get(key_submitted, False)
    if not submitted:
        choice = st.radio(
            "보기",
            options=range(len(options)),
            format_func=lambda i: (options[i] if i < len(options) else ""),
            key="mvp_quiz_radio",
            label_visibility="collapsed",
        )
        if st.button("제출", key="mvp_quiz_submit"):
            st.session_state[key_submitted] = True
            st.session_state[key_choice] = choice
            # DB에 풀이 이력 저장 (취약점 분석용)
            save_attempt(
                student_id,
                data.get("source_question") or "",
                data.get("source_answer") or "",
                data.get("question") or "",
                correct_index,
                choice,
            )
            st.rerun()
    else:
        user_choice = st.session_state.get(key_choice, -1)
        if user_choice == correct_index:
            st.success("✅ **정답**입니다.")
        else:
            st.error("❌ **오답**입니다.")
        st.caption(f"정답: {options[correct_index]}")
        if st.button("다른 문제 풀기", key="mvp_quiz_again"):
            st.session_state.pop(key_data, None)
            st.session_state.pop(key_submitted, None)
            st.session_state.pop(key_choice, None)
            st.rerun()


def _render_quiz_weakness_analysis(student_id: str, student_handle: str) -> None:
    """질의개념복습 통계 + AI 취약점 분석 (공통 컴포넌트 사용)."""
    render_quiz_weakness_section(student_id, student_handle, lookback_days=90)
