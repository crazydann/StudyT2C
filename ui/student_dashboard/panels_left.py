import streamlit as st
import pandas as pd

from services.analytics_service import (
    get_student_learning_status,
    get_student_ai_learning_progress,
    get_subject_achievement,
    get_subject_weak_concepts,
    get_subject_mastery_levels,
    get_today_goal_progress,
    get_streak_days,
)
from services.review_service import get_today_reviews, record_review_attempt
from ui.ui_errors import show_error


def _count_open_homework(supabase, student_id: str) -> int:
    try:
        assigns = (
            supabase.table("homework_assignments")
            .select("id")
            .eq("student_user_id", student_id)
            .execute()
            .data
            or []
        )
        if not assigns:
            return 0

        open_cnt = 0
        for a in assigns:
            sub = (
                supabase.table("homework_submissions")
                .select("id")
                .eq("assignment_id", a["id"])
                .limit(1)
                .execute()
                .data
            )
            if not sub:
                open_cnt += 1
        return open_cnt
    except Exception:
        return 0


def _count_recent_practice(supabase, student_id: str, limit: int = 20) -> int:
    try:
        rows = (
            supabase.table("practice_items")
            .select("id, solved_at")
            .eq("student_user_id", student_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
        return len([r for r in rows if r.get("solved_at")])
    except Exception:
        return 0


def render_left_panel(supabase, student_id: str):
    # 오늘 목표 + 연속 학습
    try:
        goal = get_today_goal_progress(student_id)
        streak = get_streak_days(student_id)
    except Exception:
        goal = {"grading_count": 0, "chat_count": 0, "target_grading": 1, "target_chat": 5}
        streak = 0

    with st.container(border=True):
        g_done = goal.get("grading_count", 0)
        g_tgt = goal.get("target_grading", 1)
        c_done = goal.get("chat_count", 0)
        c_tgt = goal.get("target_chat", 5)
        goal_done = (g_done >= g_tgt) and (c_done >= c_tgt)
        st.markdown("**오늘 목표**")
        st.caption(f"채점 {min(g_done, g_tgt)}/{g_tgt}회 · 질문 {min(c_done, c_tgt)}/{c_tgt}개")
        if goal_done:
            st.success("오늘 목표 달성")
        if streak > 0:
            st.caption(f"🔥 **{streak}일** 연속 학습")

    st.divider()

    try:
        reviews = get_today_reviews(student_id)
        review_count = len(reviews)
    except Exception as e:
        show_error("복습 큐 로드 실패", e, context="get_today_reviews", show_trace=False)
        reviews = []
        review_count = 0

    try:
        status_data = get_student_learning_status(student_id)
    except Exception as e:
        show_error("학습 현황 로드 실패", e, context="get_student_learning_status", show_trace=False)
        status_data = {"review_count": 0, "subject_counts": {}}

    st.caption(f"오늘 복습 **{status_data.get('review_count', 0)}**개")

    with st.expander("상세 통계", expanded=False):
        try:
            progress = get_student_ai_learning_progress(student_id)
            chat = progress.get("chat") or {}
            review_q = progress.get("review_quiz") or {}
            grading = progress.get("vision_grading") or {}
            if any([chat.get("recent") or chat.get("prev"), review_q.get("recent", {}).get("total"), grading.get("recent", {}).get("total")]):
                c1, c2, c3 = st.columns(3)
                with c1:
                    st.metric("튜터 질문", f"{chat.get('recent', 0)}회", f"{chat.get('delta', 0):+d}" if chat.get("delta") else "—")
                with c2:
                    pct = review_q.get("recent", {}).get("accuracy_pct") or 0
                    st.metric("복습 퀴즈", f"{pct}%", f"{review_q.get('delta_accuracy_pct') or 0:+.1f}%" if review_q.get("delta_accuracy_pct") else "—")
                with c3:
                    pct = grading.get("recent", {}).get("accuracy_pct") or 0
                    st.metric("채점", f"{pct}%", f"{grading.get('delta_accuracy_pct') or 0:+.1f}%" if grading.get("delta_accuracy_pct") else "—")
        except Exception:
            pass
        subject_counts = status_data.get("subject_counts")
        if subject_counts:
            chart_data = pd.DataFrame(list(subject_counts.items()), columns=["과목", "질문수"]).set_index("과목")
            st.bar_chart(chart_data)
        try:
            ach = get_subject_achievement(student_id, lookback_days=30)
            subs = ach.get("subjects", []) or []
            if subs:
                for s in subs:
                    st.caption(f"**{s.get('label')}**: {int(s.get('score') or 0)}점")
        except Exception:
            pass
        try:
            mastery = get_subject_mastery_levels(student_id, lookback_days=30)
            for s in mastery.get("subject_levels") or []:
                if s.get("level") == "none":
                    continue
                level_ko = "마스터" if s.get("level") == "mastered" else "연습"
                st.caption(f"**{s.get('label')}**: {level_ko}")
        except Exception:
            pass

    st.divider()
    st.subheader("AI 취약점")
    expand_weak = st.button("취약점 보기", key=f"ai_weak_btn_{student_id}", use_container_width=True)
    key_open = f"ai_weak_open_{student_id}"
    if expand_weak:
        st.session_state[key_open] = True
    if st.session_state.get(key_open, False):
        try:
            weak_data = get_subject_weak_concepts(student_id, lookback_days=30)
            weak_subs = weak_data.get("subjects", {}) or {}
            ach_data = get_subject_achievement(student_id, lookback_days=30)
            ach_subs = ach_data.get("subjects", []) or []
        except Exception as e:
            show_error("취약점 분석 로드 실패", e, context="get_subject_weak_concepts", show_trace=False)
            weak_subs = {}
            ach_subs = []

        if ach_subs:
            chart_df = pd.DataFrame(ach_subs)[["label", "score"]].set_index("label")
            st.bar_chart(chart_df)
        if weak_subs:
            st.caption("과목별 취약 개념")
            for label, concepts in weak_subs.items():
                if concepts:
                    pills = " · ".join([f"`{c}`" for c in concepts[:5]])
                    st.markdown(f"**{label}**: {pills}")
        if st.button("접기", key=f"ai_weak_close_{student_id}", use_container_width=True):
            st.session_state[key_open] = False
            st.rerun()

    st.divider()
    st.subheader("오늘의 복습")
    if not reviews:
        st.caption("복습할 항목이 없습니다.")
        if st.button("취약점 보기", key=f"ai_weak_btn_zero_{student_id}", use_container_width=True):
            st.session_state[f"ai_weak_open_{student_id}"] = True
            st.rerun()
        return

    for item in reviews:
        title = (item.get("extracted_question_text", "문제") or "")[:25]
        with st.expander(f"복습: {title}..."):
            st.write(item.get("explanation_summary"))
            c1, c2 = st.columns(2)
            if c1.button("✅ 맞춤", key=f"r_o_{student_id}_{item['id']}"):
                try:
                    record_review_attempt(student_id, item["id"], True)
                    st.rerun()
                except Exception as e:
                    show_error("복습 결과 저장 실패", e, context="record_review_attempt(True)")
            if c2.button("❌ 또 틀림", key=f"r_x_{student_id}_{item['id']}"):
                try:
                    record_review_attempt(student_id, item["id"], False)
                    st.rerun()
                except Exception as e:
                    show_error("복습 결과 저장 실패", e, context="record_review_attempt(False)")