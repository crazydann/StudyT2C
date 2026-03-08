-- chat_messages 테이블: 공부 외 질문 이력 저장용 스키마 설정
-- Supabase SQL Editor에서 이 파일 전체를 복사해 실행하세요.

-- 1. role, content 컬럼 추가 (없는 경우)
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS role text;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS content text;

-- 2. meta 컬럼 추가 (없는 경우)
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS meta jsonb;

-- 3. session_id를 nullable로 변경 (service_role insert 시 필요 없도록)
-- session_id가 chat_sessions FK를 참조하면, 랜덤 UUID 대신 null 허용으로 저장 가능
ALTER TABLE chat_messages ALTER COLUMN session_id DROP NOT NULL;

-- 4. question, answer를 nullable로 변경 (role/content 방식으로도 저장 가능하도록)
ALTER TABLE chat_messages ALTER COLUMN question DROP NOT NULL;
ALTER TABLE chat_messages ALTER COLUMN answer DROP NOT NULL;
