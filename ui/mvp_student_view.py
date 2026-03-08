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


def _apply_student_layout_css():
    """로그인학생 화면: 전체 화면, AI 튜터가 가장 크게, 뷰포트 비율·반응형(태블릿/휴대폰)."""
    st.markdown(
        """
        <style>
        /* 로그인학생 전용: 전체 폭 사용, 헤더~본문 사이 여백 최소화 */
        div[data-testid="stAppViewContainer"] div.block-container {
            max-width: 100%;
            padding-left: 1.5rem;
            padding-right: 1.5rem;
            padding-top: 0.35rem;
            padding-bottom: 1rem;
            min-height: 0;
        }
        /* 헤더와 질의개념복습/AI튜터/문제채점기 사이 블록 간격 축소 */
        div[data-testid="stAppViewContainer"] div.block-container > div {
            margin-bottom: 0.2rem;
            margin-top: 0.1rem;
        }
        div[data-testid="stAppViewContainer"] div.block-container hr {
            margin: 0.35rem 0;
        }
        section[data-testid="stSidebar"] { display: none; }
        header[data-testid="stHeader"] { background: transparent; }

        /* AI 튜터 대화창이 가장 큰 비율: 가운데 열(2번째) 내 스크롤 영역을 뷰포트 비율로 */
        div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[style*="overflow"] {
            height: 65vh !important;
            min-height: 380px !important;
            max-height: 85vh;
        }
        /* 가운데 열 자체도 최소 높이 확보 */
        div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
            min-height: 70vh;
        }

        /* 태블릿 (768px ~ 1024px): AI 튜터 비율 유지 */
        @media (max-width: 1024px) {
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[style*="overflow"] {
                height: 58vh !important;
                min-height: 320px !important;
            }
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) { min-height: 65vh; }
        }

        /* 휴대폰: 3열 세로 쌓기, AI 튜터를 맨 위에 두고 가장 크게 */
        @media (max-width: 768px) {
            div[data-testid="stHorizontalBlock"] {
                flex-direction: column !important;
            }
            div[data-testid="stHorizontalBlock"] > div {
                max-width: 100% !important;
                flex: 0 0 auto !important;
            }
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
                order: -1;
                min-height: 0;
            }
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[style*="overflow"] {
                height: 55vh !important;
                min-height: 280px !important;
                max-height: 70vh;
            }
        }

        /* 매우 작은 화면 (세로 모드 등) */
        @media (max-width: 480px) {
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[style*="overflow"] {
                height: 50vh !important;
                min-height: 240px !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_mvp_student_view(supabase, user: dict):
    """
    로그인한 MVP 학생 전용.
    첨부 스케치 형태: 상단 헤더(입력창) | 좌: 질의개념복습·문제만들기 | 중: AI 튜터(스크롤+입력) | 우: 문제 채점기·취약점
    """
    student_id = (user or {}).get("id")
    student_handle = (user or {}).get("handle") or "student"

    state = st.session_state.get("mvp_student_state") or {}
    state.setdefault("messages", [])
    state.setdefault("graded_items", [])
    state.setdefault("pending_save", None)
    state.setdefault("upload_rotation", {})
    st.session_state["mvp_student_state"] = state

    _apply_student_layout_css()

    # 1. 상단: 헤더 한 줄 (StudyT2C · 학생 이름 | 로그아웃), 여백 최소
    header_left, header_right = st.columns([4, 1])
    with header_left:
        st.markdown(
            f'<div style="font-size:1rem; font-weight:600; line-height:1.4;">'
            f'<span style="color:#64748b; font-weight:500;">StudyT2C</span> · 👤 {student_handle}'
            f'</div>',
            unsafe_allow_html=True,
        )
    with header_right:
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

    # 2. 3열: 좌 | 중(AI 튜터, 가장 넓고 길게) | 우 — 브라우저 크기에 따라 CSS로 비율/반응형 적용
    col_left, col_center, col_right = st.columns([1, 5, 1])

    with col_left:
        _render_quiz_from_qa(str(student_id), student_handle)

    with col_center:
        st.markdown("#### 🤖 AI 튜터")
        render_center_panel(user, str(student_id), state)

    with col_right:
        st.markdown("#### 📝 문제 채점기")
        render_grading_panel(user, str(student_id), state, _make_image_renderer())
        st.markdown("---")
        _render_quiz_weakness_analysis(str(student_id), student_handle)


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
