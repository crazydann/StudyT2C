import streamlit as st
from typing import Any, Dict, List, Optional, Callable

from ui.ui_errors import show_error
from ui.ui_common import format_ts_kst
from services.db_service import (
    list_grading_submissions,
    get_submission_items,
)


def _pick_dt(row: Dict[str, Any]) -> str:
    """uploaded_at / created_at 중 존재하는 날짜 표시"""
    return (
        str(row.get("uploaded_at") or "")
        or str(row.get("created_at") or "")
        or str(row.get("updated_at") or "")
        or ""
    )


def _submission_title(row: Dict[str, Any]) -> str:
    fname = row.get("file_name") or row.get("filename") or row.get("name") or "제출물"
    dt = _pick_dt(row)
    if dt:
        return f"{fname}  ·  {format_ts_kst(dt, with_seconds=True)}"
    return str(fname)


def _render_submission_summary(items: List[Dict[str, Any]]):
    total = len(items)
    wrong = sum(1 for it in items if it.get("is_correct") is False)
    correct = sum(1 for it in items if it.get("is_correct") is True)
    unknown = total - wrong - correct

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("문항 수", total)
    c2.metric("정답", correct)
    c3.metric("오답", wrong)
    c4.metric("미판정", unknown)


def _render_items_table(items: List[Dict[str, Any]], limit: int = 60):
    """너무 길어지지 않게 상위 limit개만 표로 보여줌"""
    rows = []
    for it in items[:limit]:
        rows.append(
            {
                "번호": it.get("item_no"),
                "정오": "⭕" if it.get("is_correct") is True else ("❌" if it.get("is_correct") is False else "-"),
                "개념": ", ".join(it.get("key_concepts") or []) if isinstance(it.get("key_concepts"), list) else (it.get("key_concepts") or ""),
                "오답원인": it.get("reason_category") or "",
                "요약": (it.get("explanation_summary") or "")[:80],
            }
        )
    if rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.caption("표시할 문항이 없습니다.")


def render_student_history(
    supabase,
    user: Dict[str, Any],
    student_id: str,
    state: Optional[Dict[str, Any]] = None,
    st_image_fullwidth: Optional[Callable[..., Any]] = None,
):
    """
    학생 - 기록 화면

    ui/ui_student.py에서 다음처럼 호출하는 호환을 위해 st_image_fullwidth 인자를 받는다:
      render_student_history(..., st_image_fullwidth=_st_image_fullwidth)

    현재 이 화면에서는 이미지를 직접 렌더링하지 않아도 되므로 사용하지 않아도 된다.
    """
    st.header("기록")

    # 1) 제출 목록 로드
    try:
        subs = list_grading_submissions(student_id, limit=30)
    except Exception as e:
        show_error("채점 제출 목록 로드 실패", e, context="list_grading_submissions", show_trace=True)
        return

    # ✅ 핵심: 데이터 0건이면 에러가 아니라 안내
    if not subs:
        st.info("아직 채점한 숙제가 없어요. 숙제를 제출하고 채점을 진행해보세요 🙂")
        st.caption("👉 **대시보드** 탭에서 오른쪽 **문제 채점기**로 이동해 이미지/PDF를 올리고 **AI 채점 요청**을 하면 여기에 기록이 쌓여요.")
        return

    st.subheader("채점 히스토리")

    # 2) 제출 선택 UI (라디오)
    options = [(_submission_title(s), str(s.get("id"))) for s in subs if s.get("id")]
    if not options:
        st.info("제출 데이터는 있지만 id가 없어 표시할 수 없어요. (DB 스키마 확인 필요)")
        return

    label_list = [o[0] for o in options]
    id_list = [o[1] for o in options]

    # 세션 키
    key = f"student_history_selected_{student_id}"
    default_idx = 0
    if key in st.session_state and st.session_state[key] in id_list:
        default_idx = id_list.index(st.session_state[key])

    selected_id = st.radio(
        "제출물 선택",
        id_list,
        index=default_idx,
        format_func=lambda x: label_list[id_list.index(x)],
        key=key,
    )

    # 선택된 row 찾기
    selected_row = None
    for s in subs:
        if str(s.get("id")) == str(selected_id):
            selected_row = s
            break

    if not selected_row:
        st.warning("선택된 제출물을 찾지 못했습니다.")
        return

    # 3) 선택 제출물 기본 정보
    st.markdown("### 제출 정보")
    c1, c2 = st.columns(2)
    with c1:
        st.write("파일명:", selected_row.get("file_name") or selected_row.get("filename") or "-")
        st.write("제출일:", _pick_dt(selected_row) or "-")
    with c2:
        storage_url = selected_row.get("storage_url")
        if storage_url:
            st.link_button("제출 파일 열기", storage_url)
        else:
            st.caption("파일 링크가 없습니다.")

    st.divider()

    # 4) 문항 로드 & 요약
    st.markdown("### 채점 요약")
    try:
        items = get_submission_items(str(selected_id), limit=500)
    except Exception as e:
        show_error("채점 문항 로드 실패", e, context="get_submission_items", show_trace=True)
        return

    if not items:
        st.info("이 제출물에는 저장된 문항 데이터가 아직 없어요.")
        return

    _render_submission_summary(items)

    with st.expander("문항 목록 보기", expanded=False):
        _render_items_table(items, limit=80)