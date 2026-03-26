#!/usr/bin/env python3
"""
seed_rich_demo.py
=================
David(중2) + Joshua(고3) 의 2개월치 풍부한 가상 데이터를 Supabase에 삽입합니다.

  국어 + 수학, 주 2회(화/목), 약 8주 × 4과목세션 = 64 채점세션
  - problem_submissions / problem_items / problem_item_feedback
  - homework_assignments / homework_submissions / homework_non_submit_reasons
  - chat_messages (AI 튜터 질문/답변)
  - teacher_student_notes (선생님 상담 메모)
  - concept_review_quizzes / concept_review_attempts
  - focus_events

사용법:
  pip install supabase==2.4.1   # (이미 requirements.txt에 있음)
  python3 scripts/seed_rich_demo.py

환경 변수(또는 스크립트 상단 상수)로 Supabase URL/키를 설정하세요.
"""

from __future__ import annotations

import os
import random
import sys
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

# ── Supabase 접속 정보 ──────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get(
    "SUPABASE_URL",
    "https://kqkbfpvmbxtaoihyeewz.supabase.co",
)
SERVICE_ROLE_KEY = os.environ.get(
    "SUPABASE_SERVICE_KEY",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imtxa2JmcHZtYnh0YW9paHllZXd6Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc3MTEyNTM4MSwiZXhwIjoyMDg2NzAxMzgxfQ.EZevfrUyDbbpXrw3iFZ9eUjo7fkuAuFFhzSbc6O_FeY",
)

try:
    from supabase import create_client
except ImportError:
    print("[ERROR] supabase 패키지를 찾을 수 없습니다.")
    print("  pip install supabase==2.4.1")
    sys.exit(1)

sb = create_client(SUPABASE_URL, SERVICE_ROLE_KEY)

# ── 상수 ───────────────────────────────────────────────────────────────────
NOW = datetime.now(timezone.utc)
SEED_WEEKS = 8          # 2달 = 8주
SESSIONS_PER_WEEK = 2   # 화/목

random.seed(42)  # 재현 가능한 난수

