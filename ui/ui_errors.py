# ui/ui_errors.py
import streamlit as st
import traceback
import hashlib


def _mk_key(prefix: str, text: str) -> str:
    h = hashlib.md5((text or "").encode("utf-8")).hexdigest()[:10]
    return f"{prefix}_{h}"


def _format_trace(err: Exception) -> str:
    """
    format_exc() 대신 err.__traceback__ 기반으로 항상 안정적으로 문자열을 만든다.
    (rerun 이후에도 저장해둔 문자열은 그대로 표시 가능)
    """
    try:
        return "".join(traceback.format_exception(type(err), err, err.__traceback__))
    except Exception:
        return f"{type(err).__name__}: {err}"


def show_error(
    title: str,
    err: Exception,
    context: str = "",
    show_trace: bool = True,
    *,
    persist_key: str | None = None,
    persist: bool = True,
    trace_text: str | None = None,
):
    """
    ✅ expander 없이 에러 표시
    ✅ checkbox 클릭으로 rerun 되어도, persist=True면 마지막 에러를 세션에 저장/복원
    """
    # 저장 키(같은 에러 컨텍스트면 같은 키로 유지)
    base = persist_key or f"{title}|{context}"
    store_key = _mk_key("last_err", base)

    # 에러 텍스트 준비
    tb_text = trace_text or _format_trace(err)
    err_summary = f"{type(err).__name__}: {err}"

    # 1) 세션에 저장 (rerun 후에도 남게)
    if persist:
        st.session_state[store_key] = {
            "title": title,
            "context": context,
            "summary": err_summary,
            "trace": tb_text,
        }

    # 2) 현재 표시할 데이터 결정(저장된 값 우선)
    data = st.session_state.get(store_key) if persist else None
    if not data:
        data = {"title": title, "context": context, "summary": err_summary, "trace": tb_text}

    # 3) UI 출력
    st.error(f"❌ {data['title']}")
    if data.get("context"):
        st.caption(f"Context: {data['context']}")

    if not show_trace:
        return

    # 상세보기 토글 (checkbox = rerun 이지만, 위에서 persist 해놔서 안 사라짐)
    ckey = _mk_key("err_trace", store_key)
    checked = st.checkbox("상세 오류 보기 (개발용)", value=False, key=ckey)
    if not checked:
        return

    # 코드 블록에는 복사 버튼이 떠서 여기서 복사 가능
    st.code(data.get("trace") or data.get("summary") or "", language="text")