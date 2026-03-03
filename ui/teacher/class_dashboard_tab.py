import math
import pandas as pd
import streamlit as st

from services.analytics_service import get_class_dashboard_rows


def _fmt_pct(v) -> str:
    if not isinstance(v, (int, float)):
        return "N/A"
    if math.isnan(v):
        return "N/A"
    return f"{int(v * 100)}%"


def render_class_dashboard_tab(state: dict, student_ids, handle_map: dict):
    st.subheader("📊 반 대시보드")

    if not student_ids:
        st.info("연결된 학생이 없습니다.")
        return

    # 분석 데이터 로드
    rows = get_class_dashboard_rows([str(sid) for sid in student_ids])
    if not rows:
        st.info("아직 충분한 데이터가 없어 반 대시보드를 구성하지 못했습니다.")
        return

    # 이름/핸들 붙이기
    for r in rows:
        sid = str(r.get("student_id"))
        r["student_name"] = handle_map.get(sid, sid)

    df = pd.DataFrame(rows)

    # 상단 KPI 요약
    total_students = len(rows)
    high_risk = sum(1 for r in rows if (r.get("risk_score") or 0) >= 70)

    avg_wrong = df["latest_wrong_rate"].dropna().mean() if "latest_wrong_rate" in df else None
    avg_submit = df["submission_rate_14d"].dropna().mean() if "submission_rate_14d" in df else None

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("총 학생 수", total_students)
        st.caption(f"고위험 학생(리스크≥70): {high_risk}명")
    with c2:
        st.metric("최근 평균 오답률", _fmt_pct(avg_wrong))
    with c3:
        st.metric("최근 14일 평균 숙제 제출률", _fmt_pct(avg_submit))

    st.divider()

    # 상세 테이블
    view_cols = [
        "student_name",
        "risk_score",
        "latest_wrong_rate",
        "submission_rate_14d",
        "unsubmitted_14d",
        "confused_rate_14d",
        "top_concept",
        "top_reason",
    ]
    view_df = df[view_cols].copy()
    if "latest_wrong_rate" in view_df:
        view_df["latest_wrong_rate"] = view_df["latest_wrong_rate"].apply(
            lambda v: _fmt_pct(v) if isinstance(v, (int, float)) and not math.isnan(v) else ""
        )
    if "submission_rate_14d" in view_df:
        view_df["submission_rate_14d"] = view_df["submission_rate_14d"].apply(
            lambda v: _fmt_pct(v) if isinstance(v, (int, float)) and not math.isnan(v) else ""
        )
    if "confused_rate_14d" in view_df:
        view_df["confused_rate_14d"] = view_df["confused_rate_14d"].apply(
            lambda v: _fmt_pct(v) if isinstance(v, (int, float)) and not math.isnan(v) else ""
        )

    st.markdown("#### 학생별 위험도 및 요약")
    st.dataframe(
        view_df.rename(
            columns={
                "student_name": "학생",
                "risk_score": "위험 점수(0~100)",
                "latest_wrong_rate": "최근 오답률",
                "submission_rate_14d": "숙제 제출률(14일)",
                "unsubmitted_14d": "미제출 숙제 수(14일)",
                "confused_rate_14d": "헷갈림 비율(14일)",
                "top_concept": "오답 개념 TOP",
                "top_reason": "오답 원인 TOP",
            }
        ),
        use_container_width=True,
    )

    # 위험 학생 빠른 이동
    st.markdown("#### 🔎 학생 상세로 바로 이동")
    options = [f"{r['student_name']} · risk={r['risk_score']}" for r in rows]
    opt_map = {label: r["student_id"] for label, r in zip(options, rows)}

    picked = st.selectbox("학생 선택", options=options, key="t_class_pick")
    if st.button("👀 선택한 학생 상세 보기", key="t_class_open_detail"):
        sid = opt_map.get(picked)
        if sid:
            state["selected_student"] = str(sid)
            st.rerun()

