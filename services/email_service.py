# services/email_service.py
"""
공부 외 질문 등 알림 이메일 발송 (Resend 사용).
학부모/선생님 역할별 템플릿 적용.
RESEND_API_KEY가 없으면 발송 건너뜀.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

import config


def _get_resend_api_key() -> Optional[str]:
    """실행 시점에 환경변수·config·.env 재로드까지 시도."""
    import os
    key = os.environ.get("RESEND_API_KEY")
    if key and str(key).strip():
        return str(key).strip()
    key = getattr(config, "RESEND_API_KEY", None)
    if key and str(key).strip():
        return str(key).strip()
    # .env가 아직 로드 안 됐을 수 있으므로 한 번 더 로드 후 재확인
    try:
        from pathlib import Path
        from dotenv import load_dotenv
        for path in (Path(__file__).resolve().parent.parent / ".env", Path.cwd() / ".env"):
            if path.exists():
                load_dotenv(path)
                break
        else:
            load_dotenv()
        key = os.environ.get("RESEND_API_KEY")
        if key and str(key).strip():
            return str(key).strip()
    except Exception:
        pass
    return None


def _render_parent_offtopic_html(student_handle: str, offtopic_content: str) -> str:
    """학부모용 공부 외 질문 알림 HTML."""
    content_preview = (offtopic_content or "").strip()[:200]
    if len(offtopic_content or "") > 200:
        content_preview += "..."
    return f"""
    <p>안녕하세요, 학부모님. StudyT2C입니다.</p>
    <p>자녀 <strong>{student_handle}</strong> 님이 공부 시간에 공부와 관련 없는 질문을 했습니다.</p>
    <blockquote style="margin:12px 0; padding:12px; background:#fff3e0; border-left:4px solid #ff9800; border-radius:4px;">
        {content_preview}
    </blockquote>
    <p>자녀의 학습 집중도를 확인하시려면 학부모 화면의 <strong>AI 리포트</strong> 탭에서 자세한 이력을 보실 수 있습니다.</p>
    <p>— StudyT2C</p>
    """


def _render_teacher_offtopic_html(student_handle: str, offtopic_content: str) -> str:
    """선생님용 공부 외 질문 알림 HTML."""
    content_preview = (offtopic_content or "").strip()[:200]
    if len(offtopic_content or "") > 200:
        content_preview += "..."
    return f"""
    <p>안녕하세요, 선생님. StudyT2C입니다.</p>
    <p>학생 <strong>{student_handle}</strong> 님이 수업(공부) 시간에 공부 외 질문을 했습니다.</p>
    <blockquote style="margin:12px 0; padding:12px; background:#e3f2fd; border-left:4px solid #2196f3; border-radius:4px;">
        {content_preview}
    </blockquote>
    <p>학생별 AI 분석 화면에서 공부 외 질문 이력과 학습 현황을 확인하실 수 있습니다.</p>
    <p>— StudyT2C</p>
    """


def send_offtopic_alert_to_recipients(
    recipients: List[Dict[str, Any]],
    student_handle: str,
    offtopic_content: str,
    subject_prefix: str = "[StudyT2C]",
) -> bool:
    """
    수신자 목록(role 포함)에 따라 학부모/선생님 템플릿으로 공부 외 질문 알림 발송.
    recipients: [ {"email": str, "role": "parent"|"teacher"}, ... ]
    """
    if not recipients:
        return False
    api_key = _get_resend_api_key()
    if not api_key:
        return False

    try:
        import resend
        resend.api_key = api_key

        subject = f"{subject_prefix} 공부 시간 중 공부 외 질문이 있었어요"
        parent_html = _render_parent_offtopic_html(student_handle, offtopic_content)
        teacher_html = _render_teacher_offtopic_html(student_handle, offtopic_content)

        for r in recipients:
            to_addr = (r.get("email") or "").strip()
            if not to_addr or "@" not in to_addr:
                continue
            role = (r.get("role") or "parent").lower()
            html = teacher_html if role == "teacher" else parent_html
            try:
                resend.Emails.send({
                    "from": "StudyT2C <onboarding@resend.dev>",
                    "to": [to_addr],
                    "subject": subject,
                    "html": html,
                })
            except Exception:
                pass
        return True
    except Exception:
        return False


def send_offtopic_alert(
    to_emails: List[str],
    student_handle: str,
    offtopic_content: str,
    subject_prefix: str = "[StudyT2C]",
) -> bool:
    """
    (하위 호환) 이메일 주소만 있을 때 학부모 템플릿으로 발송.
    """
    recipients = [{"email": e, "role": "parent"} for e in to_emails if e and "@" in e]
    return send_offtopic_alert_to_recipients(recipients, student_handle, offtopic_content, subject_prefix)


def _render_focus_left_html(role: str, student_handle: str) -> str:
    """탭 이탈 알림 HTML (학부모/선생 공통 문구만 약간 다르게)."""
    if role == "teacher":
        return f"""
    <p>안녕하세요, 선생님. StudyT2C입니다.</p>
    <p>학생 <strong>{student_handle}</strong> 님이 학습 화면 탭을 벗어났습니다.</p>
    <p>다른 탭이나 창을 열었을 수 있습니다. 학생별 AI 분석 화면에서 <strong>집중 현황</strong>을 확인하실 수 있습니다.</p>
    <p>— StudyT2C</p>
    """
    return f"""
    <p>안녕하세요, 학부모님. StudyT2C입니다.</p>
    <p>자녀 <strong>{student_handle}</strong> 님이 학습 화면 탭을 벗어났습니다.</p>
    <p>다른 탭(예: 유튜브, 게임)이나 창을 열었을 수 있습니다. 학부모 화면의 <strong>AI 리포트 → 집중 현황</strong>에서 확인하실 수 있습니다.</p>
    <p>— StudyT2C</p>
    """


def send_focus_left_alert(
    recipients: List[Dict[str, Any]],
    student_handle: str,
    subject_prefix: str = "[StudyT2C]",
) -> bool:
    """탭 이탈 시 학부모/선생님에게 즉시 알림 이메일 발송. 실제로 1통이라도 발송되면 True."""
    if not recipients:
        return False
    api_key = _get_resend_api_key()
    if not api_key:
        return False
    sent_count = 0
    try:
        import resend
        resend.api_key = api_key
        subject = f"{subject_prefix} 학습 화면 탭을 벗어났어요"
        for r in recipients:
            to_addr = (r.get("email") or "").strip()
            if not to_addr or "@" not in to_addr:
                continue
            role = (r.get("role") or "parent").lower()
            html = _render_focus_left_html(role, student_handle)
            try:
                resend.Emails.send({
                    "from": "StudyT2C <onboarding@resend.dev>",
                    "to": [to_addr],
                    "subject": subject,
                    "html": html,
                })
                sent_count += 1
            except Exception:
                pass
        return sent_count > 0
    except Exception:
        return False


def send_focus_left_alert_with_reason(
    recipients: List[Dict[str, Any]],
    student_handle: str,
) -> tuple[bool, str]:
    """
    탭 이탈 알림 발송 후 (성공 여부, 사용자에게 보여줄 메시지) 반환.
    수동 발송 버튼에서 발송 결과·도착 예상 시간 안내용.
    """
    if not recipients:
        return False, "수신자가 없습니다. 이메일 알림 ON, 주기 실시간, 이메일 주소 저장 후 다시 시도해 주세요."
    if not _get_resend_api_key():
        return False, "발송 설정(RESEND_API_KEY)이 없어 메일을 보낼 수 없습니다. 관리자에게 문의해 주세요."
    ok = send_focus_left_alert(recipients, student_handle)
    if ok:
        return True, f"{len(recipients)}명에게 발송했습니다. 도착까지 보통 **10초~1분** 걸립니다. 스팸함도 확인해 주세요."
    return False, "Resend API 발송에 실패했습니다. 수신 이메일 주소와 API 키를 확인해 주세요."


def get_parent_emails_for_student(student_id: str) -> List[str]:
    """
    (하위 호환) 해당 학생과 연결된 학부모의 알림 이메일 목록만 반환.
    수신 설정 무시. 실시간 발송용은 get_offtopic_recipients_realtime 사용 권장.
    """
    from services.notification_settings_service import get_offtopic_recipients_realtime
    recs = get_offtopic_recipients_realtime(student_id)
    return [r["email"] for r in recs if r.get("role") == "parent"]
