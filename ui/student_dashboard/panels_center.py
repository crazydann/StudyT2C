import streamlit as st

from services.llm_service import chat_with_tutor, classify_subject
from services.db_service import (
    save_chat_message,
    list_grading_submissions,
    get_submission_items,
)
from services.email_service import send_offtopic_alert_to_recipients
from services.notification_settings_service import get_offtopic_recipients_realtime
from ui.ui_common import format_ts_kst
from ui.ui_errors import show_error

OFFTOPIC_EMAIL_COOLDOWN_SEC = 3600


def _is_studying(user: dict) -> bool:
    return (user.get("status") or "break") == "studying"


def _classify_study_relevance(text: str, studying: bool) -> tuple[bool, str]:
    """
    질문이 공부 관련인지 간단히 구분 (모니터링용).
    - studying 모드가 아닐 땐 항상 공부 관련(True)로 본다.
    """
    if not studying:
        return True, "FREE"

    t = (text or "").lower()
    offtopic_keywords = [
        "게임",
        "롤",
        "배그",
        "주식",
        "코인",
        "연애",
        "썸",
        "유튜브",
        "틱톡",
        "넷플릭스",
        "아이돌",
        "잡담",
        "농담",
    ]
    for kw in offtopic_keywords:
        if kw in t:
            return False, "OFFTOPIC"
    return True, "STUDY"


def _maybe_send_offtopic_email(student_id: str, user: dict, offtopic_content: str) -> None:
    """공부 외 질문 저장 후 수신 설정이 실시간인 학부모/선생님에게 역할별 템플릿으로 이메일 알림 (1시간 쿨다운)."""
    import time
    key = "offtopic_email_last_sent"
    if key not in st.session_state:
        st.session_state[key] = {}
    last = st.session_state[key].get(student_id) or 0
    if time.time() - last < OFFTOPIC_EMAIL_COOLDOWN_SEC:
        return
    recipients = get_offtopic_recipients_realtime(student_id)
    if not recipients:
        return
    student_handle = user.get("handle") or "학생"
    if send_offtopic_alert_to_recipients(recipients, student_handle, offtopic_content):
        st.session_state[key][student_id] = time.time()


def _render_recent_grading_history(student_id: str, user: dict):
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


def render_center_panel(user: dict, student_id: str, state: dict):
    st.subheader("💬 AI 튜터")

    studying = _is_studying(user)
    if studying:
        st.caption("🟢 studying 모드: 학습 외 질문은 제한될 수 있어요.")
    else:
        st.caption("🟡 break 모드: 자유 질문 가능(데모용).")

    state.setdefault("messages", [])
    if not isinstance(state.get("messages"), list):
        state["messages"] = []

    # 대화창: 고정 높이 + 스크롤 (질문/답변은 이 안에서만 스크롤), 입력창은 항상 아래에
    # 높이는 학생 화면 CSS에서 뷰포트 비율(65vh 등)로 오버라이드됨
    try:
        chat_height = 720
        with st.container(height=chat_height):
            for msg in state.get("messages", []):
                with st.chat_message(msg.get("role", "assistant")):
                    st.markdown(msg.get("content", ""))
                    if msg.get("role") == "assistant" and msg.get("_subject"):
                        st.caption(f"분류된 과목: {msg.get('_subject')}")
    except TypeError:
        for msg in state.get("messages", []):
            with st.chat_message(msg.get("role", "assistant")):
                st.markdown(msg.get("content", ""))
                if msg.get("role") == "assistant" and msg.get("_subject"):
                    st.caption(f"분류된 과목: {msg.get('_subject')}")

    # 입력창은 대화 영역 바로 아래 고정 (ChatGPT처럼)
    u_input = st.chat_input("질문하세요")
    if u_input:
        is_study, category = _classify_study_relevance(u_input, studying)
        if studying and not is_study:
            ans = "지금은 공부 시간이에요. 숙제나 개념 관련 질문을 해주세요. 😊"
            subj_class = {"subject": "OTHER", "confidence": 0.0}
        else:
            try:
                subj_class = classify_subject(u_input)
                ans = chat_with_tutor(u_input, mode=user.get("status", "break"))
            except Exception as e:
                show_error("AI 튜터 응답 실패", e, context="classify_subject/chat_with_tutor")
                subj_class = {"subject": "OTHER", "confidence": 0.0}
                ans = "AI 튜터 연결 오류"
        state["messages"].append({"role": "user", "content": u_input})
        state["messages"].append({"role": "assistant", "content": ans, "_subject": subj_class.get("subject", "OTHER")})
        try:
            meta = {
                "mode": user.get("status", "break"),
                "is_study": bool(is_study),
                "offtopic_category": category,
                "subject": subj_class.get("subject", "OTHER"),
            }
            save_chat_message(student_id, "user", u_input, meta=meta, answer=ans)
            if studying and not is_study:
                _maybe_send_offtopic_email(student_id, user, u_input)
        except Exception as e:
            if st.session_state.get("dev_mode", False):
                show_error("채팅 이력 저장 실패", e, context="save_chat_message", show_trace=False)
                st.code(str(e), language="text")
        st.rerun()

    st.divider()
    _render_recent_grading_history(student_id, user)