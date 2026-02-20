import streamlit as st
import pandas as pd

from services.analytics_service import get_student_learning_status
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
    st.subheader("✅ 오늘 할 일 (MVP)")

    try:
        reviews = get_today_reviews(student_id)
        review_count = len(reviews)
    except Exception as e:
        show_error("복습 큐 로드 실패", e, context="get_today_reviews", show_trace=False)
        reviews = []
        review_count = 0

    hw_open = _count_open_homework(supabase, student_id)
    prac_recent = _count_recent_practice(supabase, student_id, limit=20)

    with st.container(border=True):
        st.checkbox(f"복습하기 (오늘 {review_count}개)", value=False, disabled=True)
        st.checkbox(f"숙제 제출 (미제출 {hw_open}개)", value=False, disabled=True)
        st.checkbox(f"연습 풀이 (최근 {prac_recent}건)", value=False, disabled=True)
        st.caption("※ 체크는 가이드용(자동 완료 처리 X)")

    st.divider()

    st.subheader("📊 내 학습 현황")
    try:
        status_data = get_student_learning_status(student_id)
    except Exception as e:
        show_error("학습 현황 로드 실패", e, context="get_student_learning_status", show_trace=False)
        status_data = {"review_count": 0, "subject_counts": {}}

    st.info(f"🚨 오늘의 복습: **{status_data.get('review_count', 0)}개**")

    subject_counts = status_data.get("subject_counts")
    if subject_counts:
        st.write("📈 **과목별 질문 비율**")
        chart_data = pd.DataFrame(list(subject_counts.items()), columns=["과목", "질문수"]).set_index("과목")
        st.bar_chart(chart_data)

    st.write("---")
    st.subheader("🎯 오늘의 복습 큐")
    if not reviews:
        st.caption("오늘은 복습 항목이 없어요.")
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