# ui/teacher/consult_tab.py
import streamlit as st

from ui.ui_common import format_ts_kst

from ui.ui_errors import show_error
from services.analytics_service import get_student_consultation_report

from ui.teacher.dev import render_dev_json
from ui.teacher.data_loaders import fetch_teacher_consult_logs, insert_teacher_consult_log, safe_json


def render_consult_tab(supabase, teacher_id: str, student_id: str):
    st.subheader("🧾 상담 리포트 (선생님용)")

    mode_key = f"t_consult_mode_{teacher_id}_{student_id}"
    if mode_key not in st.session_state:
        st.session_state[mode_key] = True
    st.toggle("🧑‍🏫 학부모 상담 모드", key=mode_key)
    consult_mode = bool(st.session_state.get(mode_key, True))

    try:
        report = get_student_consultation_report(student_id)
    except Exception as e:
        show_error("상담 리포트 생성 실패", e, context="get_student_consultation_report", show_trace=False)
        report = {"consult_script": "데이터를 불러오지 못했습니다."}

    st.markdown("#### 🗣️ 상담 스크립트(한 문단)")
    st.info(report.get("consult_script") or "")

    st.markdown("#### 📝 상담 로그 저장")
    default_one = (report.get("consult_script") or "").strip()
    if len(default_one) > 120:
        default_one = default_one[:120] + "..."

    one_liner = st.text_input("한 줄 요약(학부모에게 설명용)", value=default_one, key=f"t_one_{student_id}")
    note = st.text_area("선생님 메모(내부 기록)", value="", height=140, key=f"t_note_{student_id}")

    c1, c2 = st.columns([1, 3])
    with c1:
        if st.button("💾 상담 로그 저장", key=f"t_save_consult_{student_id}"):
            ok, err = insert_teacher_consult_log(
                supabase,
                teacher_id=teacher_id,
                student_id=student_id,
                one_liner=one_liner,
                note=note,
                snapshot=safe_json(report),
            )
            if ok:
                st.success("저장 완료 ✅")
                st.rerun()
            else:
                show_error("저장 실패", err, context="teacher_consultation_logs insert", show_trace=True)

    with c2:
        st.caption("상담 로그 저장 시, 학부모 화면에서도 요약/히스토리로 보이게 됩니다.")

    st.divider()

    st.markdown("#### 🗂️ 상담 로그 히스토리 (최근 10개)")
    logs = fetch_teacher_consult_logs(supabase, teacher_id, student_id, limit=10)
    if not logs:
        st.caption("저장된 상담 로그가 없습니다.")
        return

    options = []
    row_map = {}
    for row in logs:
        c_at = format_ts_kst(row.get("created_at"), with_seconds=True)
        ol = (row.get("one_liner") or "").strip()
        title = f"{c_at} · {ol}" if c_at else (ol if ol else str(row.get("id")))
        options.append(title)
        row_map[title] = row

    selected = st.selectbox("상담 로그 선택", options=options, index=0, key=f"t_consult_sel_{student_id}")
    row = row_map.get(selected) or logs[0]

    with st.expander("상담 로그 상세 보기", expanded=consult_mode):
        c_at = format_ts_kst(row.get("created_at"), with_seconds=True)
        if c_at:
            st.caption(f"일시: {c_at}")

        if row.get("one_liner"):
            st.markdown("**한 줄 요약**")
            st.info(row.get("one_liner"))

        if row.get("note"):
            st.markdown("**선생님 메모**")
            st.write(row.get("note"))

        snapshot = row.get("snapshot")
        if snapshot is not None and st.session_state.get("dev_mode", False):
            render_dev_json(
                "KPI 스냅샷",
                snapshot,
                key=f"t_consult_json_{student_id}_{row.get('id')}",
            )