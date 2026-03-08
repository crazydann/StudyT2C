# ui/mvp_student_view.py
"""
로그인학생 화면: 첨부 UI 스타일 — 헤더(타이머·과목·쉬는시간), 좌(질의 개념 복습·문제 만들기·지난 문제들·추천 개념), 중(AI 튜터), 우(문제 채점기·지난 채점 이력).
"""
import time
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
from ui.ui_common import format_ts_short
from services.db_service import list_grading_submissions, get_submission_items


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
        /* 로그인학생 전용: 헤더~본문 사이 공간 완전 축소 */
        div[data-testid="stAppViewContainer"] {
            padding-top: 0 !important;
        }
        div[data-testid="stAppViewContainer"] div.block-container {
            max-width: 100%;
            padding-left: 1.5rem;
            padding-right: 1.5rem;
            padding-top: 0 !important;
            padding-bottom: 1rem;
            min-height: 0;
        }
        div[data-testid="stAppViewContainer"] div.block-container > div {
            margin-bottom: 0 !important;
            margin-top: 0 !important;
        }
        div[data-testid="stAppViewContainer"] div.block-container hr {
            margin: 0.1rem 0 !important;
        }
        /* iframe/컴포넌트로 인한 빈 칸 제거 (focus 트래커 등) */
        div[data-testid="stAppViewContainer"] iframe[title="streamlitComponent"] {
            height: 0 !important;
            min-height: 0 !important;
            display: block !important;
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
    state.setdefault("display_status", user.get("status") or "break")
    if "study_timer_start" not in state and state.get("display_status") == "studying":
        state["study_timer_start"] = time.time()
    st.session_state["mvp_student_state"] = state

    _apply_student_layout_css()

    # 1. 헤더: 왼쪽(학생 이름·집중 상태) | 가운데(타이머) | 오른쪽(과목·쉬는시간/학습시작·로그아웃)
    effective_status = state.get("display_status") or "break"
    studying = effective_status == "studying"
    header_left, header_center, header_right = st.columns([2, 1, 2])
    with header_left:
        status_label = "현재 집중 학습 중" if studying else "쉬는 시간"
        st.markdown(
            f'<div style="font-size:1.05rem; font-weight:600;">👤 {student_handle}</div>'
            f'<div style="font-size:0.8rem; color:#64748b;">{status_label}</div>',
            unsafe_allow_html=True,
        )
    with header_center:
        if studying and state.get("study_timer_start"):
            elapsed = int(time.time() - state["study_timer_start"])
            h, r = divmod(elapsed, 3600)
            m, s = divmod(r, 60)
            timer_str = f"{h:02d}:{m:02d}:{s:02d}"
        else:
            timer_str = "00:00:00"
        st.markdown(
            f'<div style="font-size:1.25rem; font-weight:700; color:#16a34a;">{timer_str}</div>',
            unsafe_allow_html=True,
        )
    with header_right:
        r1, r2 = st.columns(2)
        with r1:
            st.selectbox(
                "과목",
                options=["수학", "국어", "영어", "과학", "사회"],
                index=0,
                key="mvp_subject",
                label_visibility="collapsed",
            )
        with r2:
            if studying:
                if st.button("쉬는시간", key="mvp_break_btn", type="primary"):
                    state["display_status"] = "break"
                    st.rerun()
            else:
                if st.button("학습시작", key="mvp_study_btn", type="primary"):
                    state["display_status"] = "studying"
                    state["study_timer_start"] = time.time()
                    st.rerun()
        if st.button("로그아웃", key="mvp_logout", type="secondary"):
            st.session_state.pop("mvp_user", None)
            st.session_state.pop("current_user", None)
            st.rerun()

    effective_user = {**user, "status": effective_status}

    # 2. 3열: 좌(질의 개념 복습·문제 만들기·지난 문제들·추천 개념) | 중(AI 튜터) | 우(문제 채점기·지난 채점 이력)
    col_left, col_center, col_right = st.columns([1, 5, 1])

    with col_left:
        _render_left_sidebar(str(student_id), student_handle, state)

    with col_center:
        st.markdown("**🤖 AI 튜터**")
        render_center_panel(effective_user, str(student_id), state)

    with col_right:
        _render_right_panel(effective_user, str(student_id), state)

    try:
        supabase_url = config.get_supabase_url()
        anon_key = config.get_supabase_anon_key()
        if supabase_url and anon_key:
            render_focus_tracker(str(student_id), supabase_url, anon_key)
    except Exception:
        pass


def _render_left_sidebar(student_id: str, student_handle: str, state: dict) -> None:
    """좌측: 질의 개념 복습·문제 만들기·지난 문제들·추천 공부 개념 (첨부 UI)."""
    st.markdown("**💡 질의 개념 복습**")
    st.caption("AI 튜터에서 나눈 질문을 바탕으로 유사 문제를 풀어 보세요.")
    st.markdown("**✨ 문제 만들기**")
    _render_quiz_from_qa(student_id, student_handle)

    st.markdown("---")
    st.markdown("**🕘 지난 문제들**")
    try:
        history = get_study_chat_history(student_id, lookback_days=7, limit=5)
        items = (history.get("items") or []) if history else []
    except Exception:
        items = []
    if not items:
        st.caption("아직 질문이 없어요")
    else:
        for it in items[:5]:
            q = (it.get("question") or "")[:40]
            if len((it.get("question") or "")) > 40:
                q += "…"
            st.caption(f"· {q}")

    st.markdown("**📚 추천 공부 개념**")
    for concept in ["일차방정식 풀이", "제곱수 계산", "삼각형 성질", "비례식"]:
        st.markdown(f"- {concept}")


def _render_right_panel(user: dict, student_id: str, state: dict) -> None:
    """우측: 문제 채점기·사진 업로드·지난 채점 이력 (첨부 UI)."""
    st.markdown("**✨ 문제 채점기**")
    st.markdown(
        "풀이한 문제를 사진으로 찍어 업로드하면 AI가 채점해요!"
    )
    render_grading_panel(user, student_id, state, _make_image_renderer(), show_title=False)
    st.markdown("---")
    st.markdown("**🕘 지난 채점 이력**")
    try:
        subs = list_grading_submissions(student_id, limit=5)
    except Exception:
        subs = []
    if not subs:
        st.caption("아직 채점 이력이 없어요")
    else:
        subjects = ["수학", "국어", "영어", "과학", "사회"]
        for i, s in enumerate(subs):
            sub_id = s.get("id")
            total = wrong = 0
            if sub_id:
                try:
                    items = get_submission_items(str(sub_id), limit=300)
                    total = len(items)
                    wrong = sum(1 for it in items if it.get("is_correct") is False)
                except Exception:
                    pass
            correct = total - wrong
            pct = int(100 * correct / total) if total else 0
            label = subjects[i % len(subjects)]
            date_str = format_ts_short(s.get("uploaded_at") or s.get("created_at"))
            st.caption(f"**{label}** {correct}/{total} ({pct}%) · {date_str}")


def _render_quiz_from_qa(student_id: str, student_handle: str = "학생") -> None:
    """질의개념복습: 최근 AI 튜터 Q&A로 5지선다 생성 → 선택 → 맞음/틀림 표시·저장."""

    key_data = "mvp_quiz_data"
    key_submitted = "mvp_quiz_submitted"
    key_choice = "mvp_quiz_user_choice"

    if st.button("문제 만들기", type="secondary", key="mvp_quiz_btn"):
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
