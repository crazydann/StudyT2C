# ui/quiz_weakness_ui.py
"""
질의개념복습 통계 + 일별 추이 + AI 취약점 분석 표시 (로그인학생·학부모 공통).
"""
import streamlit as st
import pandas as pd

from services.concept_review_service import (
    get_concept_review_stats,
    get_concept_review_wrong_items,
    get_concept_review_recent_all,
    get_concept_review_daily_stats,
)
from services.llm_service import generate_weakness_analysis_from_quiz
from ui.ui_errors import show_error


def render_quiz_weakness_section(student_id: str, student_handle: str, lookback_days: int = 90) -> None:
    """
    질의개념복습 풀이 통계(총 풀이, 정답률, 오답 수) + 최근 일별 추이 + AI 취약점 분석 문단을 렌더링.
    """
    st.markdown("#### 📊 질의개념복습 취약점 분석")
    st.caption("AI 튜터 Q&A로 만든 복습 문제 풀이 이력과, AI가 분석한 취약점입니다.")
    try:
        stats = get_concept_review_stats(student_id, lookback_days=lookback_days)
    except Exception:
        stats = {"total": 0, "correct": 0, "wrong": 0, "accuracy_pct": 0}
    if stats["total"] == 0:
        st.caption("아직 질의개념복습 풀이 이력이 없습니다. 학생이 로그인학생 화면에서 복습 문제를 풀면 여기에 통계와 AI 취약점 분석이 나타납니다.")
        return

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("총 풀이", f"{stats['total']}문항")
    with c2:
        st.metric("정답률", f"{stats['accuracy_pct']}%")
    with c3:
        st.metric("오답", f"{stats['wrong']}문항")

    # 최근 7일 일별 복습 퀴즈 결과 (학생·학부모가 한눈에 추이를 볼 수 있게)
    try:
        daily = get_concept_review_daily_stats(student_id, days=7)
    except Exception:
        daily = []
    if daily:
        st.markdown("##### 📆 최근 7일 복습 퀴즈 결과")
        df = pd.DataFrame(daily)
        # 날짜 순으로 정렬되어 있으므로 인덱스는 날짜로 설정
        chart_df = df.set_index("date")[["correct", "wrong"]]
        st.bar_chart(chart_df, use_container_width=True)
        st.caption("초록=정답, 빨강=오답 (최근 7일 기준)")

    try:
        wrong_items = get_concept_review_wrong_items(student_id, limit=30)
        recent = get_concept_review_recent_all(student_id, limit=50)
        analysis = generate_weakness_analysis_from_quiz(student_handle, stats, wrong_items, recent)
        st.markdown("**AI 취약점 분석**")
        st.write(analysis)
    except Exception as e:
        show_error("취약점 분석 로드 실패", e, context="generate_weakness_analysis", show_trace=False)
