# ui/parent/student_detail.py
import streamlit as st

from ui.ui_errors import show_error
from shared_summary import render_shared_summary
from ui.parent.consult_tab import render_consult_tab
from ui.parent.homework_tab import render_homework_tab
from ui.parent.data_loaders import (
    fetch_student_status,
    update_student_status,
    fetch_parent_notification_email,
    update_parent_notification_email,
)
from ui.parent.ai_report_tab import render_ai_report_tab
from services.notification_settings_service import (
    fetch_notification_settings,
    upsert_notification_settings,
    FREQUENCY_OPTIONS,
    get_offtopic_recipients_realtime,
)
from services.email_service import send_focus_left_alert_with_reason
from services.focus_events_service import record_focus_alert_sent


def _render_parent_detail_settings(supabase, parent_id: str, sid: str, shandle: str):
    with st.sidebar:
        with st.expander("⚙️ 자녀 설정", expanded=False):
            st.markdown("**AI 튜터 모드**")
            current_status = fetch_student_status(supabase, str(sid))
            options = ["studying", "break"]
            def _label(mode: str) -> str:
                return "수업 중" if mode == "studying" else "쉬는 시간"
            try:
                default_index = options.index(current_status) if current_status in options else 1
            except ValueError:
                default_index = 1
            selected_mode = st.radio("자녀의 AI 튜터 모드", options, index=default_index, format_func=_label, horizontal=True, key=f"p_ai_mode_{sid}")
            if selected_mode != current_status:
                if update_student_status(supabase, str(sid), selected_mode):
                    st.success("저장되었습니다.")
                else:
                    st.warning("저장에 실패했습니다.")
            st.markdown("**이메일 알림**")
            current_email = fetch_parent_notification_email(supabase, parent_id)
            notify_email = st.text_input("알림 수신 이메일", value=current_email, placeholder="example@email.com", key=f"p_notify_email_{sid}")
            if st.button("이메일 저장", key=f"p_save_notify_{sid}"):
                if update_parent_notification_email(supabase, parent_id, notify_email or ""):
                    st.success("저장되었습니다.")
                    st.rerun()
            settings = fetch_notification_settings(supabase, parent_id, str(sid))
            email_enabled = st.toggle("이 학생 알림 받기", value=settings.get("email_enabled", True), key=f"p_email_on_{sid}")
            receive_offtopic = st.checkbox("공부 외 질문 알림", value=settings.get("receive_offtopic", True), key=f"p_offtopic_{sid}")
            receive_weekly_report = st.checkbox("주간 리포트", value=settings.get("receive_weekly_report", False), key=f"p_weekly_{sid}")
            receive_daily_summary = st.checkbox("일일 요약", value=settings.get("receive_daily_summary", False), key=f"p_daily_{sid}")
            freq_labels = {"realtime": "실시간", "daily": "일", "weekly": "주", "monthly": "월"}
            freq_index = max(0, FREQUENCY_OPTIONS.index(settings.get("frequency", "realtime")) if settings.get("frequency") in FREQUENCY_OPTIONS else 0)
            frequency = st.selectbox("알림 주기", options=FREQUENCY_OPTIONS, index=freq_index, format_func=lambda x: freq_labels.get(x, x), key=f"p_freq_{sid}")
            if st.button("수신 설정 저장", key=f"p_save_settings_{sid}"):
                if upsert_notification_settings(supabase, parent_id, str(sid), "parent", email_enabled=email_enabled, receive_offtopic=receive_offtopic, receive_weekly_report=receive_weekly_report, receive_daily_summary=receive_daily_summary, frequency=frequency):
                    st.success("저장되었습니다.")
                    st.rerun()
            if st.button("탭 이탈 알림 수동 발송", key=f"p_focus_manual_send_{sid}"):
                recipients = get_offtopic_recipients_realtime(str(sid))
                ok, msg = send_focus_left_alert_with_reason(recipients, shandle)
                if ok:
                    record_focus_alert_sent(str(sid))
                    st.success(msg)
                else:
                    st.error(msg)


def render_student_detail(supabase, parent_id: str, state: dict):
    sel = state.get("selected_student") or {}
    sid = sel.get("id")
    shandle = sel.get("handle") or "student"

    if not sid:
        st.warning("자녀가 선택되지 않았습니다.")
        state["selected_student"] = None
        return

    _render_parent_detail_settings(supabase, parent_id, str(sid), shandle)

    # 상단 한 줄: 뒤로 | 자녀명
    row = st.columns([1, 4])
    with row[0]:
        if st.button("🔙 목록으로", key="p_back"):
            state["selected_student"] = None
            st.rerun()
    with row[1]:
        st.markdown(f"<span style='font-size:16px;font-weight:600;'>{shandle}</span>", unsafe_allow_html=True)

    tab_labels = ["AI 리포트", "상담", "숙제", "요약"]
    selected = st.radio("탭", options=tab_labels, horizontal=True, key="parent_detail_tab", label_visibility="collapsed")

    if selected == "AI 리포트":
        render_ai_report_tab(str(sid), shandle)
    elif selected == "상담":
        render_consult_tab(supabase, str(sid))
    elif selected == "숙제":
        render_homework_tab(supabase, str(sid))
    else:
        try:
            render_shared_summary(supabase, str(sid), shandle, "parent", parent_id)
        except Exception as e:
            show_error("Shared Summary 로드 실패", e, context="render_shared_summary", show_trace=False)