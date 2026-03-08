from datetime import datetime, timezone, timedelta
import streamlit as st

# 대한민국 표준시 (UTC+9) — UI에 표기되는 모든 시간 기준
KST = timezone(timedelta(hours=9))


def format_ts_kst(ts: str | None, with_seconds: bool = False) -> str:
    """
    DB 등에서 오는 ISO 타임스탬프(UTC)를 대한민국 시간(KST)으로 변환해 표시용 문자열로 반환.
    ts: ISO 형식 또는 "YYYY-MM-DD HH:MM:SS" 등
    with_seconds: True면 "YYYY-MM-DD HH:MM:SS", False면 "YYYY-MM-DD HH:MM"
    """
    if not ts:
        return "—"
    try:
        s = (ts if isinstance(ts, str) else str(ts)).strip()
        s = s.replace("Z", "+00:00")
        if "T" not in s and " " in s and "+" not in s and "Z" not in s:
            s = s.replace(" ", "T", 1) + "+00:00"
        elif "T" not in s and len(s) >= 16:
            s = s[:10] + "T" + s[11:19] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        kst_dt = dt.astimezone(KST)
        fmt = "%Y-%m-%d %H:%M:%S" if with_seconds else "%Y-%m-%d %H:%M"
        return kst_dt.strftime(fmt)
    except Exception:
        return (str(ts)[:19].replace("T", " ") if ts else "—")


def format_ts_short(ts: str | None) -> str:
    """날짜만 M/D/YYYY 형식 (예: 3/7/2026)."""
    if not ts:
        return "—"
    try:
        s = (ts if isinstance(ts, str) else str(ts)).strip().replace("Z", "+00:00")
        if "T" not in s and " " in s:
            s = s.replace(" ", "T", 1) + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        kst_dt = dt.astimezone(KST)
        return f"{kst_dt.month}/{kst_dt.day}/{kst_dt.year}"
    except Exception:
        try:
            return str(ts)[:10].replace("-", "/")
        except Exception:
            return "—"


def st_image_fullwidth(img_bytes_or_url):
    """
    Streamlit 버전 호환용 이미지 렌더링.
    - 신버전: use_container_width
    - 구버전: use_column_width
    """
    try:
        st.image(img_bytes_or_url, use_container_width=True)
    except TypeError:
        st.image(img_bytes_or_url, use_column_width=True)


def get_role_state(role_key: str, user_id: str) -> dict:
    """
    ✅ 역할(teacher/parent 등) + 유저별 session_state 분리 헬퍼
    - role_key 예: "teacher", "parent"
    - user_id: 현재 로그인한 유저 id

    return: 해당 유저의 state dict
    """
    root_key = f"{role_key}_states"
    if root_key not in st.session_state:
        st.session_state[root_key] = {}

    states = st.session_state[root_key]
    if user_id not in states:
        states[user_id] = {}
    return states[user_id]