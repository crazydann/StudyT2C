# ui/parent/consult_tab.py
import pandas as pd
import streamlit as st

from ui.ui_errors import show_error
from ui.ui_common import format_ts_kst
from services.analytics_service import get_student_consultation_report
from ui.parent.dev import render_dev_json
from ui.parent.data_loaders import fetch_teacher_consult_logs_for_student


def _render_learning_profile_block(profile: dict):
    st.markdown("#### 🧠 학습 성향 (학생 체크 기반)")
    if not profile or (profile.get("count") or 0) == 0:
        st.caption("아직 학생 피드백 데이터가 없습니다. (오답노트에서 '이해됨/헷갈림'과 원인을 저장하면 쌓입니다.)")
        return

    cnt = int(profile.get("count") or 0)
    conf = profile.get("confused_rate")
    conf_str = f"{int(conf*100)}%" if isinstance(conf, (int, float)) else "N/A"

    c1, c2 = st.columns([1, 2])
    with c1:
        st.metric("헷갈림 비율", conf_str)
        st.caption(f"최근 {profile.get('lookback_days', 14)}일 · {cnt}건")
    with c2:
        rt = profile.get("reason_top") or []
        if rt:
            lines = [f"- {x.get('label')} ({x.get('count')})" for x in rt if isinstance(x, dict)]
            st.markdown("**자주 선택한 오답 원인 TOP**\n" + "\n".join(lines))
        else:
            st.caption("원인 선택 데이터가 아직 부족합니다.")


def _render_non_submit_reason_block(ns: dict):
    st.markdown("#### 🧾 미제출 사유 TOP (학생 선택 기반)")
    if not ns or (ns.get("count") or 0) == 0:
        st.caption("아직 미제출 사유 데이터가 없습니다. (학생이 미제출 숙제에서 사유 버튼을 누르면 쌓입니다.)")
        return

    top = ns.get("top") or []
    if not top:
        st.caption("데이터 부족")
        return

    lines = []
    for x in top:
        if isinstance(x, dict):
            lines.append(f"- {x.get('label')} ({x.get('count')})")
    st.markdown("\n".join(lines) if lines else "데이터 부족")
    st.caption(f"최근 {ns.get('lookback_days', 14)}일 · {int(ns.get('count') or 0)}건")


def _render_consult_kpi_header(report: dict):
    hw = report.get("homework", {}) or {}
    gt = report.get("grading_trend", {}) or {}
    top = report.get("top_wrong", {}) or {}
    profile = report.get("learning_profile", {}) or {}
    ns = report.get("non_submit_reasons", {}) or {}

    rate = hw.get("submission_rate")
    rate_str = f"{int(rate*100)}%" if isinstance(rate, (int, float)) else "N/A"

    points = gt.get("points") or []
    latest_wrong_rate = None
    if points and isinstance(points[-1], dict) and points[-1].get("wrong_rate") is not None:
        latest_wrong_rate = points[-1]["wrong_rate"]
    wr_str = f"{int(latest_wrong_rate*100)}%" if isinstance(latest_wrong_rate, (int, float)) else "N/A"

    conf = profile.get("confused_rate")
    conf_str = f"{int(conf*100)}%" if isinstance(conf, (int, float)) else "N/A"

    unsubmitted_cnt = int(report.get("unsubmitted_homework_count") or 0)

    top_concepts = top.get("top_wrong_concepts") or []
    top_reasons = top.get("top_wrong_reasons") or []
    tc1 = top_concepts[0] if top_concepts else "N/A"
    tr1 = top_reasons[0] if top_reasons else "N/A"

    rt = profile.get("reason_top") or []
    rt1 = rt[0].get("label") if rt and isinstance(rt[0], dict) else "N/A"

    ns_top = ns.get("top") or []
    ns1 = ns_top[0].get("label") if ns_top and isinstance(ns_top[0], dict) else "N/A"

    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("숙제 제출률(14일)", rate_str)
        st.caption(f"미제출 {unsubmitted_cnt}건 · 사유TOP: {ns1}")
    with c2:
        st.metric("최근 오답률", wr_str)
        st.caption(f"오답개념TOP: {tc1}")
    with c3:
        st.metric("헷갈림 비율(학생체크)", conf_str)
        st.caption(f"오답원인TOP: {rt1 if rt1 != 'N/A' else tr1}")

    line = (
        f"최근 2주 숙제 제출률 {rate_str}, 미제출 {unsubmitted_cnt}건(사유TOP: {ns1}). "
        f"최근 오답률 {wr_str}이며, 학생 체크 기준 헷갈림 비율은 {conf_str}입니다. "
        f"다음 학습은 오답개념({tc1})과 원인({rt1 if rt1 != 'N/A' else tr1}) 중심으로 보완합니다."
    )
    st.info(line)


