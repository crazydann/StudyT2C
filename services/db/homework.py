# services/db/homework.py
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Sequence

from services.db.base import DbServiceError, _now_iso, _safe_gte, _safe_order, _sb


def list_homework_status_for_student(student_user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    """
    homework_assignments를 기반으로 숙제 목록 조회 (현재 프로젝트 구조에 맞춘 최소 구현)
    """
    try:
        sb = _sb()
        q = sb.table("homework_assignments").select("*").eq("student_user_id", student_user_id)
        # 스키마에 따라 due_date가 없을 수 있어 best-effort
        q = _safe_order(q, "due_date", desc=False)
        q = _safe_order(q, "created_at", desc=True)
        q = q.limit(limit)
        return q.execute().data or []
    except Exception as e:
        raise DbServiceError(f"list_homework_status_for_student failed: {e}")


def upsert_homework_non_submit_reason(student_user_id: str, assignment_id: str, reason_code: str) -> bool:
    """
    homework_non_submit_reasons:
      - unique(student_user_id, assignment_id) 가정
      - reason_code만 바뀌는 '덮어쓰기' 동작이 핵심
    """
    try:
        sb = _sb()
        payload = {
            "student_user_id": student_user_id,
            "assignment_id": assignment_id,
            "reason_code": reason_code,
        }

        # updated_at 컬럼이 있는 환경이면 같이 업데이트
        # (없으면 upsert/update에서 무시되거나 에러 날 수 있어 try로 분기)
        try:
            payload["updated_at"] = _now_iso()
        except Exception:
            pass

        # 1) 우선 upsert (정석)
        try:
            sb.table("homework_non_submit_reasons").upsert(
                payload, on_conflict="student_user_id,assignment_id"
            ).execute()
            return True
        except Exception:
            # 2) upsert 미지원/정책 문제 등 fallback: update -> 없으면 insert
            try:
                sb.table("homework_non_submit_reasons").update(payload) \
                    .eq("student_user_id", student_user_id) \
                    .eq("assignment_id", assignment_id) \
                    .execute()
                return True
            except Exception:
                sb.table("homework_non_submit_reasons").insert(payload).execute()
                return True

    except Exception as e:
        raise DbServiceError(f"upsert_homework_non_submit_reason failed: {e}")


def get_homework_non_submit_reason_map(
    student_user_id: str,
    assignment_ids: Optional[Sequence[str]] = None,
    lookback_days: int = 60,
    limit: int = 2000,
) -> Dict[str, Dict[str, Any]]:
    """
    ✅ UI가 기대하는 형태로 통일

    반환:
      key = assignment_id(str)
      value = row(dict)  (최소 'reason_code' 포함)

    사용 패턴:
      - get_homework_non_submit_reason_map(student_id, a_ids)  # 특정 숙제들만
      - get_homework_non_submit_reason_map(student_id)        # 전체(lookback 기반)
    """
    try:
        sb = _sb()
        since_iso = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()

        q = sb.table("homework_non_submit_reasons").select("*").eq("student_user_id", student_user_id).limit(limit)

        # assignment_ids 필터(있으면 UI 성능/정확도 개선)
        if assignment_ids:
            # supabase-py: in_ 사용
            q = q.in_("assignment_id", list(assignment_ids))

        # updated_at이 없을 수 있으니 best-effort로 필터/정렬
        q = _safe_gte(q, "updated_at", since_iso)
        q = _safe_order(q, "updated_at", desc=True)

        rows = q.execute().data or []
        out: Dict[str, Dict[str, Any]] = {}
        for r in rows:
            aid = str(r.get("assignment_id"))
            if not aid:
                continue

            # 어떤 버전은 code 컬럼명을 썼을 수도 있어 방어
            if "reason_code" not in r and "code" in r:
                r["reason_code"] = r.get("code")

            out[aid] = r

        return out

    except Exception as e:
        raise DbServiceError(f"get_homework_non_submit_reason_map failed: {e}")