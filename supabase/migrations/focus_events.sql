-- 탭 이탈/복귀/닫기 감지: 학생이 우리 서비스 탭을 벗어났는지 기록
-- event_type: left_tab | returned_tab | tab_closed
CREATE TABLE IF NOT EXISTS focus_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  student_user_id text NOT NULL,
  event_type text NOT NULL CHECK (event_type IN ('left_tab', 'returned_tab', 'tab_closed')),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_focus_events_student_created
ON focus_events (student_user_id, created_at DESC);

ALTER TABLE focus_events ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Allow insert focus_events" ON focus_events;
CREATE POLICY "Allow insert focus_events" ON focus_events FOR INSERT WITH CHECK (true);

DROP POLICY IF EXISTS "Allow select focus_events" ON focus_events;
CREATE POLICY "Allow select focus_events" ON focus_events FOR SELECT USING (true);

-- 탭 이탈 알람 이메일 쿨다운 (같은 학생당 15분에 1회)
CREATE TABLE IF NOT EXISTS focus_alert_sent (
  student_user_id text PRIMARY KEY,
  last_sent_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE focus_alert_sent ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS "Allow all focus_alert_sent" ON focus_alert_sent;
CREATE POLICY "Allow all focus_alert_sent" ON focus_alert_sent FOR ALL USING (true) WITH CHECK (true);

SELECT 'focus_events 및 focus_alert_sent 테이블 생성 완료' AS result;
