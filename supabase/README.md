# Supabase 설정 (chat_messages 공부 외 질문 이력용)

## 실행 방법

1. [Supabase 대시보드](https://supabase.com/dashboard) → 프로젝트 선택
2. 왼쪽 메뉴 **SQL Editor** 클릭
3. **New query** 선택
4. 아래 SQL 전체 복사 → 붙여넣기 → **Run** 실행

```sql
-- chat_messages: 공부 외 질문 이력 저장용 스키마 설정
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS role text;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS content text;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS meta jsonb;
ALTER TABLE chat_messages ALTER COLUMN session_id DROP NOT NULL;
ALTER TABLE chat_messages ALTER COLUMN question DROP NOT NULL;
ALTER TABLE chat_messages ALTER COLUMN answer DROP NOT NULL;
```

5. 에러 없이 완료되면 설정 끝
6. 앱에서 학생이 공부 외 질문 후 → 학부모 AI 리포트 탭에서 이력 표시되는지 확인
