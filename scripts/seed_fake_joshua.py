import json
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone


# 프로젝트 루트를 sys.path 에 추가해서 'services' 모듈을 인식시키기
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from services.supabase_client import supabase  # noqa: E402


STUDENT_ID = "joshua"  # Supabase users.id 와 일치해야 함
NOW = datetime.now(timezone.utc)


def main() -> None:
    base = BASE_DIR  # 프로젝트 루트
    json_path = base / "fake_usage_joshua.json"

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

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
                    "student_user_id": STUDENT_ID,
                    "created_at": created_at,
                    "subject": subject,
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
                    "student_user_id": STUDENT_ID,
                    "submission_id": submission_id,
                    "is_correct": bool(it.get("is_correct")),
                    "key_concepts": it.get("key_concepts") or [],
                    "reason": (it.get("reason") or "").strip() or None,
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
                "student_user_id": STUDENT_ID,
                "role": "user",
                "content": content,
                "meta": meta,
                "created_at": created_at,
            }
        )

    if chat_rows:
        supabase.table("chat_messages").insert(chat_rows).execute()

    print("✅ Fake data for joshua inserted.")


if __name__ == "__main__":
    main()