# ── 학생 프로필 ─────────────────────────────────────────────────────────────
STUDENTS = {
    "david": {
        "grade": "중2",
        "subjects": {
            "KOREAN": {
                "label": "국어",
                "weak_concepts": ["시 분석", "화자의 정서", "비유법 파악", "문학 감상"],
                "ok_concepts": ["서술형 쓰기", "어휘력", "독해 속도"],
                "wrong_rate_range": (0.35, 0.55),
            },
            "MATH": {
                "label": "수학",
                "weak_concepts": ["이차함수 최댓값·최솟값", "이차방정식 근의 공식", "연립방정식 활용"],
                "ok_concepts": ["일차함수", "인수분해 기초", "수와 연산"],
                "wrong_rate_range": (0.40, 0.60),
            },
        },
        "chat_patterns": {
            "KOREAN": [
                ("시에서 화자가 느끼는 감정을 어떻게 파악하나요?", "화자의 정서"),
                ("비유법 종류가 헷갈려요. 은유와 직유 차이가 뭔가요?", "비유법 파악"),
                ("문학 작품 감상문 쓸 때 어떤 구조로 써야 해요?", "문학 감상"),
                ("시의 분위기를 분석하는 방법을 알려주세요.", "시 분석"),
                ("이 시에서 '새벽빛'이 무엇을 상징하는 건가요?", "시 분석"),
            ],
            "MATH": [
                ("이차함수에서 꼭짓점 공식을 어떻게 쓰나요?", "이차함수 최댓값·최솟값"),
                ("최댓값과 최솟값은 어떻게 구해요?", "이차함수 최댓값·최솟값"),
                ("근의 공식이 기억이 안 나요. 다시 설명해 주세요.", "이차방정식 근의 공식"),
                ("연립방정식 문제에서 어떤 방법이 빠른가요?", "연립방정식 활용"),
                ("이차방정식의 판별식은 언제 써요?", "이차방정식 근의 공식"),
            ],
        },
        "consult_notes": [
            "수학 이차함수 단원에서 최댓값·최솟값 파악이 어려운 상태. 그래프 직접 그려보며 설명 필요. 다음 수업에 y=-x²+4x+1 형태 문제 5개 추가.",
            "국어 시 분석 전반적으로 약함. 화자의 정서 파악 훈련이 필요. 현대시 3편 독해 과제 부과.",
            "수학 시험 전 점검: 근의 공식 암기 완료, 활용 문제에서 실수 잦음. 계산 검토 습관 강조.",
            "국어 비유법 파악 많이 늘었음. 이제 주제 파악으로 넘어갈 것. 이번 주 소설 지문 추가.",
            "전반적 학습 태도 양호. 질문 횟수 늘고 있어 긍정적. 수학은 여전히 응용 문제에서 막힘.",
            "방학 직전 점검: 이차함수 완성도 60% → 목표 80% 위해 여름방학 문제집 pp.45-80 자율 학습 권장.",
        ],
    },
    "joshua": {
        "grade": "고3",
        "subjects": {
            "KOREAN": {
                "label": "국어",
                "weak_concepts": ["화법과 작문 통합형", "매체 언어 분석", "문법 어휘 선택지"],
                "ok_concepts": ["문학 감상", "독서(비문학)", "화법 기본"],
                "wrong_rate_range": (0.25, 0.40),
            },
            "MATH": {
                "label": "수학",
                "weak_concepts": ["미적분 치환 적분", "정적분과 넓이", "급수와 극한 증명"],
                "ok_concepts": ["함수의 극값", "도함수 활용", "수열"],
                "wrong_rate_range": (0.30, 0.50),
            },
        },
        "chat_patterns": {
            "KOREAN": [
                ("화법과 작문이 통합된 문제 유형이 너무 헷갈려요.", "화법과 작문 통합형"),
                ("매체 언어 문제에서 사진 자료 해석하는 법을 모르겠어요.", "매체 언어 분석"),
                ("문법 문제에서 어미 활용 선택지가 어려워요.", "문법 어휘 선택지"),
                ("수능 국어 독서 비문학 지문 읽는 시간이 오래 걸려요.", "독서(비문학)"),
                ("화법 지문에서 말하는 이의 의도를 파악하기 어려워요.", "화법 기본"),
            ],
            "MATH": [
                ("치환 적분할 때 어떤 걸 t로 놓아야 하는지 모르겠어요.", "미적분 치환 적분"),
                ("정적분으로 넓이 구할 때 부호를 항상 헷갈려요.", "정적분과 넓이"),
                ("급수 수렴 증명 방법을 잘 모르겠어요.", "급수와 극한 증명"),
                ("로피탈 정리는 언제 써야 하나요?", "급수와 극한 증명"),
                ("치환 적분과 부분 적분 중 어떤 걸 먼저 시도해야 해요?", "미적분 치환 적분"),
            ],
        },
        "consult_notes": [
            "수능 수학 미적분 영역 중 치환 적분에서 실수 패턴 발견. 유형별 치환 전략 정리 필요. 수능 기출 5개년 치환 적분 문제 모음 제공.",
            "국어 화법과 작문 통합형 문제 오답률 높음. 지문 읽는 순서 훈련 필요. PSAT 기출 5문제 추가 과제.",
            "수학 6월 모의고사 대비 점검: 정적분 넓이 계산 오류 잦음. 절댓값 조건 확인 습관화 필요.",
            "국어 매체 언어 부분 향상됨. 이제 3점짜리 변환·추론 문제 집중 연습 필요.",
            "9월 모의고사 이후 점검: 국어 86점(+4), 수학 82점(+6) 상승. 적분 단원 완성도 목표 90% 도달.",
            "수능 D-60 최종 점검: 수학 3·4등급 경계 반복 실수 방지 전략. 시간 관리 모의 훈련 1회/주 권장.",
        ],
    },
}

# ── 헬퍼 ───────────────────────────────────────────────────────────────────

def _resolve_student_id(handle: str) -> str:
    rows = sb.table("users").select("id,handle").eq("handle", handle).limit(1).execute().data or []
    if not rows:
        raise RuntimeError(f"handle='{handle}' 학생을 users 테이블에서 찾지 못했습니다.")
    return rows[0]["id"]


def _resolve_teacher_id() -> Optional[str]:
    rows = sb.table("users").select("id").eq("role", "teacher").limit(1).execute().data or []
    if rows:
        return rows[0]["id"]
    return None


def _session_times(weeks: int = SEED_WEEKS) -> List[datetime]:
    """화(1), 목(3) 기준 과거 세션 날짜 목록 반환."""
    times = []
    for w in range(weeks, 0, -1):
        # 화요일
        tue = NOW - timedelta(weeks=w) + timedelta(days=(1 - NOW.weekday()) % 7)
        tue = tue.replace(hour=16, minute=30, second=0, microsecond=0)
        times.append(tue)
        # 목요일
        thu = tue + timedelta(days=2)
        times.append(thu)
    return times


