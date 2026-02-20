# services/db/feedback.py
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Sequence

from services.db.base import DbServiceError, _now_iso, _safe_gte, _safe_order, _sb


def upsert_problem_item_feedback(
    student_id: str,
    problem_item_id: str,
    submission_id: Optional[str] = None,
    understanding: str = "confused",          # "understood" | "confused"
    reason_category: Optional[str] = None,    # concept|calculation|reading|time|guessing|None
    memo: Optional[str] = None,
) -> bool:
    """
    problem_item_feedback 테이블(권장 스키마)
      - student_user_id (uuid)
      - problem_item_id (uuid)   ✅ 핵심
      - submission_id (uuid)     (optional)
      - understanding (text)     understood/confused
      - reason_category (text)   optional
      - memo (text)              optional
      - created_at (timestamptz) default now()
      - updated_at (timestamptz) optional

    unique(student_user_id, problem_item_id) 가정
    """
    try:
        sb = _sb()

        payload: Dict[str, Any] = {
            "student_user_id": student_id,
            "problem_item_id": str(problem_item_id),
            "understanding": understanding or "confused",
            "reason_category": reason_category,
            "memo": memo,
        }
        if submission_id:
            payload["submission_id"] = str(submission_id)

        # updated_at 컬럼이 없을 수도 있으니 best-effort
        try:
            payload["updated_at"] = _now_iso()
        except Exception:
            pass

        # 1) upsert 우선
        try:
            sb.table("problem_item_feedback").upsert(
                payload,
                on_conflict="student_user_id,problem_item_id",
            ).execute()
            return True
        except Exception:
            # 2) fallback: update -> 없으면 insert
            try:
                sb.table("problem_item_feedback").update(payload) \
                    .eq("student_user_id", student_id) \
                    .eq("problem_item_id", str(problem_item_id)) \
                    .execute()
                return True
            except Exception:
                sb.table("problem_item_feedback").insert(payload).execute()
                return True

    except Exception as e:
        raise DbServiceError(f"upsert_problem_item_feedback failed: {e}")


def get_problem_item_feedback_map(
    student_id: str,
    problem_item_ids: Optional[Sequence[str]] = None,
    lookback_days: int = 60,
    limit: int = 2000,
) -> Dict[str, Dict[str, Any]]:
    """
    ✅ UI(student_wrongnote)가 기대하는 형태로 통일

    반환:
      key = problem_item_id(str)
      value = row(dict)  (최소 understanding / reason_category 포함)

    사용:
      - get_problem_item_feedback_map(student_id, pids)
      - get_problem_item_feedback_map(student_id)  # 전체(lookback 기반)
    """
    try:
        sb = _sb()
        since_iso = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()

        q = sb.table("problem_item_feedback").select("*") \
            .eq("student_user_id", student_id) \
            .limit(limit)

        if problem_item_ids:
            q = q.in_("problem_item_id", list(problem_item_ids))

        # created_at / updated_at 둘 다 없을 수 있어 best-effort
        q = _safe_gte(q, "updated_at", since_iso)
        q = _safe_gte(q, "created_at", since_iso)
        q = _safe_order(q, "updated_at", desc=True)
        q = _safe_order(q, "created_at", desc=True)

        rows = q.execute().data or []
        out: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            pid = r.get("problem_item_id")
            if not pid:
                continue

            # 혹시 예전 컬럼명이 섞였던 경우 방어 (있으면 변환)
            if "reason_category" not in r and "reason_code" in r:
                r["reason_category"] = r.get("reason_code")
            if "understanding" not in r and "is_confused" in r:
                r["understanding"] = "confused" if r.get("is_confused") else "understood"

            out[str(pid)] = r

        return out

    except Exception as e:
        raise DbServiceError(f"get_problem_item_feedback_map failed: {e}")