# ui/student_dashboard/focus_tracker_component.py
"""
학생 대시보드에서 탭 이탈/복귀/닫기를 감지해 Supabase focus_events에 기록하는 스크립트 주입.
"""
import json
import streamlit as st


def render_focus_tracker(student_id: str, supabase_url: str, supabase_anon_key: str) -> None:
    """
    학생 화면에 focus_events 전송 스크립트를 넣습니다.
    - 탭이 보이지 않게 되면 left_tab
    - 다시 보이면 returned_tab
    - 탭/창 닫을 때 tab_closed (가능한 범위에서)
    """
    # HTML/JS 내부에 넣을 값 이스케이프 (따옴표, </script> 등)
    config = json.dumps({
        "student_id": student_id,
        "url": (supabase_url or "").rstrip("/") + "/rest/v1/focus_events",
        "key": supabase_anon_key or "",
    })
    config_escaped = config.replace("\\", "\\\\").replace("</", "<\\/").replace("-->", "--\\>")

    html = f"""
<script>
(function() {{
  var config = {config_escaped};
  if (!config.url || !config.key) return;
  function send(eventType) {{
    var body = JSON.stringify({{
      student_user_id: config.student_id,
      event_type: eventType
    }});
    var opts = {{
      method: 'POST',
      headers: {{
        'apikey': config.key,
        'Authorization': 'Bearer ' + config.key,
        'Content-Type': 'application/json',
        'Prefer': 'return=minimal'
      }},
      body: body
    }};
    fetch(config.url, opts).catch(function() {{}});
  }}
  document.addEventListener('visibilitychange', function() {{
    if (document.hidden) send('left_tab');
    else send('returned_tab');
  }});
  window.addEventListener('beforeunload', function() {{
    var body = JSON.stringify({{ student_user_id: config.student_id, event_type: 'tab_closed' }});
    fetch(config.url, {{ method: 'POST', headers: {{ 'apikey': config.key, 'Authorization': 'Bearer ' + config.key, 'Content-Type': 'application/json' }}, body: body, keepalive: true }}).catch(function() {{}});
  }});
}})();
</script>
"""
    st.components.v1.html(html, height=0)
