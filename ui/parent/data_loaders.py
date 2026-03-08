# ui/parent/data_loaders.py
from ui.ui_errors import show_error


def fetch_children_ids(supabase, parent_id: str):
    try:
        resp = (
            supabase.table("parent_student_links")
            .select("student_user_id")
            .eq("parent_user_id", parent_id)
            .execute()
        )
        rows = resp.data or []
        return [r["student_user_id"] for r in rows if r.get("student_user_id")]
    except Exception as e:
        show_error("자녀 링크 로드 실패", e, context="parent_student_links select", show_trace=False)
        return []


def fetch_user_handles_by_ids(supabase, user_ids):
    if not user_ids:
        return {}
    try:
        resp = supabase.table("users").select("id, handle").in_("id", user_ids).execute()
        rows = resp.data or []
        return {r["id"]: (r.get("handle") or f"user-{r['id']}") for r in rows if r.get("id")}
    except Exception as e:
        show_error("학생 handle 로드 실패", e, context="users select (batch)", show_trace=False)
        return {uid: f"user-{uid}" for uid in user_ids}


def fetch_student_status(supabase, student_id: str) -> str:
    """
    자녀의 현재 status(예: studying/break)를 users 테이블에서 조회.
    실패 시 기본값 'break' 반환.
    """
    try:
        resp = (
            supabase.table("users")
            .select("status")
            .eq("id", student_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return "break"
        return (rows[0].get("status") or "break").strip() or "break"
    except Exception as e:
        show_error("학생 AI 모드 로드 실패", e, context="users select (status)", show_trace=False)
        return "break"


def update_student_status(supabase, student_id: str, status: str) -> bool:
    """
    자녀의 status 값을 업데이트하여 AI 튜터 모드에 반영.
    """
    try:
        supabase.table("users").update({"status": status}).eq("id", student_id).execute()
        return True
    except Exception as e:
        show_error("학생 AI 모드 저장 실패", e, context="users update (status)", show_trace=False)
        return False


def fetch_parent_notification_email(supabase, parent_id: str) -> str:
    """
    학부모(현재 로그인 사용자)의 알림 수신 이메일 주소 조회.
    """
    try:
        resp = (
            supabase.table("users")
            .select("notification_email")
            .eq("id", parent_id)
            .limit(1)
            .execute()
        )
        rows = resp.data or []
        if not rows:
            return ""
        return (rows[0].get("notification_email") or "").strip()
    except Exception as e:
        show_error("알림 이메일 로드 실패", e, context="users select (notification_email)", show_trace=False)
        return ""


def update_parent_notification_email(supabase, parent_id: str, email: str) -> bool:
    """
    학부모의 알림 수신 이메일 주소 저장. 공부 외 질문 발생 시 해당 주소로 이메일 발송.
    """
    try:
        supabase.table("users").update({"notification_email": (email or "").strip() or None}).eq("id", parent_id).execute()
        return True
    except Exception as e:
        show_error("알림 이메일 저장 실패", e, context="users update (notification_email)", show_trace=False)
        return False


def fetch_homework_assignments(supabase, student_id: str, limit: int = 30):
    try:
        return (
            supabase.table("homework_assignments")
            .select("id, title, description, created_at")
            .eq("student_user_id", student_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
    except Exception as e:
        show_error("숙제 목록 로드 실패", e, context="homework_assignments select", show_trace=False)
        return []


def fetch_latest_homework_submission(supabase, assignment_id: str):
    try:
        rows = (
            supabase.table("homework_submissions")
            .select("id, storage_path, created_at")
            .eq("assignment_id", assignment_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
            .data
            or []
        )
        return rows[0] if rows else None
    except Exception:
        try:
            rows = (
                supabase.table("homework_submissions")
                .select("id, storage_path")
                .eq("assignment_id", assignment_id)
                .limit(1)
                .execute()
                .data
                or []
            )
            return rows[0] if rows else None
        except Exception:
            return None


def fetch_teacher_consult_logs_for_student(supabase, student_id: str, limit: int = 5):
    """
    teacher_consultation_logs에서 최근 상담 로그 N개 로드.
    created_at이 있는 경우 정렬, 없으면 limit만.
    """
    try:
        rows = (
            supabase.table("teacher_consultation_logs")
            .select("id, teacher_user_id, student_user_id, one_liner, note, snapshot, created_at")
            .eq("student_user_id", student_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
        return rows
    except Exception:
        try:
            rows = (
                supabase.table("teacher_consultation_logs")
                .select("id, teacher_user_id, student_user_id, one_liner, note, snapshot")
                .eq("student_user_id", student_id)
                .limit(limit)
                .execute()
                .data
                or []
            )
            return rows
        except Exception as e:
            show_error("상담 로그 로드 실패", e, context="teacher_consultation_logs select", show_trace=False)
            return []