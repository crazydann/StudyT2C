# services/db/grading.py
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional
import uuid
import re

from services.db.base import DbServiceError, _now_iso, _safe_gte, _safe_order, _sb, _sbw


def _exc_text(e: Exception) -> str:
    try:
        return str(e) or repr(e)
    except Exception:
        return repr(e)


_COL_MISSING_RE = re.compile(r"Could not find the '([^']+)' column", re.IGNORECASE)


def _strip_missing_column_from_payload(payload: Dict[str, Any], err_text: str) -> Dict[str, Any]:
    """
    PostgREST PGRST204: "Could not find the 'xxx' column ..." 이면
    payload에서 xxx 키를 제거하고 재시도할 수 있게 한다.
    """
    m = _COL_MISSING_RE.search(err_text or "")
    if not m:
        return payload
    col = m.group(1)
    if col in payload:
        p2 = dict(payload)
        p2.pop(col, None)
        return p2
    return payload


# ---------------------------
# Read helpers
# ---------------------------
def check_cached_submission(student_user_id: str, file_hash: str) -> Optional[Dict[str, Any]]:
    """
    problem_submissions: (student_user_id, file_hash) unique 가정
    """
    try:
        sb = _sb(write=False)
        res = (
            sb.table("problem_submissions")
            .select("*")
            .eq("student_user_id", student_user_id)
            .eq("file_hash", file_hash)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None
    except Exception as e:
        raise DbServiceError(f"check_cached_submission failed: {_exc_text(e)}")


def _get_submission_by_id_service(submission_id: str) -> Optional[Dict[str, Any]]:
    """
    ✅ 존재 여부 확인은 service role로 (RLS 영향 제거)
    """
    try:
        sbw = _sbw()
        res = sbw.table("problem_submissions").select("*").eq("id", submission_id).limit(1).execute()
        rows = res.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def _get_submission_by_unique_service(student_user_id: str, file_hash: str) -> Optional[Dict[str, Any]]:
    try:
        sbw = _sbw()
        res = (
            sbw.table("problem_submissions")
            .select("*")
            .eq("student_user_id", student_user_id)
            .eq("file_hash", file_hash)
            .limit(1)
            .execute()
        )
        rows = res.data or []
        return rows[0] if rows else None
    except Exception:
        return None


def _ensure_submission_exists_or_raise(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    ✅ FK 깨지지 않도록 "DB에 실제 row 존재"를 강제
    """
    sid = str(payload.get("id") or "")
    if sid:
        got = _get_submission_by_id_service(sid)
        if got:
            return got

    got2 = _get_submission_by_unique_service(str(payload.get("student_user_id")), str(payload.get("file_hash")))
    if got2:
        return got2

    raise DbServiceError(
        "problem_submissions row를 DB에서 확인할 수 없습니다. "
        "upsert/update가 0 rows였거나 insert가 실패했을 가능성이 큽니다."
    )


# ---------------------------
# Write: problem_submissions upsert
# ---------------------------
def _try_upsert_problem_submission(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    ✅ write는 service role 우선(_sbw)
    ✅ upsert가 rows를 반환하지 않는 환경도 있으므로, service로 재조회까지 강제
    ✅ update fallback은 '0 rows'일 수 있으므로 존재 확인 후 없으면 insert로 간다
    ✅ 컬럼 미존재(PGRST204)면 해당 컬럼을 payload에서 제거하며 재시도
    """
    sbw = _sbw()

    # --- 1) upsert (column strip retry 포함) ---
    up_payload = dict(payload)
    for _ in range(5):
        try:
            res = (
                sbw.table("problem_submissions")
                .upsert(up_payload, on_conflict="student_user_id,file_hash")
                .select("*")
                .execute()
            )
            rows = res.data or []
            if rows:
                return rows[0]
            # rows가 비면 service로 존재 확인
            return _ensure_submission_exists_or_raise(up_payload)
        except Exception as e:
            msg = _exc_text(e)
            # 스키마에 없는 컬럼이면 제거 후 retry
            new_payload = _strip_missing_column_from_payload(up_payload, msg)
            if new_payload is not up_payload:
                up_payload = new_payload
                continue
            # updated_at 등 없는 환경도 여기에 걸릴 수 있음
            if "updated_at" in up_payload and ("updated_at" in msg and "does not exist" in msg):
                up_payload.pop("updated_at", None)
                continue
            # 다른 에러면 upsert 단계 종료 → fallback update/insert 시도
            break

    # --- 2) fallback update (0 rows 가능) ---
    upd_payload = dict(up_payload)
    for _ in range(5):
        try:
            sbw.table("problem_submissions").update(upd_payload) \
                .eq("student_user_id", upd_payload.get("student_user_id")) \
                .eq("file_hash", upd_payload.get("file_hash")) \
                .execute()

            # ✅ update 후 실제 존재 확인 (없으면 insert로)
            try:
                return _ensure_submission_exists_or_raise(upd_payload)
            except Exception:
                # update가 0 rows였던 케이스 → insert로 계속 진행
                break

        except Exception as e:
            msg = _exc_text(e)
            new_payload = _strip_missing_column_from_payload(upd_payload, msg)
            if new_payload is not upd_payload:
                upd_payload = new_payload
                continue
            break

    # --- 3) fallback insert ---
    ins_payload = dict(upd_payload)
    for _ in range(5):
        try:
            sbw.table("problem_submissions").insert(ins_payload).execute()
            return _ensure_submission_exists_or_raise(ins_payload)
        except Exception as e:
            msg = _exc_text(e)
            new_payload = _strip_missing_column_from_payload(ins_payload, msg)
            if new_payload is not ins_payload:
                ins_payload = new_payload
                continue
            raise DbServiceError(f"problem_submissions insert failed: {msg}")

    # 이론상 도달 X
    return _ensure_submission_exists_or_raise(ins_payload)


def upsert_problem_submission(
    student_user_id: str,
    file_hash: str,
    file_name: str,
    storage_path: str,
    storage_url: Optional[str] = None,
    status: str = "created",
    submission_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    ✅ 항상 submission_id를 확보 (UUID 선발급)
    ✅ write는 service role 우선
    ✅ 중요한 점: "DB에 실제 row 존재"를 보장하고 반환 (FK 안전)
    """
    try:
        sid = submission_id or str(uuid.uuid4())

        # ⚠️ 스키마에 없는 컬럼이 있을 수 있으니 여기서도 보수적으로 넣고,
        #     _try_upsert에서 PGRST204면 자동 제거됨.
        payload: Dict[str, Any] = {
            "id": sid,
            "student_user_id": student_user_id,
            "file_hash": file_hash,
            "file_name": file_name,        # ← 스키마에 없을 수 있음 (자동 제거됨)
            "storage_path": storage_path,
            "storage_url": storage_url,    # ← 없을 수 있음 (자동 제거됨)
            "status": status,              # ← 없을 수 있음 (자동 제거됨)
            "updated_at": _now_iso(),      # ← 없을 수 있음 (자동 제거됨)
        }
        # None 값은 insert에서 문제될 수 있어 제거
        payload = {k: v for k, v in payload.items() if v is not None}

        row = _try_upsert_problem_submission(payload)

        # 반환에도 id는 보장
        if not row.get("id"):
            row["id"] = sid
        return row

    except DbServiceError:
        raise
    except Exception as e:
        raise DbServiceError(f"upsert_problem_submission failed: {_exc_text(e)}")


# ---------------------------
# Read: submissions list/items/stats
# ---------------------------
def list_grading_submissions(student_user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    try:
        sb = _sb(write=False)
        base = sb.table("problem_submissions").select("*").eq("student_user_id", student_user_id)

        try:
            return base.order("uploaded_at", desc=True).limit(limit).execute().data or []
        except Exception:
            pass
        try:
            return base.order("created_at", desc=True).limit(limit).execute().data or []
        except Exception:
            pass
        return base.order("id", desc=True).limit(limit).execute().data or []
    except Exception as e:
        raise DbServiceError(f"list_grading_submissions failed: {_exc_text(e)}")


def get_submission_items(submission_id: str, limit: int = 200) -> List[Dict[str, Any]]:
    try:
        sb = _sb(write=False)
        q = sb.table("problem_items").select("*").eq("submission_id", submission_id)
        q = _safe_order(q, "item_no", desc=False).limit(limit)
        return q.execute().data or []
    except Exception as e:
        raise DbServiceError(f"get_submission_items failed: {_exc_text(e)}")


def _get_stats_for_submission(submission_id: str) -> Dict[str, Any]:
    items = get_submission_items(str(submission_id), limit=500)
    total = len(items)
    wrong = sum(1 for it in items if it.get("is_correct") is False)
    wrong_rate = (wrong / total) if total else None
    return {"submission_id": submission_id, "total": total, "wrong": wrong, "wrong_rate": wrong_rate}


def _submission_exists(submission_id: str) -> bool:
    try:
        sb = _sb(write=False)
        rows = sb.table("problem_submissions").select("id").eq("id", submission_id).limit(1).execute().data or []
        return bool(rows)
    except Exception:
        return False


def get_submission_stats(arg: str, lookback_days: int = 14) -> Dict[str, Any]:
    """
    - arg가 submission_id면 1건 stats
    - 아니면 student_user_id로 간주하고 최신 제출 stats
    """
    try:
        if arg and _submission_exists(arg):
            return _get_stats_for_submission(arg)

        sb = _sb(write=False)
        since_iso = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()
        base = sb.table("problem_submissions").select("id,created_at,uploaded_at").eq("student_user_id", arg)

        subs: List[Dict[str, Any]] = []
        latest_submission_id = None

        try:
            subs = base.gte("uploaded_at", since_iso).order("uploaded_at", desc=True).limit(200).execute().data or []
        except Exception:
            subs = []

        if not subs:
            try:
                subs = base.gte("created_at", since_iso).order("created_at", desc=True).limit(200).execute().data or []
            except Exception:
                subs = []

        if not subs:
            try:
                subs = base.order("uploaded_at", desc=True).limit(200).execute().data or []
            except Exception:
                subs = []
        if not subs:
            try:
                subs = base.order("created_at", desc=True).limit(200).execute().data or []
            except Exception:
                subs = []

        if subs:
            latest_submission_id = subs[0].get("id")

        latest_total = 0
        latest_wrong = 0
        latest_wrong_rate = None

        if latest_submission_id:
            st1 = _get_stats_for_submission(str(latest_submission_id))
            latest_total = st1["total"]
            latest_wrong = st1["wrong"]
            latest_wrong_rate = st1["wrong_rate"]

        return {
            "lookback_days": lookback_days,
            "submission_count": len(subs),
            "latest_submission_id": latest_submission_id,
            "latest_total": latest_total,
            "latest_wrong": latest_wrong,
            "latest_wrong_rate": latest_wrong_rate,
        }
    except Exception as e:
        raise DbServiceError(f"get_submission_stats failed: {_exc_text(e)}")


# ---------------------------
# Write: problem_items upsert
# ---------------------------
def save_grading_results(submission_id: str, student_user_id: str, items: List[Dict[str, Any]]) -> int:
    """
    ✅ write는 service role 우선(_sbw)
    ✅ created_at 컬럼 없을 수 있어서 2-pass
    ✅ FK 보호를 위해, 시작 전에 submission 존재를 service로 한번 확인
    """
    try:
        if not items:
            return 0

        # ✅ FK 안전: submission 존재 확인
        if not _get_submission_by_id_service(str(submission_id)):
            raise DbServiceError(
                f"problem_items 저장 전 확인 실패: submission_id({submission_id}) row가 problem_submissions에 없습니다. "
                "→ submissions upsert가 실제로 insert되지 않았습니다."
            )

        sbw = _sbw()

        payloads_with_created: List[Dict[str, Any]] = []
        payloads_no_created: List[Dict[str, Any]] = []

        for it in items:
            base = {
                "submission_id": submission_id,
                "student_user_id": student_user_id,
                "item_no": int(it.get("item_no", 0) or 0),
                "extracted_question_text": it.get("extracted_question_text") or it.get("question") or "",
                "is_correct": it.get("is_correct"),
                "explanation_summary": it.get("explanation_summary") or "",
                "explanation_detail": it.get("explanation_detail") or "",
                "key_concepts": it.get("key_concepts") or [],
                "reason_category": it.get("reason_category"),
                "next_review_at": it.get("next_review_at"),
            }
            with_created = dict(base)
            with_created["created_at"] = _now_iso()

            payloads_with_created.append(with_created)
            payloads_no_created.append(base)

        # 1) created_at 포함 upsert
        try:
            sbw.table("problem_items").upsert(payloads_with_created, on_conflict="submission_id,item_no").execute()
            return len(payloads_with_created)
        except Exception as e1:
            msg1 = _exc_text(e1)

            # created_at 없는 환경
            if "created_at" in msg1 and "does not exist" in msg1:
                try:
                    sbw.table("problem_items").upsert(payloads_no_created, on_conflict="submission_id,item_no").execute()
                    return len(payloads_no_created)
                except Exception as e2:
                    try:
                        sbw.table("problem_items").insert(payloads_no_created).execute()
                        return len(payloads_no_created)
                    except Exception as e3:
                        raise DbServiceError(f"problem_items save failed (no created_at path): {_exc_text(e3)}") from e2

            # 그 외 upsert 실패 → insert fallback
            try:
                sbw.table("problem_items").insert(payloads_with_created).execute()
                return len(payloads_with_created)
            except Exception:
                sbw.table("problem_items").insert(payloads_no_created).execute()
                return len(payloads_no_created)

    except DbServiceError:
        raise
    except Exception as e:
        raise DbServiceError(f"save_grading_results failed: {_exc_text(e)}")