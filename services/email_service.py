# services/email_service.py
"""
공부 외 질문 발생 시 학부모에게 이메일 알림 발송 (Resend 사용).
RESEND_API_KEY가 없으면 발송 건너뜀.
"""
from __future__ import annotations

from typing import List, Optional

import config


def _get_resend_api_key() -> Optional[str]:
    return getattr(config, "RESEND_API_KEY", None)


def send_offtopic_alert(
    to_emails: List[str],
    student_handle: str,
    offtopic_content: str,
    subject_prefix: str = "[StudyT2C]",
) -> bool:
    """
    공부 외 질문 발생 알림 이메일 발송.
    to_emails가 비어있거나 API 키가 없으면 False.
    """
    if not to_emails:
        return False
    api_key = _get_resend_api_key()
    if not api_key:
        return False

    try:
        import resend
        resend.api_key = api_key

        content_preview = (offtopic_content or "").strip()[:200]
        if len(offtopic_content or "") > 200:
            content_preview += "..."

        subject = f"{subject_prefix} 공부 시간 중 공부 외 질문이 있었어요"
        html = f"""
        <p>안녕하세요, StudyT2C입니다.</p>
        <p><strong>{student_handle}</strong> 님이 공부 시간에 공부와 관련 없는 질문을 했습니다.</p>
        <blockquote style="margin:12px 0; padding:12px; background:#f5f5f5; border-radius:8px;">
            {content_preview}
        </blockquote>
        <p>학부모 화면의 <strong>AI 리포트</strong> 탭에서 자세한 이력을 확인할 수 있습니다.</p>
        <p>— StudyT2C</p>
        """

        for to_addr in to_emails:
            if not (to_addr and "@" in to_addr):
                continue
            try:
                resend.Emails.send({
                    "from": "StudyT2C <onboarding@resend.dev>",
                    "to": [to_addr.strip()],
                    "subject": subject,
                    "html": html,
                })
            except Exception:
                pass
        return True
    except Exception:
        return False


def get_parent_emails_for_student(student_id: str) -> List[str]:
    """
    해당 학생과 연결된 학부모의 알림 이메일 목록 반환.
    """
    from services.supabase_client import supabase_service, supabase
    sb = supabase_service if supabase_service is not None else supabase

    try:
        links = (
            sb.table("parent_student_links")
            .select("parent_user_id")
            .eq("student_user_id", student_id)
            .execute()
        ).data or []
        parent_ids = [r["parent_user_id"] for r in links if r.get("parent_user_id")]
        if not parent_ids:
            return []

        users = (
            sb.table("users")
            .select("notification_email")
            .in_("id", parent_ids)
            .execute()
        ).data or []
        emails = []
        for u in users:
            email = (u.get("notification_email") or "").strip()
            if email and "@" in email:
                emails.append(email)
        return list(dict.fromkeys(emails))
    except Exception:
        return []
