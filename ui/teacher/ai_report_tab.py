import pandas as pd
import streamlit as st

from services.analytics_service import get_subject_achievement, get_offtopic_chat_summary, get_next_class_recommendation
from ui.focus_ui import render_focus_section


def render_teacher_ai_report_tab(student_id: str, student_handle: str = ""):
    try:
        rec = get_next_class_recommendation(student_id, lookback_days=30)
        with st.container(border=True):
            st.markdown("📌 **다음 수업 권고**")
            st.markdown(rec)
    except Exception:
        pass

    st.subheader("🧠 과목별 성취도 분석")

    try:
        data = get_subject_achievement(student_id, lookback_days=30)
    except Exception as e:
        st.error(f"성취도 분석을 불러오는 중 오류가 발생했습니다: {e}")
        return

    summary = data.get("summary", {}) or {}
    subjects = data.get("subjects", []) or []

    avg_score = summary.get("avg_score") or 0
    avg_cr = summary.get("avg_correct_rate")
    cr_str = f"{int(avg_cr * 100)}%" if isinstance(avg_cr, (int, float)) else "N/A"

    try:
        off = get_offtopic_chat_summary(student_id, lookback_days=7)
    except Exception:
        off = {"total": 0}
    total_off = off.get("total", 0)
    badge = "🔴 경고" if total_off >= 10 else ("🟠 주의" if total_off >= 5 else None)

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("평균 성취도", f"{avg_score}점")
    with c2:
        st.metric("평균 정답률", cr_str)
    with c3:
        m_label = "공부 외 질문(7일)"
        if badge:
            m_label = f"{badge} · {m_label}"
        st.metric(m_label, f"{total_off}건")

    st.markdown("---")

    render_focus_section(student_id, student_handle or "학생")

    st.markdown("---")

    if not subjects:
        st.caption("아직 성취도 분석에 사용할 데이터가 충분하지 않습니다.")
        return

    df = pd.DataFrame(subjects)

    st.markdown("#### 과목별 성취도 상세")
    table_df = df[["label", "score", "correct_rate", "question_count"]].copy()
    table_df["정답률(%)"] = (table_df["correct_rate"].fillna(0) * 100).round(0).astype(int)
    table_df = table_df.drop(columns=["correct_rate"]).rename(
        columns={
            "label": "과목",
            "score": "성취도 점수",
            "question_count": "질문 수(30일)",
        }
    )
    st.dataframe(table_df, use_container_width=True)

    st.markdown("#### 과목별 성취도 비교")
    chart_df = df[["label", "score"]].set_index("label")
    st.bar_chart(chart_df)

