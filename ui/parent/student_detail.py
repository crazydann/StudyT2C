# ui/parent/student_detail.py
import streamlit as st

from ui.ui_errors import show_error
from shared_summary import render_shared_summary
from ui.parent.consult_tab import render_consult_tab
from ui.parent.homework_tab import render_homework_tab
from ui.parent.data_loaders import fetch_student_status, update_student_status
from ui.parent.ai_report_tab import render_ai_report_tab


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