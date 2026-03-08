import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pandas as pd

from services.supabase_client import supabase, supabase_service


def _execute_with_retry(fn, retries: int = 3, base_sleep: float = 0.6):
    last_err = None
    for i in range(retries):
        try:
            return fn()
        except Exception as e:
            last_err = e
            msg = str(e).lower()
            transient = any(
                k in msg
                for k in [
                    "server disconnected",
                    "connection reset",
                    "connection aborted",
                    "timed out",
                    "timeout",
                    "temporary failure",
                    "network is unreachable",
                    "connection refused",
                    "httpx",
                ]
            )
            if (i == retries - 1) or (not transient):
                raise
            time.sleep(base_sleep * (2 ** i))
    raise last_err


def _utc_now():
    return datetime.now(timezone.utc)


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


# ---------------------------
# Labels
# ---------------------------
_REASON_KO = {
    "concept": "개념 부족",
    "calculation": "계산 실수/계산 약함",
    "reading": "문제 해석/독해",
    "time": "시간 부족",
    "guessing": "찍음/감",
}

_NONSUBMIT_KO = {
    "time": "시간 부족",
    "hard": "어려워서 막힘",
    "forgot": "깜빡함",
}


# ---------------------------
# ✅ REQUIRED (student_dashboard imports this)
# ---------------------------
def get_student_learning_status(student_id: str) -> dict:
    """
    학생 대시보드에서 쓰는 가벼운 요약(기존 호환)
    - 채팅(튜터 질문) 수/과목 분포
    - 복습(다음 리뷰) 카운트(가능하면)
    - 오답 key_concepts 일부
    """
    chat_data = _execute_with_retry(
        lambda: supabase.table("chat_messages").select("subject").eq("student_user_id", student_id).execute()
    ).data or []

    # next_review_at / now() 비교는 DB/스키마 차이로 에러 날 수 있어서 방어적으로
    review_count = 0
    try:
        review_res = _execute_with_retry(
            lambda: supabase.table("problem_items")
            .select("id", count="exact")
            .eq("student_user_id", student_id)
            .lte("next_review_at", "now()")
            .execute()
        )
        review_count = review_res.count if getattr(review_res, "count", None) else 0
    except Exception:
        review_count = 0

    wrong_items = _execute_with_retry(
        lambda: supabase.table("problem_items")
        .select("key_concepts")
        .eq("student_user_id", student_id)
        .eq("is_correct", False)
        .limit(200)
        .execute()
    ).data or []

    subject_counts = {}
    if chat_data:
        df = pd.DataFrame(chat_data)
        if not df.empty and "subject" in df.columns:
            subject_counts = df["subject"].value_counts().to_dict()

    concepts = list(set([c for item in wrong_items for c in (item.get("key_concepts") or [])]))

    return {
        "chat_count": len(chat_data),
        "subject_counts": subject_counts,
        "review_count": review_count,
        "bookmarked_concepts": concepts[:5],
    }


# ---------------------------
# 오답 피드백 기반 학습 성향 요약
# ---------------------------
def get_student_learning_profile_summary(student_id: str, lookback_days: int = 14) -> Dict[str, Any]:
    since = _iso(_utc_now() - timedelta(days=lookback_days))

    rows = _execute_with_retry(
        lambda: supabase.table("problem_item_feedback")
        .select("understanding, reason_category, created_at")
        .eq("student_user_id", student_id)
        .gte("created_at", since)
        .order("created_at", desc=True)
        .limit(300)
        .execute()
    ).data or []

    if not rows:
        return {
            "lookback_days": lookback_days,
            "count": 0,
            "confused_rate": None,
            "reason_top": [],
        }

    total = len(rows)
    confused = len([r for r in rows if (r.get("understanding") or "confused") == "confused"])
    confused_rate = confused / total if total else None

    reason_counter = Counter()
    for r in rows:
        rc = r.get("reason_category")
        if rc:
            reason_counter[rc] += 1

    top = []
    for key, cnt in reason_counter.most_common(3):
        top.append({"code": key, "label": _REASON_KO.get(key, key), "count": int(cnt)})

    return {
        "lookback_days": lookback_days,
        "count": total,
        "confused_rate": confused_rate,
        "reason_top": top,
    }


