from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from services.supabase_client import supabase

logger = logging.getLogger("studyt2c.review")


class ReviewServiceError(Exception):
    """복습 서비스 관련 에러를 명확히 표시하기 위한 예외."""


def record_review_attempt(student_id: str, problem_item_id: str, is_correct: bool) -> None:
    """
    복습 결과 기록:
    - next_review_at 업데이트 (맞음: 3일 후, 틀림: 1일 후)
    - attempts 테이블에 review 시도 기록
    """
    try:
        next_days = 3 if is_correct else 1
        next_review = (datetime.utcnow() + timedelta(days=next_days)).isoformat()

        supabase.table("problem_items").update({"next_review_at": next_review}).eq("id", problem_item_id).execute()

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