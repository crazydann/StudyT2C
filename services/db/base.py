# services/db/base.py
from __future__ import annotations

from datetime import datetime, timezone


class DbServiceError(Exception):
    pass


def _sb(write: bool = False):
    """
    ✅ DB 클라이언트 선택:
    - read: anon
    - write: service role 있으면 service, 없으면 anon

    NOTE:
      write=True를 각 DB 함수에서 명시해야 실제로 service가 사용됨.
      실수 방지를 위해 _sbw()도 제공.
    """
    from services.supabase_client import supabase, supabase_service  # type: ignore

    if write and supabase_service is not None:
        return supabase_service
    return supabase


def _sbw():
    """
    ✅ write 전용 shortcut
    - service role 있으면 service
    - 없으면 anon
    """
    return _sb(write=True)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_order(query, column: str, desc: bool = True):
    try:
        return query.order(column, desc=desc)
    except Exception:
        return query


def _safe_gte(query, column: str, value: str):
    try:
        return query.gte(column, value)
    except Exception:
        return query