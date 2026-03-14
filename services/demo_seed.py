from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Any, List, Tuple

from services.supabase_client import get_supabase_anon, get_supabase_service


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _get_client():
    """
    데모 데이터는 쓰기 권한이 필요하므로 가능하면 service role 클라이언트를 사용.
    없을 경우 anon 클라이언트로 fallback (RLS 설정에 따라 실패할 수 있음).
    """
    svc = get_supabase_service()
    if svc is not None:
        return svc
    return get_supabase_anon()


def seed_demo_basic() -> Dict[str, Any]:
    """
    간단한 데모용 데이터 세트:
    - teacher_demo / student_demo / parent_demo 유저 1명씩
    - teacher_student_links / parent_student_links 연결
    - 최근 숙제 2개 + 제출 1개
    이 함수는 idempotent 하지는 않지만, 여러 번 눌러도 큰 문제 없이 비슷한 데이터가 누적되도록 설계.
    """
    now = _utc_now()
    supabase = _get_client()

    # 1) 유저 생성
    teacher = (
        supabase.table("users")
        .insert(
            {
                "handle": f"teacher_demo_{now.strftime('%H%M%S')}",
                "role": "teacher",
                "status": "studying",
            }
        )
        .execute()
        .data[0]
    )

    student = (
        supabase.table("users")
        .insert(
            {
                "handle": f"student_demo_{now.strftime('%H%M%S')}",
                "role": "student",
                "status": "studying",
                "detail_permission": True,
            }
        )
        .execute()
        .data[0]
    )

    parent = (
        supabase.table("users")
        .insert(
            {
                "handle": f"parent_demo_{now.strftime('%H%M%S')}",
                "role": "parent",
                "status": "break",
            }
        )
        .execute()
        .data[0]
    )

    # 2) 링크
    supabase.table("teacher_student_links").insert(
        {"teacher_user_id": teacher["id"], "student_user_id": student["id"]}
    ).execute()
    supabase.table("parent_student_links").insert(
        {"parent_user_id": parent["id"], "student_user_id": student["id"]}
    ).execute()

    # 3) 숙제 2개 + 제출 1개
    hw1 = (
        supabase.table("homework_assignments")
        .insert(
            {
                "student_user_id": student["id"],
                "title": "중2 수학 함수 연습",
                "description": "교재 p.120 함수 그래프 1~10번",
                "created_at": now.isoformat(),
            }
        )
        .execute()
        .data[0]
    )
    hw2 = (
        supabase.table("homework_assignments")
        .insert(
            {
                "student_user_id": student["id"],
                "title": "영어 독해 숙제",
                "description": "모의고사 3회 독해 파트",
                "created_at": (now - timedelta(days=1)).isoformat(),
            }
        )
        .execute()
        .data[0]
    )

    supabase.table("homework_submissions").insert(
        {
            "assignment_id": hw1["id"],
            "student_user_id": student["id"],
            # 데모용: 실제 파일 대신 더미 경로
            "storage_path": "problem_images/demo/demo_homework.png",
            "created_at": now.isoformat(),
        }
    ).execute()

    # 4) 간단한 상담 로그 1개
    supabase.table("teacher_consultation_logs").insert(
        {
            "teacher_user_id": teacher["id"],
            "student_user_id": student["id"],
            "one_liner": "최근 함수 단원에서 그래프 해석이 약해 추가 연습이 필요합니다.",
            "note": "다음 주까지 함수 그래프 기초 문제 20문제 추가로 내주기.",
            "snapshot": {
                "demo": True,
                "created_at": now.isoformat(),
            },
        }
    ).execute()

    return {
        "teacher": teacher,
        "student": student,
        "parent": parent,
        "homeworks": [hw1, hw2],
    }


# handle에 '_demo_'가 포함된 유저 = 데모 시드로 생성된 유저
DEMO_HANDLE_PATTERN = "%_demo_%"


