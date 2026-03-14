# ui/student_dashboard/panels_chat.py
import streamlit as st

from services.llm_service import chat_with_tutor, classify_subject
from services.db_service import save_chat_message
from ui.ui_errors import show_error


def _is_studying(user: dict) -> bool:
    return (user.get("status") or "break") == "studying"


def render_chat_panel(user: dict, student_id: str, state: dict) -> None:
    st.subheader("💬 AI 튜터")

    studying = _is_studying(user)
    if studying:
        st.caption("🟢 studying 모드: 학습 외 질문은 제한될 수 있어요.")
    else:
        st.caption("🟡 break 모드: 자유 질문 가능(데모용).")

    socratic = st.checkbox(
        "소크라틱 모드 (단계별 질문으로 스스로 답 찾기)",
        value=state.get("socratic_mode", False),
        key=f"chat_socratic_{student_id}",
    )
    state["socratic_mode"] = socratic

    for msg in state.get("messages", []):
        with st.chat_message(msg.get("role", "assistant")):
            st.markdown(msg.get("content", ""))

    u_input = st.chat_input("질문하세요")
    if not u_input:
        return

    if studying and any(x in u_input.lower() for x in ["게임", "주식", "연애", "잡담", "농담", "영화"]):
        st.warning("studying 모드에서는 학습 관련 질문을 우선으로 해주세요.")

    state["messages"].append({"role": "user", "content": u_input})
    with st.chat_message("user"):
        st.markdown(u_input)

    with st.chat_message("assistant"):
        with st.spinner("생각 중..."):
            try:
                subj_class = classify_subject(u_input)
                history = state.get("messages", []) if state.get("socratic_mode") else None
                ans = chat_with_tutor(
                    u_input,
                    mode=user.get("status", "break"),
                    socratic=state.get("socratic_mode", False),
                    history=history,
                )
            except Exception as e:
                show_error("AI 튜터 응답 실패", e, context="classify_subject/chat_with_tutor")
                subj_class = {"subject": "OTHER", "confidence": 0.0}
                ans = "AI 튜터 연결 오류"

            st.markdown(ans)
            st.caption(f"분류된 과목: {subj_class.get('subject', 'OTHER')}")
            if ans == "AI 튜터 연결 오류":
                if st.button("다시 시도", key=f"chat_retry_{student_id}"):
                    if len(state.get("messages", [])) >= 2:
                        state["messages"] = state["messages"][:-2]
                    st.rerun()

    state["messages"].append({"role": "assistant", "content": ans})
    try:
        meta = {
            "mode": user.get("status", "break"),
            "subject": subj_class.get("subject", "OTHER"),
        }
        save_chat_message(student_id, "user", u_input, meta=meta)
    except Exception:
        pass