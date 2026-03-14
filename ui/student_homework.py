import streamlit as st

from utils.image_utils import normalize_upload
from services.storage_service import upload_problem_image
from services.db_service import (
    get_homework_non_submit_reason_map,
    upsert_homework_non_submit_reason,
    DbServiceError,
)
from services.email_service import send_homework_submitted_notification
from ui.ui_errors import show_error
from ui.components.file_preview import render_file_preview


_REASON_LABELS = {
    "time": "⏰ 시간이 부족했음",
    "hard": "🧩 어려워서 막힘",
    "forgot": "😵‍💫 깜빡함",
}


def _list_assignments(supabase, student_id: str, limit: int = 30):
    try:
        res = (
            supabase.table("homework_assignments")
            .select("id, title, description, created_at, teacher_user_id, student_user_id")
            .eq("student_user_id", student_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return res.data or []
    except Exception as e:
        show_error("숙제 목록 로드 실패", e, context="homework_assignments select", show_trace=st.session_state.get("dev_mode", False))
        return []


def _get_latest_submission(supabase, assignment_id: str):
    try:
        res = (
            supabase.table("homework_submissions")
            .select("id, assignment_id, student_user_id, storage_path, created_at")
            .eq("assignment_id", assignment_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        data = res.data or []
        return data[0] if data else None
    except Exception:
        # created_at이 없을 수도 있으니 fallback
        try:
            res = (
                supabase.table("homework_submissions")
                .select("id, assignment_id, student_user_id, storage_path")
                .eq("assignment_id", assignment_id)
                .limit(1)
                .execute()
            )
            data = res.data or []
            return data[0] if data else None
        except Exception:
            return None


def _insert_submission(supabase, assignment_id: str, student_id: str, storage_path: str):
    payload = {
        "assignment_id": assignment_id,
        "student_user_id": student_id,
        "storage_path": storage_path,
    }
    return supabase.table("homework_submissions").insert(payload).execute()


def _extract_reason_code(obj):
    """
    reason_map의 값 형태가 프로젝트 진행 중 여러 형태로 바뀌었을 수 있어서,
    dict/str 모두 안전하게 reason_code를 뽑아준다.
    """
    if obj is None:
        return None
    if isinstance(obj, str):
        return obj
    if isinstance(obj, dict):
        # 후보 키들 모두 지원
        return obj.get("reason_code") or obj.get("code") or obj.get("reason")
    return None


def render_student_homework(supabase, user, student_id: str, state: dict, st_image_fullwidth=None):
    st.subheader("내 숙제")

    _msg_key = f"hw_submit_msg_{student_id}"
    _sent = st.session_state.pop(_msg_key, None)
    if _sent is True:
        st.success("제출 완료. 선생님/학부모에게 알림을 보냈어요.")
    elif _sent is False:
        st.success("제출 완료.")

    assigns = _list_assignments(supabase, student_id)
    if not assigns:
        st.info("현재 할당된 숙제가 없습니다.")
        return

    st.caption("숙제를 선택하고 파일을 업로드한 뒤 제출하세요. (HEIC/PDF 포함)")

    # ✅ 미제출 사유 맵(배치 조회)
    a_ids = [str(a.get("id")) for a in assigns if a.get("id")]
    reason_map = {}
    if a_ids:
        try:
            reason_map = get_homework_non_submit_reason_map(student_id, a_ids) or {}
        except Exception:
            reason_map = {}

    for a in assigns:
        aid = a["id"]
        aid_str = str(aid)
        title = a.get("title") or "숙제"
        desc = a.get("description") or ""

        latest = _get_latest_submission(supabase, aid)
        submitted = latest is not None
        header = f"📌 {title}  {'✅ 제출됨' if submitted else '⚠️ 미제출'}"

        with st.expander(header, expanded=not submitted):
            if desc:
                st.write(desc)

            # 제출된 숙제
            if submitted:
                st.success("이미 제출된 숙제입니다.")
                try:
                    render_file_preview(
                        supabase,
                        latest.get("storage_path") or "",
                        key_prefix=f"s_hwprev_{student_id}_{aid_str}",
                        label="🔗 제출한 파일 열기",
                    )
                except Exception as e:
                    show_error("숙제 파일 미리보기 실패", e, context="render_file_preview", show_trace=False)
                continue

            # ----------------------------
            # 미제출 사유 3버튼
            # ----------------------------
            # 1) DB에서 읽은 값
            picked_from_db = _extract_reason_code(reason_map.get(aid_str))

            # 2) UI 즉시 반영을 위한 세션 값 (DB 반영이 늦거나 캐시여도 표시 보장)
            sess_key = f"ns_pick_{student_id}_{aid_str}"
            if picked_from_db:
                st.session_state[sess_key] = picked_from_db  # DB값이 있으면 세션도 동기화
            picked = st.session_state.get(sess_key) or picked_from_db

            st.markdown("#### 🧾 미제출 사유(10초)")
            st.caption("미제출이라면 아래 중 하나를 선택해줘. (선생님이 더 정확히 도와줄 수 있어요)")

            c1, c2, c3 = st.columns(3)

            def _reason_button(col, code: str):
                label = _REASON_LABELS[code]
                selected = (picked == code)

                with col:
                    if st.button(label, key=f"ns_{student_id}_{aid_str}_{code}", use_container_width=True):
                        try:
                            upsert_homework_non_submit_reason(student_id, aid_str, code)
                            st.session_state[sess_key] = code  # ✅ 즉시 선택 표시
                            st.toast("저장 완료 ✅", icon="✅")
                            st.rerun()
                        except DbServiceError as e:
                            show_error(
                                "미제출 사유 저장 실패",
                                e,
                                context="upsert_homework_non_submit_reason",
                                show_trace=bool(st.session_state.get("dev_mode", False)),
                            )
                        except Exception as e:
                            show_error(
                                "미제출 사유 저장 실패",
                                e,
                                context="upsert_homework_non_submit_reason",
                                show_trace=bool(st.session_state.get("dev_mode", False)),
                            )

                    # ✅ 버튼 아래 “선택됨” 표시 (버튼 라벨 줄바꿈 의존 X)
                    if selected:
                        st.caption("✅ 선택됨")

            _reason_button(c1, "time")
            _reason_button(c2, "hard")
            _reason_button(c3, "forgot")

            st.divider()

            # ----------------------------
            # 파일 업로드 & 제출
            # ----------------------------
            up = st.file_uploader(
                "숙제 파일 업로드 (이미지/PDF)",
                type=["png", "jpg", "jpeg", "heic", "pdf"],
                key=f"hw_upload_{student_id}_{aid_str}",
            )

            if up:
                try:
                    raw = up.getvalue()
                    norm_bytes, norm_name = normalize_upload(raw, up.name)

                    # 미리보기
                    if callable(st_image_fullwidth):
                        st_image_fullwidth(norm_bytes)
                    else:
                        try:
                            st.image(norm_bytes, use_container_width=True)
                        except TypeError:
                            st.image(norm_bytes, use_column_width=True)

                    hw_confirm_key = f"hw_confirm_{student_id}_{aid_str}"
                    if st.checkbox("제출 후 수정할 수 없습니다. 제출할까요?", key=hw_confirm_key, value=False):
                        if st.button("제출하기", key=f"hw_submit_{student_id}_{aid_str}"):
                            with st.spinner("업로드/제출 중..."):
                                storage_url = upload_problem_image(student_id, norm_bytes, f"HW_{aid_str}_{norm_name}")
                                _insert_submission(supabase, aid, student_id, storage_url)
                                notified = send_homework_submitted_notification(
                                    user.get("handle") or "학생",
                                    (aid.get("title") or "숙제").strip() or "숙제",
                                    student_id,
                                )
                            _key = f"hw_submit_msg_{student_id}"
                            st.session_state[_key] = notified  # True: 알림 발송됨, False: 제출만
                            st.rerun()

                except Exception as e:
                    show_error(
                        "숙제 제출 실패",
                        e,
                        context="normalize_upload/upload_problem_image/homework_submissions insert",
                        show_trace=bool(st.session_state.get("dev_mode", False)),
                    )