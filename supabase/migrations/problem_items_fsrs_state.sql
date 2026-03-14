-- FSRS 복습 스케줄: 카드 상태 저장 (선택 컬럼)
-- 있으면 record_review_attempt에서 FSRS 알고리즘으로 next_review_at 계산
ALTER TABLE problem_items ADD COLUMN IF NOT EXISTS fsrs_state jsonb;

COMMENT ON COLUMN problem_items.fsrs_state IS 'FSRS card state (optional). When set, next_review_at is computed by FSRS.';
