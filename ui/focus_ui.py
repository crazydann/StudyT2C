# ui/focus_ui.py
"""
학부모/선생님 화면에서 집중 현황(탭 이탈·사용 구간) 표시 및 탭 이탈 시 알람 발송.
"""
from datetime import datetime, timezone, timedelta

import pandas as pd
import streamlit as st

from services.focus_events_service import (
    get_daily_usage_and_idle,
    get_recent_left_tab,
    should_send_focus_left_alert,
    record_focus_alert_sent,
    get_focus_alert_cooldown_minutes,
)
from services.notification_settings_service import get_offtopic_recipients_realtime
from services.email_service import send_focus_left_alert, send_focus_left_alert_with_reason
from ui.ui_common import format_ts_kst

KST = timezone(timedelta(hours=9))


def _format_time_only(ts: str) -> str:
    """그래프 라벨용 시간만 (HH:MM)."""
    try:
        s = (ts or "").replace("Z", "+00:00")
        if "T" not in s and " " in s:
            s = s.replace(" ", "T", 1) + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(KST).strftime("%H:%M")
    except Exception:
        return "—"


def _idle_duration_minutes(start_ts: str, end_ts: str) -> float:
    try:
        if not start_ts or not end_ts:
            return 0.0
        s = (start_ts or "").replace("Z", "+00:00")
        e = (end_ts or "").replace("Z", "+00:00")
        dt_s = datetime.fromisoformat(s)
        dt_e = datetime.fromisoformat(e)
        if dt_s.tzinfo is None:
            dt_s = dt_s.replace(tzinfo=timezone.utc)
        if dt_e.tzinfo is None:
            dt_e = dt_e.replace(tzinfo=timezone.utc)
        return (dt_e - dt_s).total_seconds() / 60.0
    except Exception:
        return 0.0


def render_focus_section(student_id: str, student_handle: str) -> None:
    """
    집중 현황: 전체 사용 구간, 비집중 구간(표+그래프), 탭 이탈 알림 수동 발송 및 발송 조건 안내.
    """
    st.markdown("#### 📌 집중 현황 (탭 사용)")
    try:
        daily = get_daily_usage_and_idle(student_id, date=None)
    except Exception:
        st.caption("집중 현황을 불러올 수 없습니다.")
        return

    usage_start = daily.get("usage_start")
    usage_end = daily.get("usage_end")
    idle_periods = daily.get("idle_periods") or []
    left_tab_count = daily.get("left_tab_count", 0)
    recipients = get_offtopic_recipients_realtime(student_id)
    recent_left = get_recent_left_tab(student_id, within_minutes=5)
    can_auto_send = should_send_focus_left_alert(student_id, within_minutes=5)

    # ----- 이메일 알림: 안내 + 수동 발송 버튼 + 왜 자동 발송이 안 되는지 -----
    st.markdown("**📧 탭 이탈 이메일 알림**")
    st.caption(
        "알림은 **이 화면(AI 리포트)을 열었을 때**, 자녀가 **최근 5분 이내** 탭을 벗어난 경우에만 자동 발송됩니다. "
        "**주기(일/주/월)** 는 ‘실시간 알림 수신자’ 선정에만 쓰이며, 예약 발송(크론)은 없습니다."
    )
    if st.button("📤 탭 이탈 알림 수동 발송", key=f"focus_manual_send_{student_id}"):
        ok, msg = send_focus_left_alert_with_reason(recipients, student_handle)
        if ok:
            record_focus_alert_sent(student_id)
            st.success(msg)
        else:
            st.error(msg)
    reasons = []
    if not recent_left:
        reasons.append("최근 5분 이내 탭 이탈 없음")
    elif not can_auto_send:
        reasons.append(f"발송 쿨다운({get_focus_alert_cooldown_minutes()}분) 미경과")
    if not recipients:
        reasons.append("수신자 없음(알림 ON·주기 실시간·이메일 저장 필요)")
    if reasons:
        st.caption("💡 자동 발송이 안 되는 경우: " + " | ".join(reasons))

    if recent_left:
        st.warning("⚠️ **방금 탭을 벗어났습니다** — 아래 비집중 구간에서 확인하세요.")
        if can_auto_send and recipients and send_focus_left_alert(recipients, student_handle)[0]:
            record_focus_alert_sent(student_id)
            st.success("알림 수신자에게 탭 이탈 알림 메일을 발송했습니다.")

    if not usage_start and not usage_end:
        st.caption("오늘 기록된 탭 사용 이벤트가 없습니다. 학생이 학습 대시보드를 켜 두면 자동으로 기록됩니다.")
        return

    # ----- 전체: 오늘 첫 사용 ~ 마지막 사용 -----
    st.markdown("**📊 전체 사용 구간**")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("오늘 첫 사용", format_ts_kst(usage_start))
    with c2:
        st.metric("오늘 마지막 사용", format_ts_kst(usage_end))
    with c3:
        st.metric("탭 이탈 횟수", f"{left_tab_count}회")

    # ----- 비집중 구간: 표 + 그래프 (학부모가 한눈에 이해할 수 있게) -----
    st.markdown("**🕐 비집중 구간** (탭을 벗어난 시각 → 다시 돌아온 시각)")
    if not idle_periods:
        st.caption("비집중 구간이 없거나, 아직 탭에 복귀하지 않은 상태일 수 있습니다.")
    else:
        rows = []
        for i, (start_ts, end_ts) in enumerate(idle_periods[:50], 1):
            dur = _idle_duration_minutes(start_ts, end_ts)
            start_str = format_ts_kst(start_ts)
            end_str = format_ts_kst(end_ts)
            chart_label = f"{_format_time_only(start_ts)}→{_format_time_only(end_ts)}"
            rows.append({
                "구간(나간→돌아온)": chart_label,
                "나간 시각": start_str,
                "돌아온 시각": end_str,
                "비집중(분)": round(dur, 1),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df[["나간 시각", "돌아온 시각", "비집중(분)"]], use_container_width=True, hide_index=True)

        st.caption("**그래프**: 가로 = **비집중 구간**(나간 시각→돌아온 시각), 세로 = **몇 분 동안** 탭을 벗어났는지")
        chart_df = df[["구간(나간→돌아온)", "비집중(분)"]].set_index("구간(나간→돌아온)")
        st.bar_chart(chart_df)
