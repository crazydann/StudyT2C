# services/db/practice.py
from __future__ import annotations

from typing import Any, Dict, Optional

from services.db.base import DbServiceError, _now_iso, _sb


def save_practice_item(
    student_user_id: str,
    source_submission_id: str,
    source_item_no: int,
    question: str,
    answer_key: Optional[str] = None,
    explanation: Optional[str] = None,
) -> Dict[str, Any]:
    """
    practice_items 테이블 저장 (없으면 생성 필요)
    """
    try:
        sb = _sb()
        payload: Dict[str, Any] = {
            "student_user_id": student_user_id,
            "source_submission_id": source_submission_id,
            "source_item_no": int(source_item_no),
            "question": question,
            "answer_key": answer_key,
            "explanation": explanation,
            "created_at": _now_iso(),
        }
        res = sb.table("practice_items").insert(payload).select("*").execute()
        rows = res.data or []
        return rows[0] if rows else payload
    except Exception as e:
        raise DbServiceError(f"save_practice_item failed: {e}")


def update_practice_result(
    practice_item_id: str,
    student_user_id: str,
    submitted_answer: str,
    is_correct: Optional[bool] = None,
    feedback: Optional[str] = None,
) -> bool:
    """
    practice_results upsert
    """
    try:
        sb = _sb()
        payload: Dict[str, Any] = {
            "practice_item_id": practice_item_id,
            "student_user_id": student_user_id,
            "submitted_answer": submitted_answer,
            "is_correct": is_correct,
            "feedback": feedback,
            "updated_at": _now_iso(),
        }
        try:
            sb.table("practice_results").upsert(payload, on_conflict="practice_item_id,student_user_id").execute()
        except Exception:
            sb.table("practice_results").update(payload).eq("practice_item_id", practice_item_id).eq(
                "student_user_id", student_user_id
            ).execute()
        return True
    except Exception as e:
        raise DbServiceError(f"update_practice_result failed: {e}")