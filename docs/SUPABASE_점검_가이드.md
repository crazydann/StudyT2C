# Supabase 점검 가이드 (비개발자용)

코드와 Supabase 테이블·컬럼·권한이 맞는지 한 번에 확인하는 방법입니다.

---

## 1단계: 환경 변수 확인 (.env 파일)

프로젝트 루트의 `.env` 파일에 아래 4개가 모두 있어야 합니다.

| 변수명 | 용도 |
|-------|------|
| `SUPABASE_URL` | Supabase 프로젝트 주소 |
| `SUPABASE_ANON_KEY` | 공개 키 (읽기 등 기본 작업용) |
| `SUPABASE_SERVICE_ROLE_KEY` | 비공개 키 (쓰기, RLS 우회) |
| `GROQ_API_KEY` | AI 튜터용 API 키 |

**확인:** Supabase 대시보드 → Project Settings → API 에서 URL과 키 복사

---

## 2단계: Supabase SQL Editor에서 스키마 점검/수정

Supabase 대시보드 → **SQL Editor** → **New query** → 아래 SQL 전체 복사 후 **Run** 실행

```sql
-- ============================================================
-- StudyT2C: 코드와 Supabase 스키마 일치 확인 및 수정 스크립트
-- 전체 복사 후 Run 실행
-- ============================================================

-- 1) chat_messages: 공부 외 질문 이력 저장용 (가장 문제 많았던 테이블)
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS role text;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS content text;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS meta jsonb;

-- session_id, question, answer를 nullable로 (없으면 에러 나올 수 있음 - 무시 가능)
DO $$
BEGIN
  ALTER TABLE chat_messages ALTER COLUMN session_id DROP NOT NULL;
EXCEPTION WHEN OTHERS THEN NULL;
END $$;
DO $$
BEGIN
  ALTER TABLE chat_messages ALTER COLUMN question DROP NOT NULL;
EXCEPTION WHEN OTHERS THEN NULL;
END $$;
DO $$
BEGIN
  ALTER TABLE chat_messages ALTER COLUMN answer DROP NOT NULL;
EXCEPTION WHEN OTHERS THEN NULL;
END $$;

-- 완료 메시지
SELECT 'chat_messages 스키마 수정 완료' AS result;
```

에러 없이 실행되면 OK입니다. 일부 `DO $$ ... EXCEPTION` 구문에서 에러가 나도, 마지막 `SELECT`가 보이면 진행된 것입니다.

---

## 3단계: 테이블별 코드 기대 스키마 (참고용)

코드가 사용하는 테이블과 기대하는 컬럼입니다.

### chat_messages (채팅 / 공부 외 질문 이력)
- **저장 시**: `student_user_id`, `role`, `content`, `created_at`, `meta`
- **조회 시**: `created_at`, `content`, `meta`, `subject`, `student_user_id`
- `session_id`, `question`, `answer`는 nullable 권장

### users
- `id`, `handle`, `role`, `status`, `detail_permission`, `show_practice_answer`

### parent_student_links
- `parent_user_id`, `student_user_id`

### teacher_student_links
- `teacher_user_id`, `student_user_id`

### homework_assignments
- `id`, `student_user_id`, `title`, `description`, `created_at`, `due_at`, `teacher_user_id`

### homework_submissions
- `id`, `assignment_id`, `student_user_id`, `storage_path`, `created_at`, `status`

### problem_submissions
- `id`, `student_user_id`, `file_hash`, `created_at`, `uploaded_at`

### problem_items
- `id`, `submission_id`, `item_no`, `is_correct`, `key_concepts`, `reason_category`, `subject_code`, `student_user_id`, `next_review_at`, `created_at`

---

## 4단계: 권한 정리

| 작업 | 사용 클라이언트 | 필요한 것 |
|------|-----------------|----------|
| 채팅 저장 (INSERT) | service_role | `SUPABASE_SERVICE_ROLE_KEY` |
| 공부 외 질문 이력 조회 | service_role | `SUPABASE_SERVICE_ROLE_KEY` |
| 기타 읽기/쓰기 | anon 또는 service_role | RLS 정책에 따라 다름 |

**권장:** `SUPABASE_SERVICE_ROLE_KEY` 를 설정해 두면, 코드에서 쓰는 대부분의 쓰기/특수 조회가 동작합니다.

---

## 5단계: 동작 확인 체크리스트

1. [ ] `.env`에 `SUPABASE_SERVICE_ROLE_KEY` 포함
2. [ ] 위 2단계 SQL 실행 완료
3. [ ] 앱 재시작 (`python3 -m streamlit run app.py`)
4. [ ] 학생 화면에서 공부 외 질문 입력 (예: `게임`, `잡담`)
5. [ ] Supabase Table Editor → `chat_messages` 에 새 행 추가 확인
6. [ ] 학부모 화면 → AI 리포트 탭에서 공부 외 질문 이력 표시 확인

---

## 문제가 생겼을 때

- **저장이 안 될 때**: 2단계 SQL 다시 실행, `.env`의 `SUPABASE_SERVICE_ROLE_KEY` 확인
- **조회가 안 될 때**: `SUPABASE_SERVICE_ROLE_KEY` 설정 여부 확인
- **에러 메시지가 뜰 때**: 개발 모드 켜서 메시지 확인 (학생 화면 개발 모드 토글)
