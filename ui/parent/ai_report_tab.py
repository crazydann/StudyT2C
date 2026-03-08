import pandas as pd
import streamlit as st

from services.analytics_service import get_subject_achievement, get_offtopic_chat_summary


def render_ai_report_tab(student_id: str):
    st.subheader("📊 AI 학습 리포트")

    try:
        data = get_subject_achievement(student_id, lookback_days=30)
    except Exception as e:
        st.error(f"리포트를 불러오는 중 오류가 발생했습니다: {e}")
        return

    summary = data.get("summary", {}) or {}
    subjects = data.get("subjects", []) or []

    avg_score = summary.get("avg_score") or 0
    total_q = summary.get("total_questions") or 0
    avg_cr = summary.get("avg_correct_rate")

    # 상단 성취도 요약 카드
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("평균 성취도 점수", f"{avg_score}점")
    with c2:
        st.metric("누적 질문 수(최근 30일)", f"{total_q}건")
    with c3:
        cr_str = f"{int(avg_cr * 100)}%" if isinstance(avg_cr, (int, float)) else "N/A"
        st.metric("평균 정답률", cr_str)

    # 공부 시간 중 비공부 질문 모니터링
    try:
        off = get_offtopic_chat_summary(student_id, lookback_days=7)
    except Exception:
        off = {"total": 0, "by_category": {}, "items": []}

    total_off = off.get("total", 0)
    by_cat = off.get("by_category", {}) or {}

    # 주의/경고 배지 (5건 이상 주의, 10건 이상 경고)
    badge = ""
    if total_off >= 10:
        badge = " 🔴 경고"
    elif total_off >= 5:
        badge = " 🟠 주의"

    with st.container(border=True):
        if total_off == 0:
            st.markdown("#### 🧠 공부 시간 AI 튜터 사용")
            st.caption("최근 7일 동안 공부 시간 중 공부 외 질문 없이 잘 활용하고 있어요.")
        else:
            st.markdown(f"#### ⚠️ 공부 외 질문 모니터링{badge}")
            parts = [f"{k}: {v}건" for k, v in by_cat.items()]
            st.write(f"최근 7일 공부 시간 중 공부 외 질문: **{total_off}건**")
            if parts:
                st.caption("유형별 분포: " + ", ".join(parts))

    st.markdown("---")

    if not subjects:
        st.caption("표시할 과목별 데이터가 아직 없습니다.")
        return

    df = pd.DataFrame(subjects)

    st.markdown("#### 과목별 성취도")
    for _, row in df.iterrows():
        label = row.get("label")
        score = int(row.get("score") or 0)
        cr = row.get("correct_rate")
        cr_str = f"{int(cr * 100)}%" if isinstance(cr, (int, float)) else "N/A"

        st.markdown(f"**{label}** · 성취도 {score}점 · 정답률 {cr_str}")
        st.progress(min(score, 100) / 100.0)

    st.markdown("#### 과목별 성취도 비교")
    chart_df = df[["label", "score"]].set_index("label")
    st.bar_chart(chart_df)

    # 공부 외 질문 히스토리 (최근 10개)
    items = (off.get("items") or [])[:10]
    st.markdown("#### 공부 시간 중 공부 외 질문 히스토리 (최근)")
    if not items:
        st.caption("최근 7일 동안 공부 시간 중 공부 외 질문이 없습니다.")
    else:
        for it in items:
            ts = (it.get("created_at") or "")[:16].replace("T", " ")
            cat = it.get("category") or "OTHER"
            content = it.get("content") or ""
            with st.container(border=True):
                st.caption(f"{ts} · 유형: {cat}")
                st.write(content)

