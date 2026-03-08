-- MVP 로그인 학생용: id/pwd 로그인 시 비밀번호 저장
-- studyt2c.streamlit.app 배포에서 로그인 화면 사용 시 필요
ALTER TABLE users
ADD COLUMN IF NOT EXISTS password_hash text;

SELECT 'users.password_hash 컬럼 추가 완료' AS result;
