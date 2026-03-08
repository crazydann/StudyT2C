-- 질의개념복습 풀이 이력: 출제된 문제·선택한 답·정오답 기록 (취약점 분석용)
CREATE TABLE IF NOT EXISTS concept_review_attempts (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  student_user_id text NOT NULL,
  source_question text,
  source_answer text,
  quiz_question text NOT NULL,
  correct_index int NOT NULL,
  user_choice_index int NOT NULL,
  is_correct boolean NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_concept_review_student_created
ON concept_review_attempts (student_user_id, created_at DESC);

ALTER TABLE concept_review_attempts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all concept_review_attempts" ON concept_review_attempts;
CREATE POLICY "Allow all concept_review_attempts" ON concept_review_attempts
FOR ALL USING (true) WITH CHECK (true);

SELECT 'concept_review_attempts 테이블 생성 완료' AS result;
