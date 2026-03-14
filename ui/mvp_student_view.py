# ui/mvp_student_view.py
"""
로그인학생 화면: 첨부 UI 스타일 — 헤더(타이머·과목·쉬는시간), 좌(질의 개념 복습·문제 만들기·지난 문제들·추천 개념), 중(AI 튜터), 우(문제 채점기·지난 채점 이력).
"""
import time
import streamlit as st

import random

import config
from ui.student_dashboard.panels_center import render_center_panel
from ui.student_dashboard.panels_grading import render_grading_panel
from ui.student_dashboard.focus_tracker_component import render_focus_tracker
from services.analytics_service import get_study_chat_history
from services.llm_service import generate_quiz_from_qa, recommend_concepts_from_chat, explain_concept
from services.concept_review_service import save_attempt, save_quiz, list_quizzes, get_quiz_by_id
from ui.quiz_weakness_ui import render_quiz_weakness_section
from ui.ui_errors import show_error
from ui.ui_common import format_ts_short
from services.db_service import list_grading_submissions, get_submission_items, list_chat_messages


def _make_image_renderer():
    def _render(img, caption=None):
        try:
            st.image(img, caption=caption, use_container_width=True)
        except TypeError:
            st.image(img, caption=caption, use_column_width=True)
    return _render


