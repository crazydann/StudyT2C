-- 1) users 테이블에 notification_email 컬럼 추가
ALTER TABLE users
ADD COLUMN IF NOT EXISTS notification_email text;

-- 2) 학부모 한 명에 수동으로 알림 이메일 설정 (role='parent'인 첫 번째 사용자)
UPDATE users
SET notification_email = 'dannyhos@naver.com'
WHERE id = (
  SELECT id FROM users WHERE role = 'parent' LIMIT 1
);

-- 3) 이메일 수신 설정 테이블 (학부모/선생님별, 학생별)
--    수신 여부, 항목(공부외질문/주간리포트 등), 주기(실시간/일/주/월)
CREATE TABLE IF NOT EXISTS notification_settings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id text NOT NULL,
  student_user_id text NOT NULL,
  role text NOT NULL CHECK (role IN ('parent', 'teacher')),
  email_enabled boolean NOT NULL DEFAULT true,
  receive_offtopic boolean NOT NULL DEFAULT true,
  receive_weekly_report boolean NOT NULL DEFAULT false,
  receive_daily_summary boolean NOT NULL DEFAULT false,
  frequency text NOT NULL DEFAULT 'realtime' CHECK (frequency IN ('realtime', 'daily', 'weekly', 'monthly')),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (user_id, student_user_id)
);

CREATE INDEX IF NOT EXISTS idx_notification_settings_user_student
ON notification_settings (user_id, student_user_id);
CREATE INDEX IF NOT EXISTS idx_notification_settings_student
ON notification_settings (student_user_id);

ALTER TABLE notification_settings ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow all notification_settings" ON notification_settings;
CREATE POLICY "Allow all notification_settings" ON notification_settings
FOR ALL USING (true) WITH CHECK (true);

-- updated_at 자동 갱신 트리거
CREATE OR REPLACE FUNCTION notification_settings_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS notification_settings_updated_at ON notification_settings;
CREATE TRIGGER notification_settings_updated_at
  BEFORE UPDATE ON notification_settings
  FOR EACH ROW EXECUTE PROCEDURE notification_settings_updated_at();

SELECT 'notification_email 컬럼 및 notification_settings 테이블 생성 완료' AS result;
