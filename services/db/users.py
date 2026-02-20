# services/db/users.py
from __future__ import annotations

from typing import Any, Dict, List

from services.db.base import DbServiceError, _sb


def list_users_by_role(role: str) -> List[Dict[str, Any]]:
    try:
        sb = _sb()
        res = sb.table("users").select("*").eq("role", role).execute()
        return res.data or []
    except Exception as e:
        raise DbServiceError(f"list_users_by_role failed: {e}")