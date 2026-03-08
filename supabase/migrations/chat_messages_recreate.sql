-- ============================================================
-- chat_messages 테이블 새로 만들기 (코드와 1:1 일치)
-- 기존 데이터는 모두 삭제됩니다. Supabase SQL Editor에서 실행하세요.
-- ============================================================

-- 1) 기존 테이블 삭제
DROP TABLE IF EXISTS chat_messages;

-- 2) 새 테이블 생성 (코드가 사용하는 컬럼만)
CREATE TABLE chat_messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  student_user_id text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  role text NOT NULL DEFAULT 'user',
  content text NOT NULL,
  meta jsonb
);

-- 3) RLS
ALTER TABLE chat_messages ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow insert chat_messages" ON chat_messages;
CREATE POLICY "Allow insert chat_messages"
ON chat_messages FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Allow select chat_messages" ON chat_messages;
CREATE POLICY "Allow select chat_messages"
ON chat_messages FOR SELECT USING (true);

-- 4) 인덱스 (학부모/분석 조회용)
CREATE INDEX IF NOT EXISTS idx_chat_messages_student_created
ON chat_messages (student_user_id, created_at DESC);

SELECT 'chat_messages 테이블 재생성 완료' AS result;
