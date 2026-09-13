-- 퀴즈 시도 정확 매칭: concept_review_attempts에 quiz_id 추가
-- (기존엔 quiz_question 텍스트로 매칭 → LLM이 동일 문항을 생성하면 시도 결과가 엉뚱한 퀴즈에 귀속)
-- 멱등·안전. 컬럼이 없어도 앱은 graceful하게 동작하며, 적용 후 새 시도부터 정확히 매칭됨.
ALTER TABLE concept_review_attempts ADD COLUMN IF NOT EXISTS quiz_id uuid;

CREATE INDEX IF NOT EXISTS idx_cra_student_quiz
  ON concept_review_attempts (student_user_id, quiz_id);

SELECT 'concept_review_attempts.quiz_id 컬럼 추가 완료' AS result;