# ---------------------------
# ✅ NEW: 미제출 사유 요약(학생별)
# ---------------------------
def get_student_non_submit_reason_summary(student_id: str, lookback_days: int = 14) -> Dict[str, Any]:
    since = _iso(_utc_now() - timedelta(days=lookback_days))

    rows = _execute_with_retry(
        lambda: supabase.table("homework_non_submit_reasons")
        .select("reason_code, created_at")
        .eq("student_user_id", student_id)
        .gte("created_at", since)
        .order("created_at", desc=True)
        .limit(300)
        .execute()
    ).data or []

    if not rows:
        return {"lookback_days": lookback_days, "count": 0, "top": []}

    total = len(rows)
    c = Counter()
    for r in rows:
        code = r.get("reason_code")
        if code:
            c[code] += 1

    top = []
    for code, cnt in c.most_common(3):
        top.append({"code": code, "label": _NONSUBMIT_KO.get(code, code), "count": int(cnt)})

    return {"lookback_days": lookback_days, "count": total, "top": top}


# ---------------------------
# 숙제/채점/오답 기존 요약
# ---------------------------
def _get_unsubmitted_homework_count(student_id: str, lookback_days: int = 14) -> int:
    since = _iso(_utc_now() - timedelta(days=lookback_days))

    assigns = _execute_with_retry(
        lambda: supabase.table("homework_assignments")
        .select("id, created_at")
        .eq("student_user_id", student_id)
        .gte("created_at", since)
        .execute()
    ).data or []

    if not assigns:
        return 0

    a_ids = [a["id"] for a in assigns if a.get("id")]
    if not a_ids:
        return 0

    subs = _execute_with_retry(
        lambda: supabase.table("homework_submissions")
        .select("assignment_id")
        .in_("assignment_id", a_ids)
        .execute()
    ).data or []

    submitted_ids = set([s.get("assignment_id") for s in subs if s.get("assignment_id")])
    return len([aid for aid in a_ids if aid not in submitted_ids])


def _get_homework_trend(student_id: str, lookback_days: int = 14) -> Dict[str, Any]:
    since_dt = _utc_now() - timedelta(days=lookback_days)
    since = _iso(since_dt)

    assigns = _execute_with_retry(
        lambda: supabase.table("homework_assignments")
        .select("id, created_at")
        .eq("student_user_id", student_id)
        .gte("created_at", since)
        .execute()
    ).data or []

    if not assigns:
        return {
            "lookback_days": lookback_days,
            "assigned_total": 0,
            "submitted_total": 0,
            "submission_rate": None,
            "daily": [],
        }

    a_ids = [a["id"] for a in assigns if a.get("id")]
    subs = _execute_with_retry(
        lambda: supabase.table("homework_submissions")
        .select("assignment_id, created_at")
        .in_("assignment_id", a_ids)
        .execute()
    ).data or []

    assigned_by_day = Counter()
    for a in assigns:
        day = (a.get("created_at") or "")[:10]
        if day:
            assigned_by_day[day] += 1

    submitted_by_day = Counter()
    submitted_ids = set()
    for s in subs:
        aid = s.get("assignment_id")
        if aid:
            submitted_ids.add(aid)
        day = (s.get("created_at") or "")[:10]
        if day:
            submitted_by_day[day] += 1

    assigned_total = len(a_ids)
    submitted_total = len(submitted_ids)
    submission_rate = (submitted_total / assigned_total) if assigned_total else None

    daily = []
    for i in range(lookback_days + 1):
        d = (since_dt + timedelta(days=i)).date().isoformat()
        daily.append(
            {"date": d, "assigned": int(assigned_by_day.get(d, 0)), "submitted": int(submitted_by_day.get(d, 0))}
        )

    return {
        "lookback_days": lookback_days,
        "assigned_total": assigned_total,
        "submitted_total": submitted_total,
        "submission_rate": submission_rate,
        "daily": daily,
    }


