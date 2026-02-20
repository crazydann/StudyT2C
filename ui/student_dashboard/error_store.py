# ui/student_dashboard/error_store.py
from __future__ import annotations

import time
import traceback
from typing import Any, Dict, Optional

import streamlit as st


def _key(student_id: str) -> str:
    return f"last_error_student_dashboard_{student_id}"


def _now_ts() -> float:
    return time.time()


def _make_trace(err: Exception) -> str:
    """
    ✅ format_exc()는 except 블록 밖이면 빈 문자열이 될 수 있음.
    그래서 err.__traceback__ 기반으로 fallback trace도 항상 만든다.
    """
    # 1) 현재 예외 컨텍스트 기반 (except 블록 안이면 가장 정확)
    try:
        tb1 = traceback.format_exc()
    except Exception:
        tb1 = ""

    # 2) 전달된 err 기반 fallback
    try:
        tb2 = "".join(traceback.format_exception(type(err), err, err.__traceback__))
    except Exception:
        tb2 = f"{type(err).__name__}: {err}"

    # tb1이 유효하면 tb1 우선, 아니면 tb2
    if tb1 and "Traceback" in tb1:
        return tb1
    return tb2


def persist_last_error(student_id: str, title: str, context: str, err: Exception, extra: Optional[Dict[str, Any]] = None) -> None:
    """
    ✅ rerun되어도 남는 에러 저장소.
    - trace는 항상 비지 않도록 보장(_make_trace)
    - count/timestamp로 마지막 에러가 갱신되는지 확인 가능
    """
    k = _key(student_id)
    prev = st.session_state.get(k) or {}
    cnt = int(prev.get("count") or 0) + 1

    st.session_state[k] = {
        "title": title,
        "context": context,
        "err_type": type(err).__name__,
        "err_msg": str(err),
        "trace": _make_trace(err),
        "ts": _now_ts(),
        "count": cnt,
        "extra": extra or {},
    }


def clear_last_error(student_id: str) -> None:
    st.session_state.pop(_key(student_id), None)


def render_persisted_error(student_id: str) -> None:
    """
    ✅ 화면에 '지속 에러' 표시 + 복사/다운로드 가능하게 렌더링
    - 체크박스 클릭으로 rerun되어도 session_state에 남아 계속 보인다.
    """
    k = _key(student_id)
    data = st.session_state.get(k)
    if not data:
        return

    title = data.get("title") or "오류"
    context = data.get("context") or ""
    err_type = data.get("err_type") or "Exception"
    err_msg = data.get("err_msg") or ""
    trace = data.get("trace") or f"{err_type}: {err_msg}"
    ts = data.get("ts")
    count = data.get("count", 1)

    st.error(f"❌ {title}")
    if context:
        st.caption(f"Context: {context}")

    # dev_mode 아니면 요약만
    if not bool(st.session_state.get("dev_mode", False)):
        return

    # 메타 정보(선택)
    with st.container(border=True):
        meta_line = f"occurrences: {count}"
        if isinstance(ts, (int, float)):
            meta_line += f" · last_ts: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))}"
        st.caption(meta_line)

        show = st.checkbox("상세 오류 보기 (개발용)", value=False, key=f"{k}_toggle")
        if show:
            # ✅ 1) 코드블록(복사 버튼이 UI에 뜨는 경우가 많음)
            st.code(trace, language="text")

            # ✅ 2) 텍스트 영역(무조건 드래그/복사 가능)
            st.text_area("Trace(복사용)", value=trace, height=220, key=f"{k}_ta")

            # ✅ 3) 파일로 다운로드
            st.download_button(
                "trace.txt 다운로드",
                data=trace.encode("utf-8"),
                file_name=f"{k}.trace.txt",
                mime="text/plain",
                key=f"{k}_dl",
            )

            # extra 디버그(있으면)
            extra = data.get("extra") or {}
            if extra:
                st.caption("extra debug")
                st.json(extra)

        # clear 버튼(원할 때만)
        if st.button("오류 메시지 지우기", key=f"{k}_clear"):
            clear_last_error(student_id)
            st.rerun()