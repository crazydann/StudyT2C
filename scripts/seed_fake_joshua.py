import json
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone


# 프로젝트 루트를 sys.path 에 추가해서 'services' 모듈을 인식시키기
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.supabase_client import supabase  # noqa: E402


NOW = datetime.now(timezone.utc)


def _resolve_student_id_by_handle(handle: str) -> str:
    """
    users.handle = 'joshua' 인 행을 찾아 id(UUID)를 가져온다.
    """
    rows = (
        supabase.table("users")
        .select("id,handle")
        .eq("handle", handle)
        .limit(1)
        .execute()
        .data
        or []
    )
    if not rows:
        raise RuntimeError(f"users 테이블에서 handle='{handle}' 인 학생을 찾지 못했습니다.")
    return rows[0]["id"]


def _seed_from_data(student_id: str, data: dict) -> None:
    sessions = data.get("sessions") or []
    questions = data.get("questions") or []

    # 1) problem_submissions + problem_items
    for sess in sessions:
        days_ago = int(sess.get("days_ago", 0))
        created_at = (NOW - timedelta(days=days_ago)).isoformat()
        subject = (sess.get("subject") or "수학").strip()

        # 한 번의 채점 세션
        sub_rows = (
            supabase.table("problem_submissions")
            .insert(
                {
                    "student_user_id": student_id,
                    "created_at": created_at,
                }
            )
            .execute()
            .data
            or []
        )
        if not sub_rows:
            continue
        submission_id = sub_rows[0].get("id")
        if not submission_id:
            continue

        # 문항별 결과
        items = sess.get("items") or []
        rows = []
        for it in items:
            rows.append(
                {
                    "student_user_id": student_id,
                    "submission_id": submission_id,
                    "is_correct": bool(it.get("is_correct")),
                    "key_concepts": it.get("key_concepts") or [],
                    "created_at": created_at,
                }
            )
        if rows:
            supabase.table("problem_items").insert(rows).execute()

    # 2) AI 튜터 질문 로그 (chat_messages)
    chat_rows = []
    for q in questions:
        days_ago = int(q.get("days_ago", 0))
        created_at = (NOW - timedelta(days=days_ago)).isoformat()
        content = q.get("content") or ""
        subject = (q.get("subject") or "수학").strip()
        concept = (q.get("concept") or "").strip()

        meta = {"subject": subject}
        if concept:
            meta["concept"] = concept

        chat_rows.append(
            {
                "student_user_id": student_id,
                "role": "user",
                "content": content,
                "meta": meta,
                "created_at": created_at,
            }
        )

    if chat_rows:
        supabase.table("chat_messages").insert(chat_rows).execute()


def main() -> None:
    base = BASE_DIR  # 프로젝트 루트

    # 처리할 JSON 파일 목록: 기본 + 추가 조각들
    paths = [base / "fake_usage_joshua.json"]
    paths.extend(sorted(base.glob("fake_usage_joshua_*.json")))

    # handle='joshua' 의 실제 id 조회 (한 번만)
    student_id = _resolve_student_id_by_handle("joshua")

    for path in paths:
        if not path.exists():
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        _seed_from_data(student_id, data)
        print(f"✅ seeded from {path.name}")

    print(f"✅ All fake data for handle='joshua' (id={student_id}) inserted.")


if __name__ == "__main__":
    main()

