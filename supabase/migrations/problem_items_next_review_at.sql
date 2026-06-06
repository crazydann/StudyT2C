-- 간격 반복(복습 큐): 다음 복습 예정 시각
-- next_review_at <= now() 인 오답 문항이 학생의 '오늘의 복습' 큐에 노출됨
-- fsrs_state(이미 추가됨)와 함께 lib/review.ts 의 간격 계산 결과를 저장
ALTER TABLE problem_items ADD COLUMN IF NOT EXISTS next_review_at timestamptz;

CREATE INDEX IF NOT EXISTS idx_problem_items_due
ON problem_items (student_user_id, next_review_at);

COMMENT ON COLUMN problem_items.next_review_at IS '다음 복습 예정 시각. 채점 시 오답이면 초기화되고, 복습 결과에 따라 lib/review.ts 가 갱신.';

SELECT 'problem_items.next_review_at 컬럼 추가 완료' AS result;
