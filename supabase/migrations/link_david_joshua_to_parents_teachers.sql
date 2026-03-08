-- david, joshua를 모든 학부모·선생님과 연결해 부모/선생 화면에서 다른 학생처럼 보이게 함
-- (이미 연결된 조합은 건너뜀)

-- 학부모: david, joshua를 모든 parent 역할 사용자와 연결
INSERT INTO parent_student_links (parent_user_id, student_user_id)
SELECT p.id, s.id
FROM users p
CROSS JOIN (SELECT id FROM users WHERE LOWER(TRIM(handle)) IN ('david', 'joshua')) s
WHERE p.role = 'parent'
  AND NOT EXISTS (
    SELECT 1 FROM parent_student_links l
    WHERE l.parent_user_id = p.id AND l.student_user_id = s.id
  );

-- 선생님: david, joshua를 모든 teacher 역할 사용자와 연결
INSERT INTO teacher_student_links (teacher_user_id, student_user_id)
SELECT t.id, s.id
FROM users t
CROSS JOIN (SELECT id FROM users WHERE LOWER(TRIM(handle)) IN ('david', 'joshua')) s
WHERE t.role = 'teacher'
  AND NOT EXISTS (
    SELECT 1 FROM teacher_student_links l
    WHERE l.teacher_user_id = t.id AND l.student_user_id = s.id
  );

SELECT 'david/joshua 학부모·선생님 연결 완료' AS result;