def _get_grading_trend(student_id: str, last_n: int = 6) -> Dict[str, Any]:
    subs = _execute_with_retry(
        lambda: supabase.table("problem_submissions")
        .select("id, created_at")
        .eq("student_user_id", student_id)
        .order("created_at", desc=True)
        .limit(last_n)
        .execute()
    ).data or []

    if not subs:
        return {"has_recent": False, "points": []}

    points = []
    for s in reversed(subs):
        sid = s.get("id")
        if not sid:
            continue
        items = _execute_with_retry(
            lambda: supabase.table("problem_items")
            .select("is_correct")
            .eq("submission_id", sid)
            .execute()
        ).data or []
        total = len(items)
        wrong = len([x for x in items if not bool(x.get("is_correct"))])
        rate = (wrong / total) if total else None
        points.append(
            {
                "submission_id": sid,
                "date": (s.get("created_at") or "")[:10],
                "total": total,
                "wrong": wrong,
                "wrong_rate": rate,
            }
        )

    return {"has_recent": True, "points": points}


def _get_top_wrong(student_id: str, top_k: int = 3) -> Dict[str, List[str]]:
    wrong_rows = _execute_with_retry(
        lambda: supabase.table("problem_items")
        .select("key_concepts, reason_category")
        .eq("student_user_id", student_id)
        .eq("is_correct", False)
        .limit(400)
        .execute()
    ).data or []

    concept_counter = Counter()
    reason_counter = Counter()

    for r in wrong_rows:
        for c in (r.get("key_concepts") or []):
            if c:
                concept_counter[c] += 1
        reason = r.get("reason_category")
        if reason:
            reason_counter[reason] += 1

    return {
        "top_wrong_concepts": [k for k, _ in concept_counter.most_common(top_k)],
        "top_wrong_reasons": [k for k, _ in reason_counter.most_common(top_k)],
    }


# ---------------------------
# 상담 스크립트 + 리포트
# ---------------------------
def _build_consult_script(summary: Dict[str, Any]) -> str:
    hw = summary.get("homework", {})
    gt = summary.get("grading_trend", {})
    top = summary.get("top_wrong", {})
    unsubmitted = summary.get("unsubmitted_homework_count", 0)
    profile = summary.get("learning_profile", {})
    ns = summary.get("non_submit_reasons", {})

    rate = hw.get("submission_rate")
    rate_str = f"{int(rate*100)}%" if isinstance(rate, (int, float)) else "데이터 부족"

    points = gt.get("points") or []
    if points and points[-1].get("wrong_rate") is not None:
        wr = points[-1]["wrong_rate"]
        wr_str = f"{int(wr*100)}%"
    else:
        wr_str = "데이터 부족"

    c = top.get("top_wrong_concepts") or []
    r = top.get("top_wrong_reasons") or []
    c_str = ", ".join(c) if c else "없음"
    r_str = ", ".join(r) if r else "없음"

    conf = profile.get("confused_rate")
    conf_str = f"{int(conf*100)}%" if isinstance(conf, (int, float)) else "N/A"
    rt = profile.get("reason_top") or []
    rt_str = ", ".join([x.get("label") for x in rt if x.get("label")]) if rt else "N/A"

    ns_top = ns.get("top") or []
    ns_str = ", ".join([f"{x.get('label')}({x.get('count')})" for x in ns_top]) if ns_top else "N/A"

    return (
        f"최근 {hw.get('lookback_days', 14)}일 기준 숙제 제출률은 {rate_str}이고, "
        f"미제출 숙제는 {unsubmitted}건입니다. "
        f"(학생 선택 기준) 미제출 사유 TOP은 [{ns_str}] 입니다. "
        f"최근 채점 기준 오답률은 {wr_str} 수준이며, "
        f"오답이 많이 나온 개념은 [{c_str}], 유형은 [{r_str}] 입니다. "
        f"(학생 체크 기준) 헷갈림 비율은 {conf_str}이고, 자주 선택한 오답 원인은 [{rt_str}] 입니다. "
        f"이 데이터를 기반으로 다음 수업/숙제에서 해당 약점을 집중 보완하도록 설계하고 있습니다."
    )


