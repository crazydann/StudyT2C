# services/concept_review_service.py
"""
질의개념복습 풀이 이력 저장·통계·취약점 분석용 조회.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from services.supabase_client import supabase_service, supabase


def _sb():
    return supabase_service if supabase_service is not None else supabase


def save_attempt(
    student_user_id: str,
    source_question: str,
    source_answer: str,
    quiz_question: str,
    correct_index: int,
    user_choice_index: int,
) -> bool:
    is_correct = correct_index == user_choice_index
    try:
        _sb().table("concept_review_attempts").insert({
            "student_user_id": student_user_id,
            "source_question": (source_question or "")[:1000],
            "source_answer": (source_answer or "")[:2000],
            "quiz_question": (quiz_question or "")[:1000],
            "correct_index": correct_index,
            "user_choice_index": user_choice_index,
            "is_correct": is_correct,
        }).execute()
        return True
    except Exception:
        return False


def get_concept_review_stats(student_id: str, lookback_days: int = 90) -> Dict[str, Any]:
    """
    질의개념복습 통계: 총 풀이 수, 정답 수, 오답 수, 정답률.
    """
    since = (datetime.now(timezone.utc) - timedelta(days=lookback_days)).isoformat()
    try:
        rows = (
            _sb()
            .table("concept_review_attempts")
            .select("is_correct")
            .eq("student_user_id", student_id)
            .gte("created_at", since)
            .execute()
            .data
            or []
        )
    except Exception:
        rows = []
    total = len(rows)
    correct = sum(1 for r in rows if r.get("is_correct") is True)
    wrong = total - correct
    accuracy_pct = (correct / total * 100) if total else 0
    return {
        "total": total,
        "correct": correct,
        "wrong": wrong,
        "accuracy_pct": round(accuracy_pct, 1),
    }


def get_concept_review_wrong_items(student_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    """오답만 최근순으로 (AI 취약점 분석용)."""
    try:
        rows = (
            _sb()
            .table("concept_review_attempts")
            .select("source_question, source_answer, quiz_question, correct_index, user_choice_index, created_at")
            .eq("student_user_id", student_id)
            .eq("is_correct", False)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
        return rows
    except Exception:
        return []


def get_concept_review_recent_all(student_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """최근 풀이 전체 (정답/오답 포함, AI가 전체 맥락 보려고)."""
    try:
        rows = (
            _sb()
            .table("concept_review_attempts")
            .select("source_question, source_answer, quiz_question, correct_index, user_choice_index, is_correct, created_at")
            .eq("student_user_id", student_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
        return rows
    except Exception:
        return []


def get_concept_review_daily_stats(student_id: str, days: int = 7) -> List[Dict[str, Any]]:
    """
    최근 N일(기본 7일) 동안의 일별 복습 퀴즈 통계.
    각 항목: {"date": "YYYY-MM-DD", "total": int, "correct": int, "wrong": int, "accuracy_pct": float}
    """
    if days <= 0:
        return []

    since = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    try:
        rows = (
            _sb()
            .table("concept_review_attempts")
            .select("is_correct, created_at")
            .eq("student_user_id", student_id)
            .gte("created_at", since)
            .order("created_at", desc=True)
            .execute()
            .data
            or []
        )
    except Exception:
        rows = []

    # created_at(UTC) 기준으로 날짜 단위 집계
    buckets: Dict[str, Dict[str, Any]] = {}
    for r in rows:
        ts_raw = r.get("created_at")
        try:
            # Supabase는 ISO 형식 문자열로 반환. timezone-aware 로 파싱.
            dt = datetime.fromisoformat(ts_raw.replace("Z", "+00:00")) if isinstance(ts_raw, str) else ts_raw
        except Exception:
            continue
        if not isinstance(dt, datetime):
            continue
        date_key = dt.date().isoformat()
        if date_key not in buckets:
            buckets[date_key] = {"date": date_key, "total": 0, "correct": 0, "wrong": 0}
        buckets[date_key]["total"] += 1
        if r.get("is_correct") is True:
            buckets[date_key]["correct"] += 1
        else:
            buckets[date_key]["wrong"] += 1

    # 날짜 오름차순 정렬 + 정답률 계산
    result: List[Dict[str, Any]] = []
    for date_key in sorted(buckets.keys()):
        item = buckets[date_key]
        total = item["total"]
        correct = item["correct"]
        wrong = item["wrong"]
        acc = (correct / total * 100) if total else 0
        result.append(
            {
                "date": date_key,
                "total": total,
                "correct": correct,
                "wrong": wrong,
                "accuracy_pct": round(acc, 1),
            }
        )
    return result


# ---------------------------
# concept_review_quizzes: 만든 문제 저장 (지난 문제들·재풀이)
# ---------------------------
def save_quiz(
    student_user_id: str,
    source_question: str,
    source_answer: str,
    quiz_question: str,
    options: List[str],
    correct_index: int,
) -> Optional[str]:
    """만든 문제 1건 저장. 반환: id, 실패 시 None."""
    try:
        row = (
            _sb()
            .table("concept_review_quizzes")
            .insert({
                "student_user_id": student_user_id,
                "source_question": (source_question or "")[:1000],
                "source_answer": (source_answer or "")[:2000],
                "quiz_question": (quiz_question or "")[:1000],
                "options": options or [],
                "correct_index": correct_index,
            })
            .execute()
        )
        data = (row.data or []) if hasattr(row, "data") else []
        if data and isinstance(data, list) and len(data) > 0:
            return data[0].get("id")
        return None
    except Exception:
        return None


def list_quizzes(student_user_id: str, limit: int = 30) -> List[Dict[str, Any]]:
    """지난 문제들: 최근 생성된 퀴즈 목록 (재풀이용)."""
    try:
        rows = (
            _sb()
            .table("concept_review_quizzes")
            .select("id, source_question, source_answer, quiz_question, options, correct_index, created_at")
            .eq("student_user_id", student_user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
            .data
            or []
        )
        return rows
    except Exception:
        return []


def get_quiz_by_id(quiz_id: str) -> Optional[Dict[str, Any]]:
    """퀴즈 1건 조회 (재풀이 팝업용)."""
    try:
        rows = (
            _sb()
            .table("concept_review_quizzes")
            .select("id, source_question, source_answer, quiz_question, options, correct_index, created_at")
            .eq("id", quiz_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if rows:
            return rows[0]
        return None
    except Exception:
        return None
