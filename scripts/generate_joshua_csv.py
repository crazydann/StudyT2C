import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path

# joshua의 UUID (이미 seed 스크립트 실행 로그에 나온 값)
STUDENT_ID = "dc049885-f9ff-402e-8fc6-1a8aec34f73c"  # joshua
TEACHER_ID = "7137728b-acf1-4097-b630-ea86309727c7"  # t1

NOW = datetime.now(timezone(timedelta(hours=9)))  # KST 기준
BASE = Path(__file__).resolve().parent.parent / "data"
BASE.mkdir(exist_ok=True)

MATH_CONCEPTS = [
    "미분의 기본법칙",
    "연속과 미분가능성",
    "정적분의 의미",
    "정적분과 넓이",
    "평균값 정리",
    "부분적분법",
    "순열과 조합",
    "이항정리",
    "확률의 정의",
    "조건부확률",
    "확률변수와 기대값",
    "수열의 극한",
    "급수의 수렴",
    "등차수열",
    "등비수열",
    "삼각함수의 그래프",
    "삼각함수의 덧셈정리",
    "삼각함수의 활용",
    "벡터의 연산",
    "내적의 의미",
    "직선의 방정식",
    "평면의 방정식",
    "집합과 명제",
    "명제의 역과 대우",
    "함수의 개념",
    "함수의 그래프 해석",
    "이차함수의 그래프",
    "이차함수의 최대최소",
]


def random_date_within_8_weeks() -> str:
    days_ago = random.randint(0, 55)  # 약 8주
    dt = NOW - timedelta(days=days_ago)
    return dt.isoformat()


def gen_submissions_and_items(target_sessions: int = 160, avg_items: int = 10):
    """problem_submissions, problem_items용 데이터 생성."""
    subs_rows = []
    items_rows = []

    for i in range(target_sessions):
        sub_id = f"sub-{i:04d}"  # CSV용 가짜 id (Import 시 id 컬럼이 필요 없으면 이 컬럼은 제거해도 됩니다)
        created_at = random_date_within_8_weeks()

        subs_rows.append(
            {
                "id": sub_id,
                "student_user_id": STUDENT_ID,
                "created_at": created_at,
            }
        )

        num_items = max(5, int(random.gauss(avg_items, 2)))
        for _ in range(num_items):
            concept = random.choice(MATH_CONCEPTS)
            # 기본 정답률 80%, 일부 어려운 개념은 60%로 낮춤
            correct_prob = 0.8
            if concept in ["조건부확률", "평균값 정리", "급수의 수렴", "삼각함수의 덧셈정리"]:
                correct_prob = 0.6
            is_correct = random.random() < correct_prob
            items_rows.append(
                {
                    "student_user_id": STUDENT_ID,
                    "submission_id": sub_id,
                    "is_correct": str(is_correct).lower(),  # CSV에서 true/false 문자열
                    "key_concepts": f"{{{concept}}}",  # text[] 형식이면 이렇게
                    "created_at": created_at,
                }
            )

    return subs_rows, items_rows


def gen_chat_messages(target_questions: int = 80):
    rows = []
    templates = [
        "최근에 {concept} 개념이 헷갈려요. 예시와 함께 다시 설명해 줄 수 있나요?",
        "{concept}이(가) 수능 문제에서 어떻게 쓰이는지 알고 싶어요.",
        "{concept} 관련 문제에서 식을 어떻게 세워야 할지 막힙니다.",
        "{concept}을(를) 그래프로 직관적으로 이해할 수 있는 방법이 있을까요?",
    ]
    for _ in range(target_questions):
        concept = random.choice(MATH_CONCEPTS)
        content = random.choice(templates).format(concept=concept)
        created_at = random_date_within_8_weeks()
        rows.append(
            {
                "student_user_id": STUDENT_ID,
                "role": "user",
                "content": content,
                "meta": f'{{"subject":"수학","concept":"{concept}"}}',
                "created_at": created_at,
            }
        )
    return rows


def gen_homework():
    assigns = []
    subs = []
    for i in range(16):  # 8주 * 주2회 과제
        days_ago = random.randint(5, 55)
        created_at = (NOW - timedelta(days=days_ago)).isoformat()
        aid = f"hw-{i:03d}"
        title = f"주간 과제 {i + 1}"
        desc = f"{random.choice(MATH_CONCEPTS)} 연습 문제 세트"

        assigns.append(
            {
                "id": aid,
                "student_user_id": STUDENT_ID,
                "title": title,
                "description": desc,
                "created_at": created_at,
            }
        )

        # 제출 여부/지각 결정
        submitted = random.random() < 0.8  # 80% 제출
        if submitted:
            delay_days = random.choice([0, 0, 0, 1, 2])  # 대부분 제때, 가끔 지각
            sub_created = (NOW - timedelta(days=max(0, days_ago - delay_days))).isoformat()
            subs.append(
                {
                    "assignment_id": aid,
                    "student_user_id": STUDENT_ID,
                    "created_at": sub_created,
                    "storage_path": f"homework/{STUDENT_ID}/{aid}.pdf",
                }
            )
    return assigns, subs


def gen_consults():
    rows = []
    for i in range(8):  # 8주 * 주1회 상담
        days_ago = 7 * (i + 1) - random.randint(0, 2)
        created_at = (NOW - timedelta(days=days_ago)).isoformat()
        one_liner = f"최근 {random.choice(MATH_CONCEPTS)} 개념 이해도 점검 및 다음 단원 계획 논의"
        note = "과제 수행 태도 양호, 개념 이해는 안정적이나 심화문제에서 실수 발생."
        snapshot = f'{{"plan_done":"{"충분히 다룸" if i % 2 == 0 else "일부만 다룸"}"}}'
        rows.append(
            {
                "teacher_user_id": TEACHER_ID,
                "student_user_id": STUDENT_ID,
                "one_liner": one_liner,
                "note": note,
                "snapshot": snapshot,
                "created_at": created_at,
            }
        )
    return rows


def write_csv(path: Path, fieldnames, rows):
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main():
    subs_rows, items_rows = gen_submissions_and_items(target_sessions=160, avg_items=10)
    chat_rows = gen_chat_messages(target_questions=80)
    assigns, subs = gen_homework()
    consults = gen_consults()

    write_csv(
        BASE / "problem_submissions_joshua.csv",
        ["id", "student_user_id", "created_at"],
        subs_rows,
    )
    write_csv(
        BASE / "problem_items_joshua.csv",
        ["student_user_id", "submission_id", "is_correct", "key_concepts", "created_at"],
        items_rows,
    )
    write_csv(
        BASE / "chat_messages_joshua.csv",
        ["student_user_id", "role", "content", "meta", "created_at"],
        chat_rows,
    )
    write_csv(
        BASE / "homework_assignments_joshua.csv",
        ["id", "student_user_id", "title", "description", "created_at"],
        assigns,
    )
    write_csv(
        BASE / "homework_submissions_joshua.csv",
        ["assignment_id", "student_user_id", "created_at", "storage_path"],
        subs,
    )
    write_csv(
        BASE / "teacher_consultation_logs_joshua.csv",
        ["teacher_user_id", "student_user_id", "one_liner", "note", "snapshot", "created_at"],
        consults,
    )
    print("✅ CSV files generated under data/ for joshua.")


if __name__ == "__main__":
    main()

