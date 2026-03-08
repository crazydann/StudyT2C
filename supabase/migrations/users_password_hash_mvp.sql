-- MVP 로그인 학생용: id/pwd 로그인 시 비밀번호 저장
-- studyt2c.streamlit.app 배포에서 로그인 화면 사용 시 필요
ALTER TABLE users
ADD COLUMN IF NOT EXISTS password_hash text;

-- david / joshua 비밀번호 = 아이디와 동일 (salt: studyt2c-mvp-2025)
-- SERVICE_ROLE_KEY 없이도 로그인 가능하도록 여기서 한 번 설정
UPDATE users SET password_hash = '7c5f73cbcdf1c9eb993ce56c5363570ee141e56af1fb0f5577724485be912bb8', role = 'student'
WHERE LOWER(TRIM(handle)) = 'david';

UPDATE users SET password_hash = '17613eeb15b8b1937e21a2ffa5b76e591cf7996484cf8e638d74419d616f56dd', role = 'student'
WHERE LOWER(TRIM(handle)) = 'joshua';

-- handle이 david/joshua인 행이 없으면 삽입 (id는 gen_random_uuid 사용)
INSERT INTO users (handle, role, status, password_hash)
SELECT 'david', 'student', 'break', '7c5f73cbcdf1c9eb993ce56c5363570ee141e56af1fb0f5577724485be912bb8'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE LOWER(TRIM(handle)) = 'david');

INSERT INTO users (handle, role, status, password_hash)
SELECT 'joshua', 'student', 'break', '17613eeb15b8b1937e21a2ffa5b76e591cf7996484cf8e638d74419d616f56dd'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE LOWER(TRIM(handle)) = 'joshua');

SELECT 'users.password_hash 컬럼 및 david/joshua 비밀번호 설정 완료' AS result;