def get_student_consultation_report(student_id: str) -> Dict[str, Any]:
    homework = _get_homework_trend(student_id, lookback_days=14)
    unsubmitted = _get_unsubmitted_homework_count(student_id, lookback_days=14)
    grading_trend = _get_grading_trend(student_id, last_n=6)
    top_wrong = _get_top_wrong(student_id, top_k=3)

    learning_profile = get_student_learning_profile_summary(student_id, lookback_days=14)
    non_submit_reasons = get_student_non_submit_reason_summary(student_id, lookback_days=14)

    summary = {
        "homework": homework,
        "unsubmitted_homework_count": unsubmitted,
        "non_submit_reasons": non_submit_reasons,
        "grading_trend": grading_trend,
        "top_wrong": top_wrong,
        "learning_profile": learning_profile,
    }
    summary["consult_script"] = _build_consult_script(summary)
    return summary


# ---------------------------
# 반(클래스) 대시보드용 점수
# ---------------------------
def _risk_score(
    unsubmitted: int,
    submission_rate: Optional[float],
    latest_wrong_rate: Optional[float],
    confused_rate: Optional[float],
) -> float:
    score = 0.0

    score += min(40.0, float(unsubmitted) * 10.0)

    if submission_rate is None:
        score += 10.0
    else:
        score += (1.0 - submission_rate) * 30.0

    if latest_wrong_rate is None:
        score += 10.0
    else:
        score += latest_wrong_rate * 20.0

    if confused_rate is None:
        score += 0.0
    else:
        score += float(confused_rate) * 15.0

    return round(min(100.0, score), 1)


