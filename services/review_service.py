from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

from services.supabase_client import supabase

logger = logging.getLogger("studyt2c.review")

# FSRS: 선택적 사용 (fsrs_state 컬럼 + 패키지 있으면 FSRS 기반 next_review_at)
try:
    from fsrs import Scheduler, Card, Rating
    _FSRS_AVAILABLE = True
except ImportError:
    _FSRS_AVAILABLE = False


class ReviewServiceError(Exception):
    """복습 서비스 관련 에러를 명확히 표시하기 위한 예외."""


def _next_review_fsrs(
    fsrs_state: Optional[Dict[str, Any]], is_correct: bool
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    FSRS로 다음 복습 시점 계산.
    반환: (next_review_iso, new_fsrs_state). state 없으면 새 카드로 간주.
    """
    if not _FSRS_AVAILABLE:
        days = 3 if is_correct else 1
        next_dt = datetime.now(timezone.utc) + timedelta(days=days)
        return next_dt.isoformat(), None

    try:
        scheduler = Scheduler()
        card = Card()
        if fsrs_state and isinstance(fsrs_state, dict):
            fields = getattr(Card, "model_fields", None) or set()
            if fields:
                card = Card(**{k: v for k, v in fsrs_state.items() if k in fields})
            else:
                for k, v in fsrs_state.items():
                    if hasattr(card, k):
                        setattr(card, k, v)

        rating = Rating.Good if is_correct else Rating.Again
        new_card, _ = scheduler.review_card(card, rating)

        due = new_card.due
        if hasattr(due, "isoformat"):
            next_iso = due.isoformat()
        else:
            next_iso = str(due)

        new_state = None
        if hasattr(new_card, "model_dump"):
            new_state = new_card.model_dump()
        elif hasattr(new_card, "__dict__"):
            new_state = {k: v for k, v in new_card.__dict__.items() if not k.startswith("_")}
        return next_iso, new_state
    except Exception as e:
        logger.warning("FSRS schedule fallback to 3/1 day: %s", e)
        days = 3 if is_correct else 1
        next_dt = datetime.now(timezone.utc) + timedelta(days=days)
        return next_dt.isoformat(), None


def record_review_attempt(student_id: str, problem_item_id: str, is_correct: bool) -> None:
    """
    복습 결과 기록:
    - next_review_at: FSRS 사용 가능 시 FSRS 기반, 아니면 맞음 3일/틀림 1일
    - attempts 테이블에 review 시도 기록
    """
    try:
        fsrs_state = None
        try:
            row = (
                supabase.table("problem_items")
                .select("id, fsrs_state")
                .eq("id", problem_item_id)
                .execute()
            )
            if row.data and len(row.data) > 0:
                fsrs_state = row.data[0].get("fsrs_state")
        except Exception:
            pass

        next_review, new_state = _next_review_fsrs(fsrs_state, is_correct)
        payload = {"next_review_at": next_review}
        if new_state is not None:
            payload["fsrs_state"] = new_state

        try:
            supabase.table("problem_items").update(payload).eq("id", problem_item_id).execute()
        except Exception as col_err:
            if "fsrs_state" in str(col_err).lower() or "column" in str(col_err).lower():
                supabase.table("problem_items").update({"next_review_at": next_review}).eq(
                    "id", problem_item_id
                ).execute()
            else:
                raise

        supabase.table("attempts").insert(
            {
                "student_user_id": student_id,
                "problem_item_id": problem_item_id,
                "is_correct": is_correct,
                "attempt_type": "review",
            }
        ).execute()

    except Exception as e:
        logger.exception(
            "record_review_attempt failed (student_id=%s, problem_item_id=%s): %s",
            student_id,
            problem_item_id,
            e,
        )
        raise ReviewServiceError(f"복습 결과 저장 실패: {e}")


def schedule_next_review(student_id: str, problem_item_id: str, days: int = 1) -> None:
    """
    ✅ 새로 추가:
    연습/채점 등에서 "오답"일 때 next_review_at만 갱신하고 싶을 때 사용.
    - attempts는 별도 기록하지 않음 (중복 방지)
    """
    try:
        days = max(0, int(days))
        next_review = (datetime.utcnow() + timedelta(days=days)).isoformat()
        supabase.table("problem_items").update({"next_review_at": next_review}).eq("id", problem_item_id).execute()
    except Exception as e:
        logger.exception(
            "schedule_next_review failed (student_id=%s, problem_item_id=%s, days=%s): %s",
            student_id,
            problem_item_id,
            days,
            e,
        )
        raise ReviewServiceError(f"복습 일정 갱신 실패: {e}")


def get_today_reviews(student_id: str) -> List[Dict[str, Any]]:
    """
    오늘 복습할 항목 조회:
    - next_review_at <= now(UTC)
    """
    try:
        now = datetime.utcnow().isoformat()
        res = (
            supabase.table("problem_items")
            .select("*")
            .eq("student_user_id", student_id)
            .lte("next_review_at", now)
            .order("next_review_at")
            .execute()
        )
        return res.data or []
    except Exception as e:
        logger.exception("get_today_reviews failed (student_id=%s): %s", student_id, e)
        return []