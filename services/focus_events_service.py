# services/focus_events_service.py
"""
학생 탭 이탈/복귀/닫기 이벤트 조회.
- 일별 사용 구간(처음~마지막), 비집중 구간(left_tab ~ returned_tab)
- 방금 탭 이탈 여부 (알람용)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from services.supabase_client import supabase_service, supabase


def _sb():
    return supabase_service if supabase_service is not None else supabase


def get_focus_events(
    student_id: str,
    since: Optional[datetime] = None,
    until: Optional[datetime] = None,
    limit: int = 500,
) -> List[Dict[str, Any]]:
    """학생의 focus_events 목록 (since~until, created_at 내림)."""
    try:
        q = (
            _sb()
            .table("focus_events")
            .select("id, student_user_id, event_type, created_at")
            .eq("student_user_id", student_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if since:
            q = q.gte("created_at", since.isoformat())
        if until:
            q = q.lte("created_at", until.isoformat())
        rows = q.execute().data or []
        return sorted(rows, key=lambda x: (x.get("created_at") or ""), reverse=False)
    except Exception:
        return []


def get_recent_left_tab(
    student_id: str,
    within_minutes: int = 5,
) -> Optional[Dict[str, Any]]:
    """가장 최근 left_tab 이벤트가 within_minutes 이내인지. 있으면 해당 행 반환."""
    try:
        since = (datetime.now(timezone.utc) - timedelta(minutes=within_minutes)).isoformat()
        rows = (
            _sb()
            .table("focus_events")
            .select("id, event_type, created_at")
            .eq("student_user_id", student_id)
            .eq("event_type", "left_tab")
            .gte("created_at", since)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        return rows[0] if rows else None
    except Exception:
        return None


def is_currently_away(student_id: str, within_minutes: int = 5) -> bool:
    """최근 within_minutes 안에 left_tab이 있고, 그 뒤에 returned_tab이 없으면 True."""
    events = get_focus_events(
        student_id,
        since=datetime.now(timezone.utc) - timedelta(minutes=within_minutes * 2),
        limit=50,
    )
    events = sorted(events, key=lambda x: x.get("created_at") or "", reverse=True)
    for e in events:
        if e.get("event_type") == "returned_tab":
            return False
        if e.get("event_type") == "left_tab":
            return True
    return False


def get_daily_usage_and_idle(
    student_id: str,
    date: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    해당 날짜(기본 오늘)의 사용 구간·비집중 구간 반환.
    - usage_start, usage_end: 당일 첫 이벤트 ~ 마지막 이벤트 (있을 때만)
    - idle_periods: [ (start, end), ... ] left_tab 시각 ~ returned_tab 시각
    - left_tab_count: 당일 left_tab 발생 횟수
    """
    tz = timezone.utc
    if date is None:
        date = datetime.now(tz)
    day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = day_start + timedelta(days=1)

    events = get_focus_events(student_id, since=day_start, until=day_end, limit=1000)
    if not events:
        return {
            "date": day_start.date().isoformat(),
            "usage_start": None,
            "usage_end": None,
            "idle_periods": [],
            "left_tab_count": 0,
        }

    first_ts = events[0].get("created_at")
    last_ts = events[-1].get("created_at")
    idle_periods: List[Tuple[str, str]] = []
    left_ts: Optional[str] = None
    left_tab_count = 0

    for e in events:
        typ = e.get("event_type")
        ts = e.get("created_at")
        if typ == "left_tab":
            left_ts = ts
            left_tab_count += 1
        elif typ == "returned_tab" and left_ts:
            idle_periods.append((left_ts, ts))
            left_ts = None

    return {
        "date": day_start.date().isoformat(),
        "usage_start": first_ts,
        "usage_end": last_ts,
        "idle_periods": idle_periods,
        "left_tab_count": left_tab_count,
    }


def get_focus_alert_cooldown_minutes() -> int:
    return 15


def should_send_focus_left_alert(student_id: str, within_minutes: int = 5) -> bool:
    """최근 within_minutes 안에 left_tab이 있고, 마지막 발송이 쿨다운(15분) 이전이면 True."""
    recent = get_recent_left_tab(student_id, within_minutes=within_minutes)
    if not recent:
        return False
    try:
        row = (
            _sb()
            .table("focus_alert_sent")
            .select("last_sent_at")
            .eq("student_user_id", student_id)
            .limit(1)
            .execute()
            .data
        )
        if not row:
            return True
        from datetime import datetime, timezone
        last = row[0].get("last_sent_at")
        if not last:
            return True
        if isinstance(last, str):
            last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
        else:
            last_dt = last
        if last_dt.tzinfo is None:
            last_dt = last_dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - last_dt
        return delta.total_seconds() >= get_focus_alert_cooldown_minutes() * 60
    except Exception:
        return True


def record_focus_alert_sent(student_id: str) -> None:
    """탭 이탈 알람 이메일 발송 후 쿨다운 기록."""
    try:
        _sb().table("focus_alert_sent").upsert(
            {"student_user_id": student_id, "last_sent_at": datetime.now(timezone.utc).isoformat()},
            on_conflict="student_user_id",
        ).execute()
    except Exception:
        pass