def _apply_student_layout_css():
    """로그인학생: 헤더–본문 공백 제거(크롬 포함) + 브라우저 사이즈에 따라 자동 변경."""
    st.markdown(
        """
        <style>
        /* 헤더–본문 공백 제거: 모든 상단 여백 제거 (크롬·데스크톱 동일 적용) */
        section[data-testid="stAppViewContainer"],
        section[data-testid="stAppViewContainer"] > div,
        div[data-testid="stAppViewContainer"] div.block-container {
            padding-top: 0 !important;
            max-width: 100%;
        }
        div[data-testid="stAppViewContainer"] div.block-container {
            padding-left: 1.5rem;
            padding-right: 1.5rem;
            padding-bottom: 1rem;
            min-height: 0;
        }
        div[data-testid="stAppViewContainer"] div.block-container > div {
            margin-bottom: 0 !important;
            margin-top: 0 !important;
        }
        /* 헤더 바로 아래 본문 끌어올리기 (크롬에서 남는 여백 제거) */
        div[data-testid="stAppViewContainer"] div.block-container > div:nth-child(n+2) {
            margin-top: 0 !important;
        }
        div[data-testid="stAppViewContainer"] div.block-container hr {
            margin: 0.1rem 0 !important;
        }
        div[data-testid="stAppViewContainer"] iframe[title="streamlitComponent"] {
            height: 0 !important;
            min-height: 0 !important;
            display: block !important;
        }
        section[data-testid="stSidebar"] { display: none; }
        header[data-testid="stHeader"] { background: transparent; }

        /* AI 튜터 대화창: 브라우저 크기에 따라 자동 변경 (고정 70vh 제거로 크롬 공백 원인 제거) */
        div[data-testid="stHorizontalBlock"] > div:nth-child(2) {
            min-height: 0;
        }
        div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[style*="overflow"] {
            height: min(55vh, 520px) !important;
            min-height: 280px !important;
            max-height: 75vh;
        }

        /* 태블릿: 비율 유지 */
        @media (max-width: 1024px) {
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[style*="overflow"] {
                height: min(52vh, 480px) !important;
                min-height: 260px !important;
            }
        }

        /* 휴대폰: 3열 세로 쌓기, AI 튜터 맨 위 */
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
            }
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[style*="overflow"] {
                height: min(50vh, 420px) !important;
                min-height: 240px !important;
            }
        }

        @media (max-width: 480px) {
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) div[style*="overflow"] {
                height: min(48vh, 380px) !important;
                min-height: 220px !important;
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
    # 학생은 부모가 설정한 학습 모드만 사용: status는 DB(user) 기준, 학생 화면에서 변경 불가
    effective_status = (user.get("status") or "break")
    if "study_timer_start" not in state and effective_status == "studying":
        state["study_timer_start"] = time.time()
    st.session_state["mvp_student_state"] = state

    _apply_student_layout_css()

    # 1. 헤더: 왼쪽(학생 이름·집중 상태) | 가운데(타이머) | 오른쪽(과목·로그아웃)
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
        r1, r2 = st.columns([2, 1])
        with r1:
            st.selectbox(
                "과목",
                options=["수학", "국어", "영어", "과학", "사회"],
                index=0,
                key="mvp_subject",
                label_visibility="collapsed",
            )
            st.caption("학습/쉬는시간 모드는 학부모 화면에서만 변경할 수 있어요.")
        with r2:
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
        # 추천 공부 개념: 얇은 띠 배너 (AI 튜터 바로 위)
        _render_recommended_concepts_banner(str(student_id), state)
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


@st.dialog("다시 풀기")
def _dialog_retry_quiz(student_id: str, quiz_id: str) -> None:
    """지난 문제 다시 풀기 팝업."""
    quiz = get_quiz_by_id(quiz_id) if quiz_id else None
    if not quiz:
        st.warning("해당 문제를 찾을 수 없어요.")
        if st.button("닫기", key="close_retry_quiz"):
            st.session_state.pop("mvp_retry_quiz_id", None)
            st.rerun()
        return
    options = quiz.get("options") or []
    if not isinstance(options, list):
        options = []
    correct_index = int(quiz.get("correct_index", 0))
    st.markdown("**다시 풀기**")
    st.write(quiz.get("quiz_question") or "(문제 없음)")
    choice = st.radio("보기", options=range(len(options)), format_func=lambda i: options[i] if i < len(options) else "", key="retry_quiz_radio", label_visibility="collapsed")
    if st.button("제출", key="retry_quiz_submit"):
        save_attempt(
            student_id,
            quiz.get("source_question") or "",
            quiz.get("source_answer") or "",
            quiz.get("quiz_question") or "",
            correct_index,
            choice,
        )
        if choice == correct_index:
            st.success("✅ 정답입니다.")
        else:
            st.error("❌ 오답입니다.")
        st.caption(f"정답: {options[correct_index]}")
    if st.button("닫기", key="close_retry_quiz"):
        st.session_state.pop("mvp_retry_quiz_id", None)
        st.rerun()


@st.dialog("개념 설명")
def _dialog_concept_explanation(concept_name: str) -> None:
    """추천 개념 설명 팝업."""
    st.markdown(f"**📚 {concept_name}**")
    with st.spinner("설명 불러오는 중..."):
        explanation = explain_concept(concept_name)
    st.write(explanation)
    if st.button("닫기", key="close_concept_popup"):
        st.session_state.pop("mvp_concept_popup", None)
        st.rerun()


def _get_recommended_concepts(student_id: str) -> list:
    """최근 채팅 기반 추천 공부 개념 목록."""
    try:
        chat_rows = list_chat_messages(student_id, limit=25)
        chat_items = []
        for r in chat_rows:
            if (r.get("role") or "").strip().lower() != "user":
                continue
            content = r.get("content") or ""
            meta = r.get("meta") or {}
            answer = meta.get("answer") or ""
            if content or answer:
                chat_items.append({"question": content, "answer": answer})
        return recommend_concepts_from_chat(chat_items, max_concepts=6) if chat_items else []
    except Exception:
        return []


def _render_recommended_concepts_banner(student_id: str, state: dict) -> None:
    """AI 튜터 위 얇은 띠 배너: 추천 공부 개념 (클릭 시 개념 설명 팝업)."""
    concepts = _get_recommended_concepts(student_id)
    if not concepts:
        st.markdown(
            '<div style="font-size:0.75rem;color:#64748b;padding:6px 10px;border-radius:6px;'
            'background:#f8fafc;border:1px solid #e2e8f0;margin-bottom:6px;">'
            "💡 <strong>추천 공부 개념</strong> — AI 튜터와 대화하면 여기에 추천 개념이 나타나요.</div>",
            unsafe_allow_html=True,
        )
    else:
        n = min(6, len(concepts))
        with st.container(border=True):
            cols = st.columns([1] * (n + 1))
            with cols[0]:
                st.caption("💡 **추천**")
            for i, c in enumerate(concepts[:n]):
                with cols[i + 1]:
                    label = (c[:8] + "…") if len(c) > 8 else c
                    if st.button(label, key=f"mvp_banner_c_{student_id}_{i}", use_container_width=True):
                        st.session_state["mvp_concept_popup"] = c
                        st.rerun()
    if st.session_state.get("mvp_concept_popup"):
        try:
            _dialog_concept_explanation(st.session_state["mvp_concept_popup"])
        except TypeError:
            st.session_state.pop("mvp_concept_popup", None)


def _render_left_sidebar(student_id: str, student_handle: str, state: dict) -> None:
    """좌측: 질의 개념 복습·문제 만들기·지난 문제들·추천 공부 개념 (첨부 UI)."""
    st.markdown("**💡 질의 개념 복습**")
    st.caption("AI 튜터에서 나눈 질문을 바탕으로 유사 문제를 풀어 보세요.")
    st.markdown("**✨ 문제 만들기**")
    _render_quiz_from_qa(student_id, student_handle)

    st.markdown("---")
    st.markdown("**🕘 지난 문제들**")
    try:
        past_quizzes = list_quizzes(student_id, limit=20)
    except Exception:
        past_quizzes = []
    if not past_quizzes:
        st.caption("아직 만든 문제가 없어요. 문제 만들기를 눌러 보세요.")
    else:
        for q in past_quizzes:
            label = (q.get("quiz_question") or "")[:42]
            if len(q.get("quiz_question") or "") > 42:
                label += "…"
            if st.button(label, key=f"retry_quiz_{q.get('id')}", use_container_width=True):
                st.session_state["mvp_retry_quiz_id"] = str(q.get("id"))
                st.rerun()
    if st.session_state.get("mvp_retry_quiz_id"):
        try:
            _dialog_retry_quiz(student_id, st.session_state["mvp_retry_quiz_id"])
        except TypeError:
            st.session_state.pop("mvp_retry_quiz_id", None)

    st.caption("💡 추천 공부 개념은 AI 튜터 창 위 띠에서 확인하세요.")


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
        with st.spinner("새 문제를 만드는 중..."):
            try:
                history = get_study_chat_history(student_id, lookback_days=7, limit=15)
                items = history.get("items") or []
                if not items:
                    st.warning("최근 AI 튜터에서 나눈 **공부 관련 질문**이 없어요. 먼저 AI 튜터로 질문해 보세요.")
                else:
                    item = random.choice(items)
                    quiz = generate_quiz_from_qa(
                        item.get("question") or "",
                        item.get("answer") or "",
                    )
                    if quiz:
                        source_q = item.get("question") or ""
                        source_a = item.get("answer") or ""
                        quiz_id = save_quiz(
                            student_id,
                            source_q,
                            source_a,
                            quiz.get("question") or "",
                            quiz.get("options") or [],
                            int(quiz.get("correct_index", 0)),
                        )
                        st.session_state[key_data] = {
                            **quiz,
                            "source_question": source_q,
                            "source_answer": source_a,
                            "_quiz_id": quiz_id,
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