def _render_teacher_consult_summary_and_history(supabase, student_id: str):
    logs = fetch_teacher_consult_logs_for_student(supabase, student_id, limit=5)

    st.markdown("### 🧑‍🏫 최근 선생님 상담 요약")
    if not logs:
        st.caption("최근 선생님 상담 요약이 아직 없습니다. (선생님 화면에서 상담 로그 저장 시 표시됩니다.)")
        return

    latest = logs[0]
    created = format_ts_kst(latest.get("created_at"), with_seconds=True)
    one_liner = latest.get("one_liner") or ""

    if created:
        st.caption(f"기록일시: {created}")
    if one_liner:
        st.info(one_liner)

    st.markdown("#### 🗂️ 상담 로그 히스토리 (최근 5개)")
    options = []
    key_map = {}
    for row in logs:
        cid = row.get("id")
        c_at = format_ts_kst(row.get("created_at"), with_seconds=True)
        ol = (row.get("one_liner") or "").strip()
        title = f"{c_at} · {ol}" if c_at else (ol if ol else str(cid))
        options.append(title)
        key_map[title] = row

    selected_title = st.selectbox("상담 로그 선택", options=options, index=0, key=f"p_consult_hist_{student_id}")
    selected = key_map.get(selected_title) or latest

    with st.expander("상담 로그 상세 보기", expanded=False):
        c_at = format_ts_kst(selected.get("created_at"), with_seconds=True)
        if c_at:
            st.caption(f"일시: {c_at}")

        if selected.get("one_liner"):
            st.markdown("**한 줄 요약**")
            st.info(selected.get("one_liner"))

        if selected.get("note"):
            st.markdown("**선생님 메모**")
            st.write(selected.get("note"))

        snapshot = selected.get("snapshot")
        if snapshot is not None and st.session_state.get("dev_mode", False):
            render_dev_json(
                "상담 로그 KPI 스냅샷",
                snapshot,
                key=f"p_consult_json_{student_id}_{selected.get('id')}",
            )


def render_consult_tab(supabase, student_id: str):
    st.subheader("🧾 상담 리포트 (학부모용)")

    _render_teacher_consult_summary_and_history(supabase, student_id)
    st.divider()

    try:
        report = get_student_consultation_report(student_id)
    except Exception as e:
        show_error("상담 리포트 생성 실패", e, context="get_student_consultation_report", show_trace=False)
        report = {
            "homework": {"lookback_days": 14, "assigned_total": 0, "submitted_total": 0, "submission_rate": None, "daily": []},
            "unsubmitted_homework_count": 0,
            "non_submit_reasons": {"count": 0, "top": [], "lookback_days": 14},
            "grading_trend": {"has_recent": False, "points": []},
            "top_wrong": {"top_wrong_concepts": [], "top_wrong_reasons": []},
            "learning_profile": {"count": 0, "confused_rate": None, "reason_top": [], "lookback_days": 14},
            "consult_script": "데이터를 불러오지 못했습니다.",
        }

    hw = report.get("homework", {}) or {}
    gt = report.get("grading_trend", {}) or {}
    profile = report.get("learning_profile", {}) or {}
    ns = report.get("non_submit_reasons", {}) or {}

    with st.container(border=True):
        _render_consult_kpi_header(report)

    st.markdown("#### 🗣️ 상담 스크립트(한 문단)")
    st.info(report.get("consult_script") or "")

    st.markdown("---")
    _render_non_submit_reason_block(ns)

    st.markdown("---")
    _render_learning_profile_block(profile)

    daily = hw.get("daily") or []
    if daily:
        df_hw = pd.DataFrame(daily).set_index("date")
        st.markdown("#### 📈 숙제 배정/제출 추이(일자별)")
        st.line_chart(df_hw[["assigned", "submitted"]])

    points = gt.get("points") or []
    if points:
        df_gt = pd.DataFrame(points)
        df_gt["wrong_rate_pct"] = df_gt["wrong_rate"].apply(lambda x: (x * 100) if isinstance(x, (int, float)) else None)
        df_gt = df_gt.set_index("date")
        st.markdown("#### 📉 최근 채점 오답률 추이(제출 기준)")
        st.line_chart(df_gt[["wrong_rate_pct"]])

    if st.session_state.get("dev_mode", False):
        render_dev_json(
            "시스템 KPI 스냅샷",
            {
                "homework": {
                    "lookback_days": hw.get("lookback_days"),
                    "assigned_total": hw.get("assigned_total"),
                    "submission_rate": hw.get("submission_rate"),
                    "submitted_total": hw.get("submitted_total"),
                },
                "grading_trend": gt,
                "learning_profile": profile,
                "non_submit_reasons": ns,
                "unsubmitted_homework_count": report.get("unsubmitted_homework_count"),
                "consult_script": report.get("consult_script"),
            },
            key=f"p_system_kpi_{student_id}",
        )