from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, Any

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

