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
