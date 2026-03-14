# ui/student_dashboard/focus_tracker_component.py
"""
학생 대시보드에서 탭 이탈/복귀/닫기를 감지해 Supabase focus_events에 기록하고,
화면을 다시 활성화했을 때 팝업으로 안내하는 스크립트 주입.
"""
import json
import streamlit as st


def render_focus_tracker(student_id: str, supabase_url: str, supabase_anon_key: str) -> None:
    """
    학생 화면에 focus_events 전송 + 탭 복귀 시 팝업 스크립트를 넣습니다.
    - 탭이 보이지 않게 되면 left_tab
    - 다시 보이면 returned_tab + 팝업(학습 화면을 벗어났던 안내)
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
  var wasHidden = false;
  function send(eventType) {{
    var body = JSON.stringify({{ student_user_id: config.student_id, event_type: eventType }});
    var opts = {{ method: 'POST', headers: {{ 'apikey': config.key, 'Authorization': 'Bearer ' + config.key, 'Content-Type': 'application/json', 'Prefer': 'return=minimal' }}, body: body }};
    fetch(config.url, opts).catch(function() {{}});
  }}
  function showReturnPopup() {{
    var msg = '학습 화면을 잠시 벗어났습니다. 다시 집중해 주세요.';
    try {{
      var doc = (window.parent && window.parent.document) ? window.parent.document : document;
      var root = doc.body || doc.documentElement;
      var m = doc.getElementById('studyt2c-focus-return-popup');
      if (m) {{ m.style.display = 'flex'; return; }}
      var modal = doc.createElement('div');
      modal.id = 'studyt2c-focus-return-popup';
      modal.style.cssText = 'position:fixed;inset:0;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:999999;font-family:system-ui,sans-serif;';
      modal.innerHTML = '<div style="background:#fff;padding:24px;border-radius:12px;max-width:320px;box-shadow:0 8px 24px rgba(0,0,0,0.2);text-align:center;">' +
        '<p style="margin:0 0 16px;font-size:1rem;">학습 화면을 잠시 벗어났습니다.<br>다시 집중해 주세요.</p>' +
        '<button type="button" style="padding:10px 24px;border:none;border-radius:8px;background:#16a34a;color:#fff;font-weight:600;cursor:pointer;">확인</button></div>';
      modal.onclick = function(e) {{ if (e.target === modal) {{ modal.style.display = 'none'; }} }};
      var btn = modal.querySelector('button');
      if (btn) btn.onclick = function(e) {{ e.stopPropagation(); modal.style.display = 'none'; }};
      var inner = modal.querySelector('div');
      if (inner) inner.onclick = function(e) {{ e.stopPropagation(); }};
      root.appendChild(modal);
    }} catch (err) {{
      try {{ alert(msg); }} catch (e) {{}}
    }}
  }}
  function onVisibilityChange(hidden) {{
    if (hidden) {{
      wasHidden = true;
      send('left_tab');
    }} else {{
      if (wasHidden) {{
        send('returned_tab');
        showReturnPopup();
        wasHidden = false;
      }}
    }}
  }}
  document.addEventListener('visibilitychange', function() {{ onVisibilityChange(document.hidden); }});
  try {{
    var pd = window.parent && window.parent.document;
    if (pd && pd !== document) pd.addEventListener('visibilitychange', function() {{ onVisibilityChange(pd.hidden); }});
  }} catch (e) {{}}
  window.addEventListener('beforeunload', function() {{
    var body = JSON.stringify({{ student_user_id: config.student_id, event_type: 'tab_closed' }});
    fetch(config.url, {{ method: 'POST', headers: {{ 'apikey': config.key, 'Authorization': 'Bearer ' + config.key, 'Content-Type': 'application/json' }}, body: body, keepalive: true }}).catch(function() {{}});
  }});
}})();
</script>
"""
    st.components.v1.html(html, height=0)
