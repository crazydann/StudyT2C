# 경량 모듈: 어드민 상단 팝오버용 학생 설정 폼만 (student_detail import 회피로 ImportError 방지)
import streamlit as st

from ui.teacher.data_loaders import fetch_teacher_notification_email, update_teacher_notification_email
from services.notification_settings_service import (
    fetch_notification_settings,
    upsert_notification_settings,
    FREQUENCY_OPTIONS,
)


def render_teacher_settings_content(supabase, teacher_id: str, student_id: str):
    """학생 설정 폼 내용만 (상단 팝오버에서 호출)."""
    current_email = fetch_teacher_notification_email(supabase, teacher_id)
    notify_email = st.text_input("알림 수신 이메일", value=current_email, placeholder="example@email.com", key=f"t_notify_email_{student_id}")
    if st.button("이메일 저장", key=f"t_save_notify_{student_id}"):
        if update_teacher_notification_email(supabase, teacher_id, notify_email or ""):
            st.success("저장되었습니다.")
            st.rerun()
    settings = fetch_notification_settings(supabase, teacher_id, str(student_id))
    email_enabled = st.toggle("이 학생 알림 받기", value=settings.get("email_enabled", True), key=f"t_email_on_{student_id}")
    receive_weekly_report = st.checkbox("주간 리포트", value=settings.get("receive_weekly_report", False), key=f"t_weekly_{student_id}")
    receive_offtopic = st.checkbox("탭 이탈·공부 외 질문 알림", value=settings.get("receive_offtopic", True), key=f"t_offtopic_{student_id}")
    with st.expander("고급 알림 설정", expanded=False):
        receive_daily_summary = st.checkbox("일일 요약", value=settings.get("receive_daily_summary", False), key=f"t_daily_{student_id}")
        freq_labels = {"realtime": "실시간", "daily": "일", "weekly": "주", "monthly": "월"}
        freq_index = max(0, FREQUENCY_OPTIONS.index(settings.get("frequency", "realtime")) if settings.get("frequency") in FREQUENCY_OPTIONS else 0)
        frequency = st.selectbox("알림 주기", options=FREQUENCY_OPTIONS, index=freq_index, format_func=lambda x: freq_labels.get(x, x), key=f"t_freq_{student_id}")
    if st.button("수신 설정 저장", key=f"t_save_settings_{student_id}"):
        if upsert_notification_settings(supabase, teacher_id, str(student_id), "teacher", email_enabled=email_enabled, receive_offtopic=receive_offtopic, receive_weekly_report=receive_weekly_report, receive_daily_summary=receive_daily_summary, frequency=frequency):
            st.success("저장되었습니다.")
            st.rerun()
