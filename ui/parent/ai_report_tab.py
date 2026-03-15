import pandas as pd
import streamlit as st

from ui.ui_common import format_ts_kst
from services.analytics_service import (
    get_subject_achievement,
    get_offtopic_chat_summary,
    get_study_chat_history,
    get_wrong_reason_summary,
    get_student_weekly_monthly_report,
    get_learning_trend_summary_sentence,
)
from ui.focus_ui import render_focus_section
from ui.quiz_weakness_ui import render_quiz_weakness_section


def render_ai_report_tab(student_id: str, student_handle: str = ""):
    st.subheader("📊 AI 학습 리포트")

    try:
        trend_sentence = get_learning_trend_summary_sentence(student_id, lookback_days=14)
        if trend_sentence:
            with st.container(border=True):
                st.markdown("💡 **학습 추이** — " + trend_sentence)
    except Exception:
        pass

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

    # 오답 유형 세분화 (찍음 vs 몰라서 vs 실수)
    try:
        wrong_reason = get_wrong_reason_summary(student_id, lookback_days=30)
        by_reason = wrong_reason.get("by_reason") or []
        if by_reason:
            with st.container(border=True):
                st.caption("📌 오답 유형별 집계 (학생 체크 기준, 최근 30일)")
                st.markdown(" · ".join([f"{r['label']} {r['count']}건" for r in by_reason]))
    except Exception:
        pass

    # 주간/월간 리포트 (한 장 요약 + 그래프)
    st.markdown("---")
    st.markdown("#### 📅 주간/월간 리포트")
    period_report = st.radio("기간", ["주간", "월간"], key="parent_report_period", horizontal=True)
    period_key = "week" if period_report == "주간" else "month"
    windows = 4 if period_key == "week" else 3
    try:
        report_data = get_student_weekly_monthly_report(student_id, period=period_key, windows=windows)
        summary = report_data.get("summary") or {}
        chart_list = report_data.get("chart") or []
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.metric("채점 횟수(해당 기간)", summary.get("grading_count", 0))
        with c2:
            st.metric("튜터 질문 수", summary.get("chat_count", 0))
        with c3:
            wr = summary.get("wrong_rate")
            st.metric("오답률", f"{int(wr*100)}%" if isinstance(wr, (int, float)) else "N/A")
        with c4:
            sr = summary.get("submission_rate")
            st.metric("숙제 제출률", f"{int(sr*100)}%" if isinstance(sr, (int, float)) else "N/A")
        st.caption(f"연속 학습 일수: {summary.get('streak_days', 0)}일")
        if chart_list:
            chart_df = pd.DataFrame(chart_list)
            chart_df = chart_df.set_index("label")
            st.line_chart(chart_df[["grading_count", "chat_count"]].rename(columns={"grading_count": "채점 수", "chat_count": "질문 수"}))
    except Exception as e:
        st.caption(f"리포트 로드 실패: {e}")

    # 1) 공부 관련 질문/답변 이력 — 접기 + 내부 스크롤
    try:
        study = get_study_chat_history(student_id, lookback_days=30, limit=30)
        study_items = study.get("items", []) or []
    except Exception:
        study_items = []

    with st.expander(f"질문 이력 (최근 30일) — {len(study_items)}건", expanded=False):
        if not study_items:
            st.caption("공부 관련 질문 이력이 없습니다.")
        else:
            st.caption("아래 영역에서 스크롤하여 개별 질문·답변을 확인하세요.")
            parts = []
            for it in study_items[:30]:
                ts = format_ts_kst(it.get("created_at"))
                subj = it.get("subject", "OTHER")
                def _esc(s: str) -> str:
                    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("\n", "<br>")
                q = _esc(it.get("question") or "")
                raw_a = it.get("answer") or ""
                a = _esc(raw_a[:400]) + ("..." if len(raw_a) > 400 else "")
                if len((it.get("answer") or "")) > 400:
                    a += "..."
                parts.append(f"<div style='border-bottom:1px solid #eee;padding:8px 0;'><strong>{ts}</strong> · {subj}<br><strong>질문</strong> {q}<br><strong>답변</strong> {a}</div>")
            st.markdown(
                f'<div style="max-height: 380px; overflow-y: auto; padding: 4px;">{"".join(parts)}</div>',
                unsafe_allow_html=True,
            )

    # 2) 공부 외 질문 — 접기 + 내부 스크롤
    try:
        off = get_offtopic_chat_summary(student_id, lookback_days=7)
    except Exception:
        off = {"total": 0, "by_category": {}, "items": []}

    total_off = off.get("total", 0)
    by_cat = off.get("by_category", {}) or {}
    items = (off.get("items") or [])[:20]
    badge = " 🔴" if total_off >= 10 else " 🟠" if total_off >= 5 else ""

    with st.expander(f"공부 외 질문 (최근 7일){badge} — {total_off}건", expanded=False):
        if total_off == 0:
            st.caption("공부 시간 중 공부 외 질문 없이 잘 활용하고 있어요.")
        else:
            if by_cat:
                st.caption("유형: " + ", ".join(f"{k} {v}건" for k, v in by_cat.items()))
            if not items:
                st.caption("히스토리 없음.")
            else:
                st.caption("아래 스크롤로 개별 항목을 확인하세요.")
                parts = []
                for it in items:
                    ts = format_ts_kst(it.get("created_at"))
                    cat = (it.get("category") or "OTHER").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
                    content = (it.get("content") or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace("\n", "<br>")
                    parts.append(f"<div style='border-bottom:1px solid #eee;padding:6px 0;'><strong>{ts}</strong> · {cat}<br>{content}</div>")
                st.markdown(
                    f'<div style="max-height: 320px; overflow-y: auto; padding: 4px;">{"".join(parts)}</div>',
                    unsafe_allow_html=True,
                )

    st.markdown("---")

    render_focus_section(student_id, student_handle or "자녀")

    render_quiz_weakness_section(student_id, student_handle or "자녀", lookback_days=90)

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