def _get_demo_user_ids(supabase) -> Tuple[List[str], List[str], List[str]]:
    """
    handle이 _demo_를 포함하는 유저 id 목록을 role별로 반환.
    returns: (teacher_ids, student_ids, parent_ids)
    """
    try:
        rows = (
            supabase.table("users")
            .select("id, role")
            .ilike("handle", DEMO_HANDLE_PATTERN)
            .execute()
            .data
            or []
        )
    except Exception:
        rows = []
    teacher_ids = [r["id"] for r in rows if (r.get("role") or "").strip().lower() == "teacher"]
    student_ids = [r["id"] for r in rows if (r.get("role") or "").strip().lower() == "student"]
    parent_ids = [r["id"] for r in rows if (r.get("role") or "").strip().lower() == "parent"]
    return (teacher_ids, student_ids, parent_ids)


def delete_demo_data() -> Dict[str, Any]:
    """
    데모 시드로 넣은 데이터만 삭제 (handle에 '_demo_'가 포함된 유저와 그에 연관된 모든 행).
    실제로 쌓인 데이터(david, joshua 등)는 건드리지 않음.
    service role 클라이언트 필요. 삭제된 건수 요약 반환.
    """
    supabase = _get_client()
    teacher_ids, student_ids, parent_ids = _get_demo_user_ids(supabase)
    demo_ids = list(dict.fromkeys(teacher_ids + student_ids + parent_ids))
    if not demo_ids:
        return {"ok": True, "message": "삭제할 데모 유저가 없습니다.", "deleted": {}}

    deleted: Dict[str, int] = {}
    # 1) teacher_consultation_logs
    try:
        supabase.table("teacher_consultation_logs").delete().in_("teacher_user_id", demo_ids).execute()
    except Exception:
        pass
    try:
        supabase.table("teacher_consultation_logs").delete().in_("student_user_id", demo_ids).execute()
    except Exception:
        pass

    # 2) homework_feedback: submission_id가 데모 학생의 homework_submissions인 것
    if student_ids:
        try:
            sub_res = supabase.table("homework_submissions").select("id").in_("student_user_id", student_ids).execute()
            sub_ids = [s["id"] for s in (sub_res.data or []) if s.get("id")]
            if sub_ids:
                supabase.table("homework_feedback").delete().in_("submission_id", sub_ids).execute()
                deleted["homework_feedback"] = len(sub_ids)
        except Exception:
            pass
        # 3) homework_submissions
        try:
            r = supabase.table("homework_submissions").delete().in_("student_user_id", student_ids).execute()
            deleted["homework_submissions"] = len(r.data) if r.data else 0
        except Exception:
            pass
        # 4) homework_assignments
        try:
            r = supabase.table("homework_assignments").delete().in_("student_user_id", student_ids).execute()
            deleted["homework_assignments"] = len(r.data) if r.data else 0
        except Exception:
            pass
        # 5) homework_non_submit_reasons
        try:
            supabase.table("homework_non_submit_reasons").delete().in_("student_user_id", student_ids).execute()
        except Exception:
            pass
        # 6) chat_messages
        try:
            supabase.table("chat_messages").delete().in_("student_user_id", student_ids).execute()
        except Exception:
            pass
        # 7) concept_review_attempts
        try:
            supabase.table("concept_review_attempts").delete().in_("student_user_id", student_ids).execute()
        except Exception:
            pass
        # 8) problem_item_feedback
        try:
            supabase.table("problem_item_feedback").delete().in_("student_user_id", student_ids).execute()
        except Exception:
            pass
        # 9) attempts
        try:
            supabase.table("attempts").delete().in_("student_user_id", student_ids).execute()
        except Exception:
            pass
        # 10) grading_items
        try:
            supabase.table("grading_items").delete().in_("student_user_id", student_ids).execute()
        except Exception:
            pass
        # 11) problem_items: 데모 학생의 problem_submissions에 연결된 것
        try:
            sub_res = supabase.table("problem_submissions").select("id").in_("student_user_id", student_ids).execute()
            sub_ids = [s["id"] for s in (sub_res.data or []) if s.get("id")]
            if sub_ids:
                supabase.table("problem_items").delete().in_("submission_id", sub_ids).execute()
                deleted["problem_items"] = len(sub_ids)
        except Exception:
            pass
        # 12) problem_submissions
        try:
            r = supabase.table("problem_submissions").delete().in_("student_user_id", student_ids).execute()
            deleted["problem_submissions"] = len(r.data) if r.data else 0
        except Exception:
            pass
        # 13) practice_results: 데모 학생의 practice_items
        try:
            pi_res = supabase.table("practice_items").select("id").in_("student_user_id", student_ids).execute()
            pi_ids = [p["id"] for p in (pi_res.data or []) if p.get("id")]
            if pi_ids:
                supabase.table("practice_results").delete().in_("practice_item_id", pi_ids).execute()
        except Exception:
            pass
        # 14) practice_items
        try:
            supabase.table("practice_items").delete().in_("student_user_id", student_ids).execute()
        except Exception:
            pass
        # 15) focus_events
        try:
            supabase.table("focus_events").delete().in_("student_user_id", student_ids).execute()
        except Exception:
            pass
        # 16) focus_alert_sent
        try:
            supabase.table("focus_alert_sent").delete().in_("student_user_id", student_ids).execute()
        except Exception:
            pass

    # 17) notification_settings (user_id 또는 student_user_id가 데모)
    try:
        supabase.table("notification_settings").delete().in_("user_id", demo_ids).execute()
    except Exception:
        pass
    try:
        if student_ids:
            supabase.table("notification_settings").delete().in_("student_user_id", student_ids).execute()
    except Exception:
        pass
    # 18) teacher_notes, weekly_plans
    try:
        supabase.table("teacher_notes").delete().in_("student_user_id", student_ids).execute()
    except Exception:
        pass
    try:
        supabase.table("teacher_notes").delete().in_("teacher_user_id", teacher_ids).execute()
    except Exception:
        pass
    try:
        supabase.table("weekly_plans").delete().in_("student_user_id", student_ids).execute()
    except Exception:
        pass
    try:
        supabase.table("weekly_plans").delete().in_("teacher_user_id", teacher_ids).execute()
    except Exception:
        pass
    # 19) teacher_student_links, parent_student_links
    try:
        supabase.table("teacher_student_links").delete().in_("teacher_user_id", teacher_ids).execute()
    except Exception:
        pass
    try:
        supabase.table("teacher_student_links").delete().in_("student_user_id", student_ids).execute()
    except Exception:
        pass
    try:
        supabase.table("parent_student_links").delete().in_("parent_user_id", parent_ids).execute()
    except Exception:
        pass
    try:
        supabase.table("parent_student_links").delete().in_("student_user_id", student_ids).execute()
    except Exception:
        pass
    # 20) teacher_student_notes (있을 경우)
    try:
        supabase.table("teacher_student_notes").delete().in_("student_user_id", student_ids).execute()
    except Exception:
        pass
    try:
        supabase.table("teacher_student_notes").delete().in_("teacher_user_id", teacher_ids).execute()
    except Exception:
        pass
    # 21) concept_review_quizzes (student_user_id 있을 수 있음)
    try:
        supabase.table("concept_review_quizzes").delete().in_("student_user_id", student_ids).execute()
    except Exception:
        pass
    # 22) users
    try:
        r = supabase.table("users").delete().in_("id", demo_ids).execute()
        deleted["users"] = len(r.data) if r.data else len(demo_ids)
    except Exception as e:
        return {"ok": False, "message": f"데모 유저 삭제 실패: {e}", "deleted": deleted}

    return {"ok": True, "message": f"데모 유저 {len(demo_ids)}명 및 연관 데이터 삭제 완료.", "deleted": deleted, "demo_user_count": len(demo_ids)}

