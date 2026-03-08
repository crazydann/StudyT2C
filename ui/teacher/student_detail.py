# ui/teacher/student_detail.py
import streamlit as st

from ui.ui_errors import show_error
from shared_summary import render_shared_summary

from ui.teacher.consult_tab import render_consult_tab
from ui.teacher.homework_tab import render_homework_tab
from ui.teacher.ai_report_tab import render_teacher_ai_report_tab
from ui.teacher.data_loaders import fetch_teacher_notification_email, update_teacher_notification_email
from services.notification_settings_service import (
    fetch_notification_settings,
    upsert_notification_settings,
    FREQUENCY_OPTIONS,
)


def render_student_detail(supabase, teacher_id: str, state: dict, handle_map: dict):
    sel = state.get("selected_student")

    if isinstance(sel, dict):
        student_id = sel.get("id")
        student_handle = sel.get("handle") or (handle_map.get(student_id) if student_id else None) or "student"
    else:
        student_id = sel
        student_handle = handle_map.get(str(student_id)) or "student"

    if not student_id:
        st.warning("학생이 선택되지 않았습니다.")
        return

    top = st.columns([1, 3, 1])
    with top[0]:
        if st.button("🔙 목록으로", key="t_back"):
            state["selected_student"] = None
            st.rerun()
    with top[1]:
        st.markdown(f"## 🎓 {student_handle} (학생 상세)")
    with top[2]:
        st.caption(" ")

    st.markdown("### 📧 이메일 알림 설정")
    current_email = fetch_teacher_notification_email(supabase, teacher_id)
    notify_email = st.text_input(
        "알림 수신 이메일 주소",
        value=current_email,
        placeholder="example@email.com",
        key=f"t_notify_email_{student_id}",
        help="이 주소로 학생 관련 알림 메일이 발송됩니다.",
    )
    if st.button("이메일 주소 저장", key=f"t_save_notify_{student_id}"):
        if update_teacher_notification_email(supabase, teacher_id, notify_email or ""):
            st.success("이메일 주소가 저장되었어요.")
            st.rerun()
        else:
            st.warning("저장에 실패했습니다. 잠시 후 다시 시도해 주세요.")

    st.markdown("#### 이 학생에 대한 수신 설정")
    settings = fetch_notification_settings(supabase, teacher_id, str(student_id))
    email_enabled = st.toggle("이 학생에 대한 이메일 알림 받기", value=settings.get("email_enabled", True), key=f"t_email_on_{student_id}")
    receive_offtopic = st.checkbox("공부 외 질문 알림 (수업 중 잡담·게임 등)", value=settings.get("receive_offtopic", True), key=f"t_offtopic_{student_id}")
    receive_weekly_report = st.checkbox("주간 학습 리포트 (준비 중)", value=settings.get("receive_weekly_report", False), key=f"t_weekly_{student_id}")
    receive_daily_summary = st.checkbox("일일 요약 (준비 중)", value=settings.get("receive_daily_summary", False), key=f"t_daily_{student_id}")
    freq_labels = {"realtime": "실시간", "daily": "일 단위", "weekly": "주 단위", "monthly": "월 단위"}
    freq_index = max(0, FREQUENCY_OPTIONS.index(settings.get("frequency", "realtime")) if settings.get("frequency") in FREQUENCY_OPTIONS else 0)
    frequency = st.selectbox(
        "알림 주기",
        options=FREQUENCY_OPTIONS,
        index=freq_index,
        format_func=lambda x: freq_labels.get(x, x),
        key=f"t_freq_{student_id}",
    )
    if st.button("수신 설정 저장", key=f"t_save_settings_{student_id}"):
        if upsert_notification_settings(
            supabase, teacher_id, str(student_id), "teacher",
            email_enabled=email_enabled,
            receive_offtopic=receive_offtopic,
            receive_weekly_report=receive_weekly_report,
            receive_daily_summary=receive_daily_summary,
            frequency=frequency,
        ):
            st.success("수신 설정이 저장되었어요.")
            st.rerun()
        else:
            st.warning("수신 설정 저장에 실패했습니다.")

    st.divider()

    t1, t2, t3, t4 = st.tabs(["🧠 AI 분석", "🧾 상담 리포트", "📦 숙제 제출", "📌 Shared Summary"])
    with t1:
        render_teacher_ai_report_tab(str(student_id))
    with t2:
        render_consult_tab(supabase, teacher_id, str(student_id))
    with t3:
        render_homework_tab(supabase, str(student_id))
    with t4:
        try:
            render_shared_summary(supabase, str(student_id), student_handle, "teacher", teacher_id)
        except Exception as e:
            show_error("Shared Summary 로드 실패", e, context="render_shared_summary", show_trace=False)