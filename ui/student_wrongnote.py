import streamlit as st

from services.llm_service import generate_practice_question
from services.db_service import (
    save_practice_item,
    update_practice_result,
    get_problem_item_feedback_map,
    upsert_problem_item_feedback,
    DbServiceError,
)
from ui.ui_errors import show_error


def _is_studying(user: dict) -> bool:
    return (user.get("status") or "break") == "studying"


def _mask_answer(text: str) -> str:
    if not text:
        return ""
    return "🔒 (정답 표시는 비활성화되어 있습니다)"


_REASON_LABELS = {
    None: "선택 안 함",
    "concept": "개념 부족",
    "calculation": "계산 실수/계산 약함",
    "reading": "문제 해석/독해",
    "time": "시간 부족",
    "guessing": "찍음/감",
}


def render_student_wrongnote(supabase, user, student_id: str, state: dict):
    st.subheader("📒 나의 오답노트")
    st.caption("오답 문항을 기반으로 유사문제를 생성하고 바로 풀어볼 수 있어요. (MVP: 세션 오답 중심)")

    graded = state.get("graded_items") or []
    wrongs = [x for x in graded if x.get("is_correct") is False]

    if not graded:
        st.info("먼저 '학습 대시보드'에서 문제를 채점하면 오답노트가 생성됩니다.")
        return

    if not wrongs:
        st.success("현재 세션 기준 오답이 없습니다. 🎉")
        st.caption("※ 과거 전체 오답노트는 '기록' 탭에서 확인 가능합니다.")
        return

    can_show_answer = bool(user.get("show_practice_answer"))
    studying = _is_studying(user)

    # ✅ 피드백을 한 번에 조회 (pid 있는 항목만)
    pids = [str(x.get("id")) for x in wrongs if x.get("id")]
    feedback_map = {}
    if pids:
        try:
            feedback_map = get_problem_item_feedback_map(student_id, pids)
        except DbServiceError as e:
            show_error("오답 피드백 조회 실패", e, context="get_problem_item_feedback_map", show_trace=False)
            feedback_map = {}
        except Exception as e:
            show_error("오답 피드백 조회 실패", e, context="get_problem_item_feedback_map", show_trace=False)
            feedback_map = {}

    for it in wrongs:
        pid = it.get("id")  # problem_items.id
        item_no = it.get("item_no", 0)
        qtext = it.get("extracted_question_text") or "(문제 텍스트 없음)"
        summ = it.get("explanation_summary") or ""
        submission_id = it.get("submission_id")

        key = f"wn_{student_id}_{pid or item_no}"

        with st.expander(f"🔴 오답 {item_no}번", expanded=False):
            st.write(qtext)
            if summ:
                st.info(summ)

            # ----------------------------
            # NEW: 학생 피드백(이해도/원인) 저장
            # ----------------------------
            if pid:
                row = feedback_map.get(str(pid)) or {}
                default_understanding = row.get("understanding") or "confused"
                default_reason = row.get("reason_category")

                st.markdown("#### ✅ 오답 체크 (학생 입력 10초)")
                c1, c2 = st.columns([1, 2])

                with c1:
                    understanding = st.radio(
                        "이해도",
                        options=["understood", "confused"],
                        index=0 if default_understanding == "understood" else 1,
                        format_func=lambda v: "이해됨" if v == "understood" else "헷갈림",
                        key=f"fb_under_{key}",
                        horizontal=True,
                    )

                with c2:
                    reason_options = [None, "concept", "calculation", "reading", "time", "guessing"]
                    try:
                        default_idx = reason_options.index(default_reason)
                    except Exception:
                        default_idx = 0
                    reason_category = st.selectbox(
                        "틀린 원인(선택 1개)",
                        options=reason_options,
                        index=default_idx,
                        format_func=lambda v: _REASON_LABELS.get(v, str(v)),
                        key=f"fb_reason_{key}",
                    )

                if st.button("💾 저장", key=f"fb_save_{key}", use_container_width=True):
                    try:
                        upsert_problem_item_feedback(
                            student_id=student_id,
                            problem_item_id=str(pid),
                            submission_id=str(submission_id) if submission_id else None,
                            understanding=understanding,
                            reason_category=reason_category,
                        )
                        st.success("저장 완료 ✅")
                        st.rerun()
                    except DbServiceError as e:
                        show_error("피드백 저장 실패", e, context="upsert_problem_item_feedback")
                    except Exception as e:
                        show_error("피드백 저장 실패", e, context="upsert_problem_item_feedback")

                st.caption("※ 이 데이터는 선생님/학부모 상담 리포트의 '학습 성향' 분석에 활용됩니다.")
                st.divider()
            else:
                st.caption("※ (이 문항은 ID가 없어 피드백 저장이 불가합니다. 다음 채점부터 자동 저장됩니다.)")
                st.divider()

            # ----------------------------
            # 기존: 연습문제 생성/저장/채점
            # ----------------------------
            practice_map = state.get("practice_by_problem", {})
            pstate = practice_map.get(str(pid) if pid else key)

            c1, c2 = st.columns([1, 2])
            with c1:
                if st.button("✍️ 연습문제 생성", key=f"gen_pr_{key}"):
                    if studying and not can_show_answer:
                        st.warning("studying 모드에서는 정답 노출 없이 연습 생성/풀이만 가능합니다.")
                    with st.spinner("연습문제 생성 중..."):
                        try:
                            pr = generate_practice_question(qtext)
                            practice_map[str(pid) if pid else key] = {
                                "q": pr.get("question"),
                                "answer_key": pr.get("answer_key"),
                                "explanation": pr.get("explanation"),
                                "key_concepts": pr.get("key_concepts") or [],
                                "practice_id": None,
                            }
                            state["practice_by_problem"] = practice_map
                            st.success("생성 완료")
                            st.rerun()
                        except Exception as e:
                            show_error("연습문제 생성 실패", e, context="generate_practice_question")

            if not pstate:
                st.caption("연습문제를 생성하면 여기서 바로 풀 수 있어요.")
                continue

            st.subheader("🧩 생성된 연습문제")
            st.write(pstate.get("q") or "(생성 실패)")

            if can_show_answer:
                st.caption("정답 키(교사용/설정 허용 시 표시)")
                st.code(pstate.get("answer_key") or "")
            else:
                st.caption(_mask_answer(pstate.get("answer_key") or ""))

            # practice_items 저장 (1회만)
            if pstate.get("practice_id") is None and pid:
                if st.button("💾 연습문제 저장", key=f"save_pr_{key}"):
                    try:
                        saved = save_practice_item(
                            problem_item_id=pid,
                            student_id=student_id,
                            question=pstate.get("q"),
                            answer_key=pstate.get("answer_key"),
                            concepts=pstate.get("key_concepts"),
                        )
                        pstate["practice_id"] = saved.get("id")
                        practice_map[str(pid)] = pstate
                        state["practice_by_problem"] = practice_map
                        st.success("저장 완료")
                        st.rerun()
                    except Exception as e:
                        show_error("연습문제 저장 실패", e, context="save_practice_item")

            st.subheader("📝 답안 제출")

            practice_id = pstate.get("practice_id")
            ans_key = f"ans_{student_id}_{practice_id or key}"
            student_ans = st.text_area("내 답", key=ans_key, height=120)

            if st.button("✅ 채점/저장", key=f"grade_pr_{key}"):
                if not practice_id or not pid:
                    st.warning("먼저 '연습문제 저장'을 눌러야 결과를 저장할 수 있어요.")
                else:
                    ak = (pstate.get("answer_key") or "").strip()
                    sa = (student_ans or "").strip()
                    is_correct = False
                    try:
                        if ak and sa:
                            is_correct = ak.lower() in sa.lower() or sa.lower() in ak.lower()

                        update_practice_result(
                            practice_id=practice_id,
                            student_answer=student_ans,
                            is_correct=is_correct,
                            student_id=student_id,
                            problem_item_id=pid,
                        )
                        st.success(f"저장 완료 ✅ ({'정답' if is_correct else '오답'})")
                        st.rerun()
                    except Exception as e:
                        show_error("연습 결과 저장 실패", e, context="update_practice_result")

            st.subheader("📚 해설")
            if pstate.get("explanation"):
                if can_show_answer:
                    st.write(pstate.get("explanation"))
                else:
                    st.caption("🔒 (해설 상세는 설정에서 허용 시 표시)")

            kc = pstate.get("key_concepts") or []
            if kc:
                st.caption("핵심 개념: " + ", ".join(kc))