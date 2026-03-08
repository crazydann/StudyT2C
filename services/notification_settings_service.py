# services/notification_settings_service.py
"""
학부모/선생님의 학생별 이메일 수신 설정 조회·저장.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

DEFAULT_SETTINGS = {
    "email_enabled": True,
    "receive_offtopic": True,
    "receive_weekly_report": False,
    "receive_daily_summary": False,
    "frequency": "realtime",
}
FREQUENCY_OPTIONS = ["realtime", "daily", "weekly", "monthly"]


def fetch_notification_settings(supabase, user_id: str, student_user_id: str) -> Dict[str, Any]:
    """
    (user_id, student_user_id)에 해당하는 수신 설정 한 건 조회.
    없으면 기본값 반환.
    """
    try:
        rows = (
            supabase.table("notification_settings")
            .select("*")
            .eq("user_id", user_id)
            .eq("student_user_id", student_user_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            return {**DEFAULT_SETTINGS, "user_id": user_id, "student_user_id": student_user_id}
        r = rows[0]
        return {
            "email_enabled": r.get("email_enabled", True),
            "receive_offtopic": r.get("receive_offtopic", True),
            "receive_weekly_report": r.get("receive_weekly_report", False),
            "receive_daily_summary": r.get("receive_daily_summary", False),
            "frequency": (r.get("frequency") or "realtime") in FREQUENCY_OPTIONS and r.get("frequency") or "realtime",
            "user_id": user_id,
            "student_user_id": student_user_id,
        }
    except Exception:
        return {**DEFAULT_SETTINGS, "user_id": user_id, "student_user_id": student_user_id}


def upsert_notification_settings(
    supabase,
    user_id: str,
    student_user_id: str,
    role: str,
    email_enabled: bool,
    receive_offtopic: bool,
    receive_weekly_report: bool,
    receive_daily_summary: bool,
    frequency: str,
) -> bool:
    """수신 설정 upsert (있으면 업데이트, 없으면 삽입)."""
    if frequency not in FREQUENCY_OPTIONS:
        frequency = "realtime"
    try:
        payload = {
            "user_id": user_id,
            "student_user_id": student_user_id,
            "role": role,
            "email_enabled": email_enabled,
            "receive_offtopic": receive_offtopic,
            "receive_weekly_report": receive_weekly_report,
            "receive_daily_summary": receive_daily_summary,
            "frequency": frequency,
        }
        supabase.table("notification_settings").upsert(
            payload,
            on_conflict="user_id,student_user_id",
            ignore_duplicates=False,
        ).execute()
        return True
    except Exception:
        return False


def get_offtopic_recipients_realtime(student_id: str) -> List[Dict[str, Any]]:
    """
    해당 학생에 대해 '실시간' 공부 외 질문 알림을 받을 수신자 목록.
    반환: [ {"email": str, "role": "parent"|"teacher"}, ... ]
    """
    from services.supabase_client import supabase_service, supabase
    sb = supabase_service if supabase_service is not None else supabase
    out: List[Dict[str, Any]] = []

    try:
        # 부모: parent_student_links + users.notification_email + notification_settings
        parent_links = (
            sb.table("parent_student_links")
            .select("parent_user_id")
            .eq("student_user_id", student_id)
            .execute()
        ).data or []
        for r in parent_links:
            uid = r.get("parent_user_id")
            if not uid:
                continue
            settings_rows = (
                sb.table("notification_settings")
                .select("email_enabled, receive_offtopic, frequency")
                .eq("user_id", uid)
                .eq("student_user_id", student_id)
                .limit(1)
                .execute()
            ).data or []
            if settings_rows:
                s = settings_rows[0]
                if not s.get("email_enabled") or not s.get("receive_offtopic") or (s.get("frequency") or "realtime") != "realtime":
                    continue
            else:
                # 설정 없으면 기본: 실시간 + 공부외 수신
                pass
            user_rows = sb.table("users").select("notification_email").eq("id", uid).limit(1).execute().data or []
            if not user_rows:
                continue
            email = (user_rows[0].get("notification_email") or "").strip()
            if email and "@" in email:
                out.append({"email": email, "role": "parent"})

        # 선생: teacher_student_links + users.notification_email + notification_settings
        teacher_links = (
            sb.table("teacher_student_links")
            .select("teacher_user_id")
            .eq("student_user_id", student_id)
            .execute()
        ).data or []
        for r in teacher_links:
            uid = r.get("teacher_user_id")
            if not uid:
                continue
            settings_rows = (
                sb.table("notification_settings")
                .select("email_enabled, receive_offtopic, frequency")
                .eq("user_id", uid)
                .eq("student_user_id", student_id)
                .limit(1)
                .execute()
            ).data or []
            if settings_rows:
                s = settings_rows[0]
                if not s.get("email_enabled") or not s.get("receive_offtopic") or (s.get("frequency") or "realtime") != "realtime":
                    continue
            user_rows = sb.table("users").select("notification_email").eq("id", uid).limit(1).execute().data or []
            if not user_rows:
                continue
            email = (user_rows[0].get("notification_email") or "").strip()
            if email and "@" in email:
                out.append({"email": email, "role": "teacher"})
    except Exception:
        pass
    return out
