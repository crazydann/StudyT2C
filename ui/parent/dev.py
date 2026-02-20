# ui/parent/dev.py
import json
import streamlit as st


def render_dev_json(title: str, data, key: str):
    """
    개발 모드에서만 JSON 원문을 보여주는 헬퍼.
    Streamlit expander 중첩 이슈를 피하려고 checkbox로 토글함.
    """
    if not st.session_state.get("dev_mode", False):
        return

    checked = st.checkbox(f"🧪 개발용: {title} JSON 보기", value=False, key=key)
    if checked:
        try:
            st.code(json.dumps(data, ensure_ascii=False, indent=2), language="json")
        except Exception:
            st.write(data)