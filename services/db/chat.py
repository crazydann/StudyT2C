# services/db/chat.py
from __future__ import annotations

from typing import Any, Dict, List, Optional

from services.db.base import DbServiceError, _now_iso, _safe_order, _sb


def save_chat_message(
    student_user_id: str,
    role: str,
    content: str,
    created_at: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> bool:
    """
    chat_messages 테이블 가정:
      - student_user_id
      - role
      - content
      - created_at
      - meta (optional jsonb)
    """
    try:
        sb = _sb()
        payload: Dict[str, Any] = {
            "student_user_id": student_user_id,
            "role": role,
            "content": content,
            "created_at": created_at or _now_iso(),
        }
        if meta is not None:
            payload["meta"] = meta
        sb.table("chat_messages").insert(payload).execute()
        return True
    except Exception as e:
        raise DbServiceError(f"save_chat_message failed: {e}")


def list_chat_messages(student_user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    try:
        sb = _sb()
        q = sb.table("chat_messages").select("*").eq("student_user_id", student_user_id)
        q = _safe_order(q, "created_at", desc=True).limit(limit)
        res = q.execute()
        rows = res.data or []
        return list(reversed(rows))
    except Exception as e:
        raise DbServiceError(f"list_chat_messages failed: {e}")