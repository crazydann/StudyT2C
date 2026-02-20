# services/db/notes.py
from __future__ import annotations

from typing import Any, Dict

from services.db.base import DbServiceError, _now_iso, _sb


def get_teacher_student_note(teacher_user_id: str, student_user_id: str) -> str:
    try:
        sb = _sb()
        res = (
            sb.table("teacher_student_notes")
            .select("note")
            .eq("teacher_user_id", teacher_user_id)
            .eq("student_user_id", student_user_id)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            return ""
        return rows[0].get("note") or ""
    except Exception as e:
        raise DbServiceError(f"get_teacher_student_note failed: {e}")


def upsert_teacher_student_note(teacher_user_id: str, student_user_id: str, note: str) -> bool:
    try:
        sb = _sb()
        payload: Dict[str, Any] = {
            "teacher_user_id": teacher_user_id,
            "student_user_id": student_user_id,
            "note": note,
            "updated_at": _now_iso(),
        }
        try:
            sb.table("teacher_student_notes").upsert(
                payload, on_conflict="teacher_user_id,student_user_id"
            ).execute()
        except Exception:
            sb.table("teacher_student_notes").update(payload).eq("teacher_user_id", teacher_user_id).eq(
                "student_user_id", student_user_id
            ).execute()
        return True
    except Exception as e:
        raise DbServiceError(f"upsert_teacher_student_note failed: {e}")