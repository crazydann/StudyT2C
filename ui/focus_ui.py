# ui/focus_ui.py
"""
학부모/선생님 화면에서 집중 현황(탭 이탈·사용 구간) 표시 및 탭 이탈 시 알람 발송.
"""
import streamlit as st

from services.focus_events_service import (
    get_daily_usage_and_idle,
    get_recent_left_tab,
    should_send_focus_left_alert,
    record_focus_alert_sent,
)
from services.notification_settings_service import get_offtopic_recipients_realtime
from services.email_service import send_focus_left_alert


def _format_ts(ts: str | None) -> str:
    if not ts:
        return "—"
    try:
        if "T" in ts:
            return ts[:16].replace("T", " ")
        return ts[:16]
    except Exception:
        return str(ts)


def render_focus_section(student_id: str, student_handle: str) -> None:
    """
    집중 현황 섹션: 오늘 사용 구간, 비집중 구간, 방금 탭 이탈 배지.
    학부모/선생이 이 화면을 열 때 최근 탭 이탈이 있으면 알람 이메일 발송(쿨다운 15분).
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

    # 방금 탭 이탈 여부 (최근 5분 이내 left_tab)
    recent_left = get_recent_left_tab(student_id, within_minutes=5)
    if recent_left:
        st.warning("⚠️ **방금 탭을 벗어났습니다** — 다른 탭이나 창을 열었을 수 있어요. 아래에서 비집중 구간을 확인하세요.")

        # 탭 이탈 시 즉시 알람: 수신자에게 이메일 발송 (15분 쿨다운)
        if should_send_focus_left_alert(student_id, within_minutes=5):
            recipients = get_offtopic_recipients_realtime(student_id)
            if recipients and send_focus_left_alert(recipients, student_handle):
                record_focus_alert_sent(student_id)
                st.success("해당 학생의 알림 수신자에게 탭 이탈 알림 메일을 발송했습니다.")

    if not usage_start and not usage_end:
        st.caption("오늘 기록된 탭 사용 이벤트가 없습니다. 학생이 학습 대시보드를 켜 두면 자동으로 기록됩니다.")
        return

    c1, c2 = st.columns(2)
    with c1:
        st.metric("오늘 첫 사용", _format_ts(usage_start))
    with c2:
        st.metric("오늘 마지막 사용", _format_ts(usage_end))
    st.caption(f"오늘 탭 이탈 횟수: **{left_tab_count}회** (다른 탭/창으로 전환한 횟수)")

    if idle_periods:
        st.markdown("**비집중 구간** (탭을 벗어났다가 돌아온 시간대)")
        for start, end in idle_periods[:20]:
            st.caption(f"· {_format_ts(start)} → {_format_ts(end)}")
    else:
        st.caption("비집중 구간이 없거나, 아직 탭에 복귀하지 않은 상태일 수 있습니다.")