def _make_items(student_id: str, submission_id: str, ts: str,
                _subject: str, profile: dict) -> List[Dict[str, Any]]:
    """채점 문항 5~8개 생성."""
    weak = profile["weak_concepts"]
    ok = profile["ok_concepts"]
    all_c = weak + ok
    wr_lo, wr_hi = profile["wrong_rate_range"]
    wrong_rate = random.uniform(wr_lo, wr_hi)

    n_items = random.randint(5, 8)
    items = []
    for i in range(1, n_items + 1):
        is_correct = random.random() > wrong_rate
        # 개념: 오답이면 취약 개념, 정답이면 정답 개념 위주
        if not is_correct:
            kc = random.sample(weak, k=min(2, len(weak)))
        else:
            kc = random.sample(all_c, k=min(2, len(all_c)))
        items.append({
            "student_user_id": student_id,
            "submission_id": submission_id,
            "item_no": i,
            "is_correct": is_correct,
            "key_concepts": kc,
            "explanation_summary": f"{'정답' if is_correct else '오답'}: {', '.join(kc)} 관련 문제입니다.",
            "created_at": ts,
        })
    return items


def _make_feedback(student_id: str, items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """오답 항목에 대한 피드백 레코드 생성."""
    reasons = ["concept", "calculation", "reading", "guessing"]
    feedbacks = []
    for it in items:
        if not it["is_correct"]:
            feedbacks.append({
                "student_user_id": student_id,
                "problem_item_id": it.get("id"),
                "understanding": random.choice(["confused", "understood"]),
                "reason_category": random.choice(reasons),
                "created_at": it["created_at"],
            })
    return feedbacks


def seed_grading(student_id: str, handle: str, sessions: List[datetime]) -> None:
    print(f"\n  [채점] {handle} — {len(sessions)}세션 × 2과목 ...")
    profile = STUDENTS[handle]

    for idx, sess_dt in enumerate(sessions):
        for subj_code, subj_info in profile["subjects"].items():
            # 과목별 시간 오프셋 (국어 오전, 수학 오후)
            offset_h = 0 if subj_code == "KOREAN" else 2
            ts_dt = sess_dt + timedelta(hours=offset_h)
            ts = ts_dt.isoformat()

            # 1) problem_submissions — upsert으로 중복 방지
            file_hash = f"demo_{handle}_{subj_code}_w{idx:02d}"
            sub_res = sb.table("problem_submissions").upsert(
                {
                    "student_user_id": student_id,
                    "file_hash": file_hash,
                    "created_at": ts,
                },
                on_conflict="student_user_id,file_hash",
            ).execute().data or []
            if not sub_res:
                continue
            submission_id = sub_res[0]["id"]

            # 2) problem_items
            items_data = _make_items(student_id, submission_id, ts, subj_code, subj_info)
            inserted_items = sb.table("problem_items").insert(items_data).execute().data or []

            # 3) problem_item_feedback (오답에 대해서만)
            feedback_data = []
            for it in inserted_items:
                if not it.get("is_correct"):
                    reasons = ["concept", "calculation", "reading", "guessing"]
                    feedback_data.append({
                        "student_user_id": student_id,
                        "problem_item_id": it["id"],
                        "understanding": random.choice(["confused", "understood"]),
                        "reason_category": random.choice(reasons),
                        "created_at": ts,
                    })
            if feedback_data:
                sb.table("problem_item_feedback").insert(feedback_data).execute()


def seed_chat(student_id: str, handle: str, sessions: List[datetime]) -> None:
    print(f"  [채팅] {handle} ...")
    profile = STUDENTS[handle]
    off_topic_msgs = [
        ("오늘 저녁 뭐 먹을까요?", "DAILY"),
        ("요즘 인기 게임이 뭐예요?", "GAME"),
        ("유튜브 재밌는 거 추천해줘요", "ENTERTAINMENT"),
        ("요즘 날씨가 너무 더워요", "DAILY"),
    ]

    rows = []
    for idx, sess_dt in enumerate(sessions):
        for subj_code, patterns in profile["chat_patterns"].items():
            q_text, concept = random.choice(patterns)
            ts = (sess_dt + timedelta(minutes=random.randint(5, 60))).isoformat()
            # 질문
            rows.append({
                "student_user_id": student_id,
                "role": "user",
                "content": q_text,
                "meta": {"subject": subj_code, "concept": concept},
                "created_at": ts,
            })
            # 답변 (AI 역할)
            ts2 = (sess_dt + timedelta(minutes=random.randint(60, 90))).isoformat()
            rows.append({
                "student_user_id": student_id,
                "role": "assistant",
                "content": f"좋은 질문이에요! {concept}에 대해 설명할게요. "
                           "먼저 개념부터 정리하고, 예제를 통해 풀어볼게요. "
                           "이 개념은 시험에도 자주 나오니 꼼꼼히 익혀두세요.",
                "meta": {"subject": subj_code, "concept": concept},
                "created_at": ts2,
            })
        # 공부 외 질문 (랜덤 20% 확률)
        if random.random() < 0.2:
            off_q, off_cat = random.choice(off_topic_msgs)
            ts_off = (sess_dt + timedelta(minutes=random.randint(90, 120))).isoformat()
            rows.append({
                "student_user_id": student_id,
                "role": "user",
                "content": off_q,
                "meta": {"subject": "OTHER", "category": off_cat, "is_offtopic": True},
                "created_at": ts_off,
            })

    if rows:
        # 배치 삽입 (100개씩)
        for i in range(0, len(rows), 100):
            sb.table("chat_messages").insert(rows[i:i+100]).execute()


def seed_homework(student_id: str, handle: str, sessions: List[datetime]) -> None:
    print(f"  [숙제] {handle} ...")
    profile = STUDENTS[handle]
    non_submit_reasons = ["forgot", "time", "hard"]

    for idx, sess_dt in enumerate(sessions):
        for subj_code, subj_info in profile["subjects"].items():
            due = sess_dt + timedelta(days=2)
            # 숙제 부과 (due_date/subject_code 는 컬럼이 없으면 무시됨)
            hw_payload: Dict[str, Any] = {
                "student_user_id": student_id,
                "title": f"[{subj_info['label']}] {subj_info['weak_concepts'][idx % len(subj_info['weak_concepts'])]} 연습",
                "description": f"{subj_info['weak_concepts'][idx % len(subj_info['weak_concepts'])]} 관련 연습 문제 10문제",
                "created_at": sess_dt.isoformat(),
            }
            # optional columns — try adding them (will fail silently if column not in DB)
            try:
                hw_payload["due_date"] = due.isoformat()
                hw_payload["subject_code"] = subj_code
            except Exception:
                pass
            hw_res = sb.table("homework_assignments").insert(hw_payload).execute().data or []
            if not hw_res:
                continue
            hw_id = hw_res[0]["id"]

            # 제출(75%) vs 미제출(25%)
            if random.random() < 0.75:
                submit_dt = due - timedelta(hours=random.randint(1, 24))
                sb.table("homework_submissions").insert({
                    "assignment_id": hw_id,
                    "student_user_id": student_id,
                    "storage_path": f"homework/demo/{handle}/{subj_code}_{idx}.png",
                    "created_at": submit_dt.isoformat(),
                }).execute()
            else:
                # 미제출 사유
                reason = random.choice(non_submit_reasons)
                sb.table("homework_non_submit_reasons").insert({
                    "student_user_id": student_id,
                    "assignment_id": hw_id,
                    "reason_code": reason,
                    "created_at": due.isoformat(),
                }).execute()


def seed_teacher_notes(student_id: str, teacher_id: str, handle: str) -> None:
    print(f"  [상담 노트] {handle} ...")
    profile = STUDENTS[handle]
    notes = profile["consult_notes"]

    # teacher_student_notes는 teacher×student 조합으로 하나의 메모 레코드
    full_note = "\n\n".join(
        [f"[{i+1}차 상담 {(NOW - timedelta(weeks=SEED_WEEKS - i)).strftime('%Y-%m-%d')}]\n{n}"
         for i, n in enumerate(notes)]
    )
    try:
        sb.table("teacher_student_notes").upsert(
            {
                "teacher_user_id": teacher_id,
                "student_user_id": student_id,
                "note": full_note,
                "updated_at": NOW.isoformat(),
            },
            on_conflict="teacher_user_id,student_user_id",
        ).execute()
    except Exception as e:
        print(f"    [WARN] teacher_student_notes upsert 실패: {e}")


def seed_concept_reviews(student_id: str, handle: str, sessions: List[datetime]) -> None:
    print(f"  [개념 복습] {handle} ...")
    profile = STUDENTS[handle]

    for idx, sess_dt in enumerate(sessions[::2]):  # 격주로 복습 퀴즈
        for subj_code, subj_info in profile["subjects"].items():
            concept = random.choice(subj_info["weak_concepts"])
            ts = (sess_dt + timedelta(hours=3)).isoformat()
            ts2 = (sess_dt + timedelta(hours=4)).isoformat()

            q_text = f"{concept}의 핵심 개념을 설명하시오."
            a_text = f"{concept}에 대한 모범 답안입니다."
            options = [
                {"label": "A", "text": a_text},
                {"label": "B", "text": "오답 보기 1"},
                {"label": "C", "text": "오답 보기 2"},
                {"label": "D", "text": "오답 보기 3"},
            ]
            correct_index = 0

            # concept_review_quizzes (실제 스키마: quiz_question, options, correct_index)
            quiz_res = sb.table("concept_review_quizzes").insert({
                "student_user_id": student_id,
                "source_question": q_text,
                "source_answer": a_text,
                "quiz_question": q_text,
                "options": options,
                "correct_index": correct_index,
                "created_at": ts,
            }).execute().data or []

            # concept_review_attempts (실제 스키마: quiz_question, correct_index, user_choice_index, is_correct)
            is_correct = random.random() > 0.4
            user_choice = 0 if is_correct else random.randint(1, 3)
            sb.table("concept_review_attempts").insert({
                "student_user_id": student_id,
                "source_question": q_text,
                "source_answer": a_text,
                "quiz_question": q_text,
                "correct_index": correct_index,
                "user_choice_index": user_choice,
                "is_correct": is_correct,
                "created_at": ts2,
            }).execute()


def seed_focus_events(student_id: str, handle: str, sessions: List[datetime]) -> None:
    print(f"  [집중도] {handle} ...")
    rows = []
    for sess_dt in sessions:
        # 세션 시작 후 랜덤 이탈/복귀 이벤트
        study_start = sess_dt.replace(hour=16, minute=0)
        for _ in range(random.randint(0, 3)):
            left_at = study_start + timedelta(minutes=random.randint(10, 50))
            returned_at = left_at + timedelta(minutes=random.randint(1, 15))
            rows.append({
                "student_user_id": student_id,
                "event_type": "left_tab",
                "created_at": left_at.isoformat(),
            })
            rows.append({
                "student_user_id": student_id,
                "event_type": "returned_tab",
                "created_at": returned_at.isoformat(),
            })

    if rows:
        for i in range(0, len(rows), 100):
            sb.table("focus_events").insert(rows[i:i+100]).execute()


# ── 메인 ───────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("StudyT2C 데모 데이터 시드 스크립트")
    print("=" * 60)

    teacher_id = _resolve_teacher_id()
    if not teacher_id:
        print("[WARN] teacher 계정을 찾지 못했습니다. 상담 노트가 건너뛰어집니다.")

    sessions = _session_times(SEED_WEEKS)
    print(f"\n세션 날짜: {sessions[0].strftime('%Y-%m-%d')} ~ {sessions[-1].strftime('%Y-%m-%d')}")
    print(f"총 세션 수: {len(sessions)} (주 {SESSIONS_PER_WEEK}회 × {SEED_WEEKS}주)")

    for handle in ("david", "joshua"):
        print(f"\n{'='*40}")
        print(f"  학생: {handle} ({STUDENTS[handle]['grade']})")
        print(f"{'='*40}")

        try:
            student_id = _resolve_student_id(handle)
        except RuntimeError as e:
            print(f"  [ERROR] {e}")
            continue

        print(f"  student_id: {student_id}")

        seed_grading(student_id, handle, sessions)
        seed_chat(student_id, handle, sessions)
        seed_homework(student_id, handle, sessions)
        if teacher_id:
            seed_teacher_notes(student_id, teacher_id, handle)
        seed_concept_reviews(student_id, handle, sessions)
        seed_focus_events(student_id, handle, sessions)

        print(f"  ✅ {handle} 데이터 삽입 완료!")

    print("\n" + "=" * 60)
    print("✅ 모든 데모 데이터 삽입 완료!")
    print("=" * 60)


if __name__ == "__main__":
    main()
