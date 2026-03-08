-- 질의개념복습에서 만든 문제 저장 (지난 문제들 목록·재풀이용)
CREATE TABLE IF NOT EXISTS concept_review_quizzes (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  student_user_id text NOT NULL,
  source_question text,
  source_answer text,
  quiz_question text NOT NULL,
  options jsonb NOT NULL DEFAULT '[]',
  correct_index int NOT NULL DEFAULT 0,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_concept_review_quizzes_student_created
ON concept_review_quizzes (student_user_id, created_at DESC);

ALTER TABLE concept_review_quizzes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all concept_review_quizzes" ON concept_review_quizzes;
CREATE POLICY "Allow all concept_review_quizzes" ON concept_review_quizzes
FOR ALL USING (true) WITH CHECK (true);

SELECT 'concept_review_quizzes 테이블 생성 완료' AS result;
