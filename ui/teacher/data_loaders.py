# ui/teacher/data_loaders.py
import json

from ui.ui_errors import show_error


def fetch_teacher_student_ids(supabase, teacher_id: str):
    try:
        rows = (
            supabase.table("teacher_student_links")
            .select("student_user_id")
            .eq("teacher_user_id", teacher_id)
            .execute()
            .data
            or []
        )
        return [r["student_user_id"] for r in rows if r.get("student_user_id")]
    except Exception as e:
        show_error("학생 연결 목록 로드 실패", e, context="teacher_student_links select", show_trace=False)
        return []


def fetch_teacher_notification_email(supabase, teacher_id: str) -> str:
    """선생님의 알림 수신 이메일 주소 조회."""
    try:
        resp = (
            supabase.table("users")
            .select("notification_email")
            .eq("id", teacher_id)
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


def update_teacher_notification_email(supabase, teacher_id: str, email: str) -> bool:
    """선생님의 알림 수신 이메일 주소 저장."""
    try:
        supabase.table("users").update({"notification_email": (email or "").strip() or None}).eq("id", teacher_id).execute()
        return True
    except Exception as e:
        show_error("알림 이메일 저장 실패", e, context="users update (notification_email)", show_trace=False)
        return False


def fetch_user_handles_by_ids(supabase, user_ids):
    if not user_ids:
        return {}
    try:
        rows = supabase.table("users").select("id, handle").in_("id", user_ids).execute().data or []
        return {r["id"]: (r.get("handle") or f"user-{r['id']}") for r in rows if r.get("id")}
    except Exception as e:
        show_error("학생 handle 로드 실패", e, context="users select (batch)", show_trace=False)
        return {uid: f"user-{uid}" for uid in user_ids}


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
    except Exception:
        try:
            return (
                supabase.table("homework_assignments")
                .select("id, title, description")
                .eq("student_user_id", student_id)
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


def fetch_teacher_consult_logs(supabase, teacher_id: str, student_id: str, limit: int = 10):
    try:
        rows = (
            supabase.table("teacher_consultation_logs")
            .select("id, teacher_user_id, student_user_id, one_liner, note, snapshot, created_at")
            .eq("teacher_user_id", teacher_id)
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
                .eq("teacher_user_id", teacher_id)
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


def insert_teacher_consult_log(supabase, teacher_id: str, student_id: str, one_liner: str, note: str, snapshot):
    payload = {
        "teacher_user_id": teacher_id,
        "student_user_id": student_id,
        "one_liner": (one_liner or "")[:400],
        "note": note or "",
        "snapshot": snapshot,
    }
    try:
        supabase.table("teacher_consultation_logs").insert(payload).execute()
        return True, None
    except Exception as e:
        return False, e


def safe_json(obj):
    try:
        return json.loads(json.dumps(obj, ensure_ascii=False, default=str))
    except Exception:
        return obj