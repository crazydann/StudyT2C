# ui/student_dashboard/panels_history.py
import streamlit as st

from services.db_service import list_grading_submissions, get_submission_items
from ui.ui_common import format_ts_kst
from ui.ui_errors import show_error


def render_history_panel(student_id: str, user: dict) -> None:
    st.subheader("🕘 최근 채점 기록")

    try:
        subs = list_grading_submissions(student_id, limit=10)
    except Exception as e:
        show_error("최근 채점 기록 로드 실패", e, context="list_grading_submissions", show_trace=False)
        subs = []

    if not subs:
        st.caption("최근 채점 기록이 없습니다.")
        return

    labels = []
    id_by_label = {}

    for s in subs:
        created = format_ts_kst(s.get("created_at") or s.get("uploaded_at"), with_seconds=True)
        fh = str(s.get("file_hash", ""))[:8]
        sub_id = s.get("id")

        label = f"{created} · {fh}"
        if sub_id:
            try:
                items = get_submission_items(str(sub_id), limit=300)
                total = len(items)
                wrong = sum(1 for it in items if it.get("is_correct") is False)
                if total > 0:
                    label = f"{created} · 오답 {wrong}/{total} · {fh}"
            except Exception:
                pass

        labels.append(label)
        if sub_id:
            id_by_label[label] = str(sub_id)

    if not id_by_label:
        st.caption("채점 기록을 표시할 수 없습니다.")
        return

    sel = st.selectbox("기록 선택", options=labels, key=f"hist_sel_{student_id}")
    sub_id = id_by_label.get(sel)
    if not sub_id:
        st.caption("선택한 기록을 찾을 수 없습니다.")
        return

    try:
        items = get_submission_items(sub_id)
    except Exception as e:
        show_error("채점 상세 로드 실패", e, context="get_submission_items", show_trace=False)
        items = []

    if not items:
        st.caption("선택한 기록에 문항이 없습니다.")
        return

    wrong_first = sorted(items, key=lambda x: (bool(x.get("is_correct")) is True, x.get("item_no") or 0))
    for it in wrong_first:
        is_corr = bool(it.get("is_correct"))
        no = it.get("item_no") or 0
        with st.expander(f"{no}번 ({'🟢' if is_corr else '🔴'})", expanded=not is_corr):
            st.write(it.get("explanation_summary"))
            kc = it.get("key_concepts") or []
            if kc:
                st.caption("핵심 개념: " + ", ".join(kc))
            if user.get("detail_permission") and it.get("explanation_detail"):
                st.info(it.get("explanation_detail"))