def get_class_dashboard_rows(student_ids: List[str]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for sid in student_ids:
        try:
            rep = get_student_consultation_report(sid)
        except Exception:
            rep = {
                "homework": {"assigned_total": 0, "submitted_total": 0, "submission_rate": None},
                "unsubmitted_homework_count": 0,
                "non_submit_reasons": {"count": 0, "top": []},
                "grading_trend": {"points": []},
                "top_wrong": {"top_wrong_concepts": [], "top_wrong_reasons": []},
                "learning_profile": {"confused_rate": None, "reason_top": [], "count": 0},
            }

        hw = rep.get("homework", {}) or {}
        gt = rep.get("grading_trend", {}) or {}
        top = rep.get("top_wrong", {}) or {}
        prof = rep.get("learning_profile", {}) or {}

        unsubmitted = int(rep.get("unsubmitted_homework_count") or 0)

        submission_rate = hw.get("submission_rate")
        if not isinstance(submission_rate, (int, float)):
            submission_rate = None
        else:
            submission_rate = float(submission_rate)

        points = gt.get("points") or []
        latest_wrong_rate = None
        if points:
            lr = points[-1].get("wrong_rate")
            if isinstance(lr, (int, float)):
                latest_wrong_rate = float(lr)

        top_concepts = top.get("top_wrong_concepts") or []
        top_reasons = top.get("top_wrong_reasons") or []

        conf = prof.get("confused_rate")
        if not isinstance(conf, (int, float)):
            conf = None
        else:
            conf = float(conf)

        rows.append(
            {
                "student_id": sid,
                "unsubmitted_14d": unsubmitted,
                "submission_rate_14d": submission_rate,
                "latest_wrong_rate": latest_wrong_rate,
                "top_concept": (top_concepts[0] if top_concepts else None),
                "top_reason": (top_reasons[0] if top_reasons else None),
                "confused_rate_14d": conf,
                "risk_score": _risk_score(unsubmitted, submission_rate, latest_wrong_rate, conf),
            }
        )

    rows.sort(key=lambda x: x.get("risk_score", 0), reverse=True)
    return rows


# ---------------------------
# 과목별 성취도 (MVP + 데모용)
# ---------------------------
_SUBJECT_LABELS = {
    "KOREAN": "국어",
    "ENGLISH": "영어",
    "MATH": "수학",
    "SCIENCE": "과학",
}


def get_subject_achievement(student_id: str, lookback_days: int = 30) -> Dict[str, Any]:
    """
    숙제, 채점, 질문 데이터를 종합한 과목별 성취도 개략치.
    - 실제 데이터가 부족하면 데모용 고정 값으로 채워준다.
    """
    subjects = list(_SUBJECT_LABELS.keys())

    since = _iso(_utc_now() - timedelta(days=lookback_days))

    # 1) 채점 데이터 기반 정답률
    try:
        rows = _execute_with_retry(
            lambda: supabase.table("problem_items")
            .select("subject_code,is_correct")
            .eq("student_user_id", student_id)
            .gte("created_at", since)
            .limit(800)
            .execute()
        ).data or []
    except Exception:
        rows = []

    by_sub_total = Counter()
    by_sub_wrong = Counter()
    for r in rows:
        code = (r.get("subject_code") or "").upper()
        if code not in subjects:
            continue
        by_sub_total[code] += 1
        if not bool(r.get("is_correct")):
            by_sub_wrong[code] += 1

    # 2) 질문 수 (chat_messages.subject)
    try:
        chats = _execute_with_retry(
            lambda: supabase.table("chat_messages")
            .select("subject")
            .eq("student_user_id", student_id)
            .gte("created_at", since)
            .execute()
        ).data or []
    except Exception:
        chats = []

    by_sub_q = Counter()
    for c in chats:
        code = (c.get("subject") or "").upper()
        if code in subjects:
            by_sub_q[code] += 1

    # 3) 점수 산출 (없으면 데모 값)
    data: List[Dict[str, Any]] = []
    for code in subjects:
        total = by_sub_total.get(code, 0)
        wrong = by_sub_wrong.get(code, 0)
        if total > 0:
            correct_rate = (total - wrong) / total
        else:
            correct_rate = None

        q_cnt = by_sub_q.get(code, 0)

        if correct_rate is None:
            # 데이터 부족: 데모용 기본값
            demo_scores = {"MATH": 0.88, "ENGLISH": 0.72, "KOREAN": 0.55, "SCIENCE": 0.68}
            correct_rate = demo_scores.get(code, 0.7)

        # 간단한 스코어: 정답률과 질문수(활동량)을 같이 반영
        score = int(correct_rate * 80 + min(q_cnt, 20) * 1)

        data.append(
            {
                "code": code,
                "label": _SUBJECT_LABELS.get(code, code.title()),
                "score": score,
                "correct_rate": correct_rate,
                "question_count": int(q_cnt),
            }
        )

    if not data:
        # 극단적으로 아무 데이터도 없을 때의 전체 데모
        data = [
            {"code": "MATH", "label": "수학", "score": 88, "correct_rate": 0.88, "question_count": 10},
            {"code": "ENGLISH", "label": "영어", "score": 72, "correct_rate": 0.72, "question_count": 8},
            {"code": "KOREAN", "label": "국어", "score": 55, "correct_rate": 0.55, "question_count": 5},
            {"code": "SCIENCE", "label": "과학", "score": 68, "correct_rate": 0.68, "question_count": 7},
        ]

    avg_score = sum(d["score"] for d in data) / len(data) if data else 0
    total_questions = sum(d["question_count"] for d in data)

    return {
        "lookback_days": lookback_days,
        "summary": {
            "avg_score": int(avg_score),
            "total_questions": int(total_questions),
            "avg_correct_rate": sum(d["correct_rate"] for d in data) / len(data) if data else None,
        },
        "subjects": data,
    }


# ---------------------------
# 과목별 취약 개념 (학생 대시보드 AI 취약점 카드용)
# ---------------------------
def get_subject_weak_concepts(student_id: str, lookback_days: int = 30, top_per_subject: int = 3) -> Dict[str, Any]:
    """
    오답 문항의 key_concepts를 과목별로 집계하여 취약 개념 리스트 반환.
    """
    since = _iso(_utc_now() - timedelta(days=lookback_days))
    try:
        rows = _execute_with_retry(
            lambda: supabase.table("problem_items")
            .select("subject_code, key_concepts")
            .eq("student_user_id", student_id)
            .eq("is_correct", False)
            .gte("created_at", since)
            .limit(500)
            .execute()
        ).data or []
    except Exception:
        rows = []

    by_subject: Dict[str, Counter] = {}
    for r in rows:
        code = (r.get("subject_code") or "OTHER").upper()
        if code not in _SUBJECT_LABELS:
            code = "MATH"  # fallback
        by_subject.setdefault(code, Counter())
        for c in (r.get("key_concepts") or []):
            if c and isinstance(c, str):
                by_subject[code][c.strip()] += 1

    weak_by_label: Dict[str, List[str]] = {}
    for code, cnt in by_subject.items():
        label = _SUBJECT_LABELS.get(code, code)
        weak_by_label[label] = [k for k, _ in cnt.most_common(top_per_subject)]

    if not weak_by_label:
        weak_by_label = {
            "수학": ["함수 그래프", "방정식", "기하"],
            "영어": ["관계대명사", "시제 일치", "전치사"],
            "국어": ["주술 호응", "문법", "독해"],
            "과학": ["화학반응", "힘과 운동", "생태계"],
        }

    return {"subjects": weak_by_label, "lookback_days": lookback_days}


# ---------------------------
# 반 전체 과목별 평균 성취도 (반 대시보드 그래프용)
# ---------------------------
def get_class_subject_achievement_aggregate(student_ids: List[str], lookback_days: int = 30) -> Dict[str, Any]:
    """
    반 전체 학생의 과목별 평균 성취도.
    """
    if not student_ids:
        return {"subjects": [], "lookback_days": lookback_days}

    agg: Dict[str, List[float]] = {}
    for sid in student_ids:
        try:
            data = get_subject_achievement(sid, lookback_days=lookback_days)
        except Exception:
            continue
        for s in data.get("subjects") or []:
            label = s.get("label") or "OTHER"
            score = s.get("score")
            if isinstance(score, (int, float)):
                agg.setdefault(label, []).append(float(score))

    subjects = []
    for label in _SUBJECT_LABELS.values():
        scores = agg.get(label, [])
        avg = sum(scores) / len(scores) if scores else 0
        subjects.append({"label": label, "avg_score": round(avg, 1), "count": len(scores)})

    return {"subjects": subjects, "lookback_days": lookback_days}


# ---------------------------
# 반 전체 주간 오답률/숙제 제출률 추이 (반 대시보드 그래프용)
# ---------------------------
def get_class_weekly_trends(student_ids: List[str], weeks: int = 4) -> Dict[str, Any]:
    """
    반 전체의 주간 오답률, 숙제 제출률 추이.
    consultation_report의 grading_trend points, homework daily를 주별로 집계.
    """
    if not student_ids:
        return {"weekly_wrong_rate": [], "weekly_submission_rate": [], "labels": [], "weeks": weeks}

    base_dt = _utc_now().date()
    wrong_by_week: Dict[str, List[float]] = {}
    submit_by_week: Dict[str, List[float]] = {}

    for w in range(weeks):
        week_start = base_dt - timedelta(weeks=weeks - w)
        week_label = week_start.isoformat()[:7] + f"-W{min(4, (week_start.day - 1) // 7 + 1)}"
        wrong_by_week[week_label] = []
        submit_by_week[week_label] = []

    for sid in student_ids:
        try:
            rep = get_student_consultation_report(sid)
        except Exception:
            continue
        gt = rep.get("grading_trend", {}) or {}
        hw = rep.get("homework", {}) or {}
        points = gt.get("points") or []
        daily = hw.get("daily") or []

        for p in points:
            d = (p.get("date") or "")[:10]
            if not d:
                continue
            try:
                dt = datetime.fromisoformat(d).date()
            except (ValueError, TypeError):
                continue
            week_start = dt - timedelta(days=dt.weekday())
            week_label = week_start.isoformat()
            if week_label in wrong_by_week:
                r = p.get("wrong_rate")
                if isinstance(r, (int, float)):
                    wrong_by_week[week_label].append(float(r))

        for day in daily:
            d = (day.get("date") or "")[:10]
            if not d:
                continue
            assigned = day.get("assigned", 0) or 0
            submitted = day.get("submitted", 0) or 0
            if assigned > 0:
                try:
                    dt = datetime.fromisoformat(d).date()
                except (ValueError, TypeError):
                    continue
                week_start = dt - timedelta(days=dt.weekday())
                week_label = week_start.isoformat()
                if week_label in submit_by_week:
                    submit_by_week[week_label].append(submitted / assigned)

    labels = []
    weekly_wrong: List[float] = []
    weekly_submit: List[float] = []

    for i in range(weeks):
        week_start = base_dt - timedelta(weeks=weeks - 1 - i)
        week_start = week_start - timedelta(days=week_start.weekday())
        week_label = week_start.isoformat()
        lb = f"{week_start.month}/{week_start.day}주"
        labels.append(lb)
        wr_list = wrong_by_week.get(week_label, [])
        sr_list = submit_by_week.get(week_label, [])
        weekly_wrong.append(sum(wr_list) / len(wr_list) if wr_list else 0.0)
        weekly_submit.append(sum(sr_list) / len(sr_list) if sr_list else 0.0)

    if not labels:
        labels = [f"W-{i+1}" for i in range(weeks)]

    return {
        "weekly_wrong_rate": weekly_wrong,
        "weekly_submission_rate": weekly_submit,
        "labels": labels,
        "weeks": weeks,
    }


# ---------------------------
# 공부 시간 중 비공부 질문 모니터링
# ---------------------------
def get_offtopic_chat_summary(student_id: str, lookback_days: int = 7) -> Dict[str, Any]:
    """
    - studying 모드 + is_study=False 인 chat_messages만 카운트.
    - 최근 예시 몇 개를 함께 반환.
    - service role 사용 → RLS policy 없이 조회 가능.
    """
    import json
    sb = supabase_service if supabase_service is not None else supabase
    since = _iso(_utc_now() - timedelta(days=lookback_days))
    try:
        rows = _execute_with_retry(
            lambda: sb.table("chat_messages")
            .select("created_at,content,meta")
            .eq("student_user_id", student_id)
            .gte("created_at", since)
            .execute()
        ).data or []
    except Exception:
        rows = []

    items: List[Dict[str, Any]] = []
    by_cat = Counter()

    for r in rows:
        raw_meta = r.get("meta")
        if raw_meta is None:
            continue
        if isinstance(raw_meta, str):
            try:
                meta = json.loads(raw_meta)
            except Exception:
                meta = {}
        else:
            meta = raw_meta or {}
        mode = meta.get("mode")
        is_study = meta.get("is_study")
        cat = meta.get("offtopic_category") or "OTHER"
        # studying 모드이면서 공부 외 질문 (False, 0, "false" 문자열 모두 비공부로 처리)
        is_offtopic = is_study is False or is_study == False or str(is_study).lower() == "false"
        if mode == "studying" and is_offtopic:
            by_cat[cat] += 1
            items.append(
                {
                    "created_at": r.get("created_at"),
                    "content": (r.get("content") or "")[:80],
                    "category": cat,
                }
            )

    items = sorted(items, key=lambda x: x.get("created_at") or "", reverse=True)
    total = len(items)

    return {
        "lookback_days": lookback_days,
        "total": total,
        "by_category": dict(by_cat),
        "items": items,
    }


# ---------------------------
# 공부 관련 질문/답변 이력 (학부모 탭용)
# ---------------------------
def get_study_chat_history(student_id: str, lookback_days: int = 30, limit: int = 50) -> Dict[str, Any]:
    """
    meta.is_study가 True인 chat_messages만 조회.
    질문·답변 쌍으로 반환 (공부 관련 이력 분석용).
    """
    import json
    sb = supabase_service if supabase_service is not None else supabase
    since = _iso(_utc_now() - timedelta(days=lookback_days))
    try:
        rows = _execute_with_retry(
            lambda: sb.table("chat_messages")
            .select("created_at,content,meta")
            .eq("student_user_id", student_id)
            .gte("created_at", since)
            .order("created_at", desc=True)
            .limit(limit * 2)
            .execute()
        ).data or []
    except Exception:
        rows = []

    items: List[Dict[str, Any]] = []
    for r in rows:
        raw_meta = r.get("meta")
        if raw_meta is None:
            continue
        if isinstance(raw_meta, str):
            try:
                meta = json.loads(raw_meta)
            except Exception:
                meta = {}
        else:
            meta = raw_meta or {}
        is_study = meta.get("is_study")
        if is_study is False or is_study == False or str(is_study).lower() == "false":
            continue
        if is_study is not True and is_study != True and str(is_study).lower() != "true":
            continue
        question = r.get("question_text") or r.get("content") or ""
        answer = r.get("answer_text") or meta.get("answer") or ""
        if not question.strip():
            continue
        items.append({
            "created_at": r.get("created_at"),
            "question": question[:200],
            "answer": (answer or "")[:500],
            "subject": meta.get("subject", "OTHER"),
        })

    items = sorted(items, key=lambda x: x.get("created_at") or "", reverse=True)[:limit]
    return {
        "lookback_days": lookback_days,
        "total": len(items),
        "items": items,
    }