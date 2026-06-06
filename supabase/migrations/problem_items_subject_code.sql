-- 과목 차원 추가(GAP 1): 채점 시 분류한 과목 코드를 저장.
-- 진짜 '과목별 성취도'(과목별 실제 정답률)와 단원/개념 단위 취약점 분석의 기반.
-- KOREAN | ENGLISH | MATH | SCIENCE | SOCIAL | HISTORY | OTHER (lib/reasons.ts 와 동일)
ALTER TABLE problem_items ADD COLUMN IF NOT EXISTS subject_code text;

CREATE INDEX IF NOT EXISTS idx_problem_items_subject
ON problem_items (student_user_id, subject_code);

COMMENT ON COLUMN problem_items.subject_code IS '문제의 과목 코드(채점 시 LLM이 분류). 과목별 성취도·단원 취약점 분석에 사용.';

SELECT 'problem_items.subject_code 컬럼 추가 완료' AS result;
