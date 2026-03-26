# ui/teacher/student_detail.py
import streamlit as st

from ui.ui_errors import show_error
from shared_summary import render_shared_summary

from ui.teacher.consult_tab import render_consult_tab
from ui.teacher.homework_tab import render_homework_tab
from ui.teacher.ai_report_tab import render_teacher_ai_report_tab
from ui.focus_ui import render_focus_section
from services.analytics_service import get_next_class_plan, get_student_profile


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

    # ── 수업 전 브리핑 카드 ──────────────────────────────────────────
    try:
        profile = get_student_profile(str(student_id))
    except Exception:
        profile = {}
    try:
        plan = get_next_class_plan(str(student_id))
    except Exception:
        plan = {}

    concepts = profile.get("concepts") or []
    strong = (profile.get("peer_compare") or {}).get("strong_concepts") or []
    weak = (profile.get("peer_compare") or {}).get("weak_concepts") or []
    qs = profile.get("questions_style") or {}
    focus = plan.get("focus_concepts") or []
    practice = plan.get("practice_types") or []

    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #eff6ff, #ffffff);
            border: 1.5px solid #bfdbfe;
            border-left: 5px solid #2563eb;
            border-radius: 12px;
            padding: 14px 18px 10px;
            margin-bottom: 12px;
        ">
            <div style="font-size:0.72rem;font-weight:700;color:#2563eb;letter-spacing:0.06em;margin-bottom:6px;">
                📋 수업 전 브리핑 — {student_handle}
            </div>
        """,
        unsafe_allow_html=True,
    )

    b1, b2 = st.columns(2)
    with b1:
        if strong:
            st.markdown(
                "<div style='font-size:0.8rem;'>"
                f"<span style='color:#16a34a;font-weight:700;'>✅ 강한 개념</span>&nbsp; "
                + " · ".join(f"<code>{c}</code>" for c in strong[:3])
                + "</div>",
                unsafe_allow_html=True,
            )
        if weak:
            st.markdown(
                "<div style='font-size:0.8rem;margin-top:4px;'>"
                f"<span style='color:#dc2626;font-weight:700;'>⚠️ 보강 필요</span>&nbsp; "
                + " · ".join(f"<code>{c}</code>" for c in weak[:3])
                + "</div>",
                unsafe_allow_html=True,
            )
        if not strong and not weak:
            st.caption("아직 분석 데이터가 충분하지 않아요.")
    with b2:
        try:
            cq = int((qs.get("conceptual_ratio") or 0) * 100)
            pq = int((qs.get("procedural_ratio") or 0) * 100)
            kq = int((qs.get("careless_ratio") or 0) * 100)
            st.markdown(
                f"<div style='font-size:0.78rem;color:#475569;'>"
                f"<b>질문 스타일</b> · 개념이해 {cq}% / 풀이 {pq}% / 실수확인 {kq}%</div>",
                unsafe_allow_html=True,
            )
        except Exception:
            pass

    if focus or practice:
        st.markdown(
            "<div style='font-size:0.78rem;font-weight:700;color:#1e293b;margin:10px 0 4px;'>"
            "🎯 오늘 수업 액션 아이템</div>",
            unsafe_allow_html=True,
        )
        for i, item in enumerate(focus, start=1):
            st.checkbox(
                f"{i}. **{item.get('name', '')}** — {item.get('suggestion', '')}",
                key=f"t_next_plan_{student_id}_{i}",
            )
        for pt in practice:
            st.caption(f"💡 {pt.get('type', '')} · {pt.get('suggestion', '')}")

    st.markdown("</div>", unsafe_allow_html=True)
    # ─────────────────────────────────────────────────────────────────

    row = st.columns([1, 4])
    with row[0]:
        if st.button("🔙 목록으로", key="t_back"):
            state["selected_student"] = None
            st.rerun()
    with row[1]:
        st.markdown(f"<span style='font-size:16px;font-weight:600;'>{student_handle}</span>", unsafe_allow_html=True)

    tab_labels = ["맞춤 보강·성취도", "상담", "숙제", "집중현황", "요약"]
    selected = st.radio("탭", options=tab_labels, horizontal=True, key=f"teacher_detail_tab_{student_id}", label_visibility="collapsed")

    if selected == "맞춤 보강·성취도":
        render_teacher_ai_report_tab(str(student_id), student_handle)
    elif selected == "상담":
        render_consult_tab(supabase, teacher_id, str(student_id))
    elif selected == "숙제":
        render_homework_tab(supabase, str(student_id))
    elif selected == "집중현황":
        render_focus_section(str(student_id), student_handle)
    else:
        try:
            render_shared_summary(supabase, str(student_id), student_handle, "teacher", teacher_id)
        except Exception as e:
            show_error("Shared Summary 로드 실패", e, context="render_shared_summary", show_trace=False)