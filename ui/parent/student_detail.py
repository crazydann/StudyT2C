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
)


def render_student_detail(supabase, parent_id: str, state: dict):
    sel = state.get("selected_student") or {}
    sid = sel.get("id")
    shandle = sel.get("handle") or "student"

    if not sid:
        st.warning("자녀가 선택되지 않았습니다.")
        state["selected_student"] = None
        return

    top_bar = st.columns([1, 3, 1])
    with top_bar[0]:
        if st.button("🔙 목록으로", key="p_back"):
            state["selected_student"] = None
            st.rerun()

    with top_bar[1]:
        st.markdown(f"## 🎓 {shandle} (자녀 상세)")

    # 학부모용 AI 튜터 모드 설정
    st.markdown("### 🤖 AI 튜터 응답 모드")
    current_status = fetch_student_status(supabase, str(sid))
    options = ["studying", "break"]

    def _label(mode: str) -> str:
        if mode == "studying":
            return "수업 중 모드 (공부 관련 질문만)"
        return "쉬는 시간 모드 (자유 질문 허용)"

    try:
        default_index = options.index(current_status) if current_status in options else 1
    except ValueError:
        default_index = 1

    selected_mode = st.radio(
        "자녀의 AI 튜터 모드",
        options,
        index=default_index,
        format_func=_label,
        horizontal=True,
        key=f"p_ai_mode_{sid}",
    )

    st.caption(
        "· 수업 중 모드: 공부/과목 관련 질문만 답변하고, 잡담/게임/연애 등은 정중히 거절합니다.\n"
        "· 쉬는 시간 모드: 자유로운 질문에도 답변하도록 허용합니다."
    )

    if selected_mode != current_status:
        if update_student_status(supabase, str(sid), selected_mode):
            st.success("자녀의 AI 튜터 모드를 변경했어요. 학생 화면의 다음 대화부터 반영됩니다.")
        else:
            st.warning("AI 튜터 모드 저장에 실패했습니다. 잠시 후 다시 시도해 주세요.")

    st.markdown("### 📧 이메일 알림 설정")
    current_email = fetch_parent_notification_email(supabase, parent_id)
    notify_email = st.text_input(
        "알림 수신 이메일 주소",
        value=current_email,
        placeholder="example@email.com",
        key=f"p_notify_email_{sid}",
        help="이 주소로 알림 메일이 발송됩니다. 수정 후 저장 버튼을 눌러 주세요.",
    )
    if st.button("이메일 주소 저장", key=f"p_save_notify_{sid}"):
        if update_parent_notification_email(supabase, parent_id, notify_email or ""):
            st.success("이메일 주소가 저장되었어요.")
            st.rerun()
        else:
            st.warning("저장에 실패했습니다. 잠시 후 다시 시도해 주세요.")

    # 이 학생에 대한 수신 여부·항목·주기
    st.markdown("#### 이 자녀에 대한 수신 설정")
    settings = fetch_notification_settings(supabase, parent_id, str(sid))
    email_enabled = st.toggle("이 학생에 대한 이메일 알림 받기", value=settings.get("email_enabled", True), key=f"p_email_on_{sid}")
    receive_offtopic = st.checkbox("공부 외 질문 알림 (수업 중 잡담·게임 등)", value=settings.get("receive_offtopic", True), key=f"p_offtopic_{sid}")
    receive_weekly_report = st.checkbox("주간 학습 리포트 (준비 중)", value=settings.get("receive_weekly_report", False), key=f"p_weekly_{sid}")
    receive_daily_summary = st.checkbox("일일 요약 (준비 중)", value=settings.get("receive_daily_summary", False), key=f"p_daily_{sid}")
    freq_labels = {"realtime": "실시간", "daily": "일 단위", "weekly": "주 단위", "monthly": "월 단위"}
    freq_index = max(0, FREQUENCY_OPTIONS.index(settings.get("frequency", "realtime")) if settings.get("frequency") in FREQUENCY_OPTIONS else 0)
    frequency = st.selectbox(
        "알림 주기",
        options=FREQUENCY_OPTIONS,
        index=freq_index,
        format_func=lambda x: freq_labels.get(x, x),
        key=f"p_freq_{sid}",
    )
    if st.button("수신 설정 저장", key=f"p_save_settings_{sid}"):
        if upsert_notification_settings(
            supabase, parent_id, str(sid), "parent",
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

    t1, t2, t3, t4 = st.tabs(["📊 AI 리포트", "🧾 상담 리포트", "📦 숙제 제출", "📌 Shared Summary"])
    with t1:
        render_ai_report_tab(str(sid))
    with t2:
        render_consult_tab(supabase, str(sid))
    with t3:
        render_homework_tab(supabase, str(sid))
    with t4:
        try:
            render_shared_summary(supabase, str(sid), shandle, "parent", parent_id)
        except Exception as e:
            show_error("Shared Summary 로드 실패", e, context="render_shared_summary", show_trace=False)