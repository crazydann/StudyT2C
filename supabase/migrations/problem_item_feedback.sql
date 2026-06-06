-- 메타인지 피드백: 학생이 오답 문항에 대해 스스로 평가한 이해도/원인
-- 원본 Streamlit services/db/feedback.py 의 권장 스키마를 Next.js 로 복원
CREATE TABLE IF NOT EXISTS problem_item_feedback (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  student_user_id text NOT NULL,
  problem_item_id uuid NOT NULL,
  submission_id uuid,
  understanding text NOT NULL DEFAULT 'confused', -- 'understood' | 'confused'
  reason_category text,                            -- concept|calculation|reading|time|guessing|null
  memo text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (student_user_id, problem_item_id)
);

CREATE INDEX IF NOT EXISTS idx_pif_student_created
ON problem_item_feedback (student_user_id, created_at DESC);

ALTER TABLE problem_item_feedback ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all problem_item_feedback" ON problem_item_feedback;
CREATE POLICY "Allow all problem_item_feedback" ON problem_item_feedback
FOR ALL USING (true) WITH CHECK (true);

SELECT 'problem_item_feedback 테이블 생성 완료' AS result;
