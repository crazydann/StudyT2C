# ui/student_dashboard/panels_grading.py
import hashlib
from typing import List, Dict, Any, Optional

import streamlit as st
from PIL import UnidentifiedImageError

from services.supabase_client import supabase_service

from utils.image_utils import normalize_upload
from services.storage_service import upload_problem_image
from services.vision_grading import grade_image_to_items
from services.db_service import (
    check_cached_submission,
    upsert_problem_submission,
    save_grading_results,
    get_submission_items,
    DbServiceError,
)
from ui.ui_errors import show_error
from ui.student_dashboard.helpers import rotate_png_bytes
from ui.student_dashboard.error_store import (
    render_persisted_error,
    persist_last_error,
    clear_last_error,
)


def _render_items(user: dict, items: List[Dict[str, Any]]) -> None:
    for item in items or []:
        is_corr = bool(item.get("is_correct"))
        item_no = item.get("item_no", 0)
        with st.expander(f"{item_no}번 ({'🟢' if is_corr else '🔴'})", expanded=not is_corr):
            st.write(item.get("explanation_summary"))
            kc = item.get("key_concepts") or []
            if kc:
                st.caption("핵심 개념: " + ", ".join(kc))
            if user.get("detail_permission") and item.get("explanation_detail"):
                st.info(item.get("explanation_detail"))


def _dev_debug_box(student_id: str, title: str, data: Dict[str, Any]) -> None:
    if not bool(st.session_state.get("dev_mode", False)):
        return
    with st.container(border=True):
        st.caption(f"🧪 {title}")
        safe = dict(data)
        if "file_bytes" in safe:
            safe["file_bytes"] = f"<bytes {len(safe['file_bytes'])}>"
        st.json(safe)


def _friendly_heic_error(e: Exception) -> None:
    # “어떤 HEIC는 라이브포토/보조이미지 때문에 디코딩 실패”를 명시
    st.error(
        "HEIC/HEIF 파일을 읽는 중 오류가 발생했습니다.\n\n"
        "✅ 해결 방법(추천 순서)\n"
        "1) iPhone에서 사진을 **공유 → 파일에 저장** 후, "
        "사진 앱/파일 앱에서 **JPG로 변환**해서 업로드\n"
        "2) 또는 **스크린샷(자동 PNG)** 로 업로드\n"
        "3) 또는 PC에서 HEIC → JPG 변환 후 업로드\n"
    )
    if bool(st.session_state.get("dev_mode", False)):
        st.caption(f"(dev) {type(e).__name__}: {e}")


def render_grading_panel(user: dict, student_id: str, state: dict, render_image, show_title: bool = True) -> None:
    if show_title:
        st.subheader("📸 문제 채점기")

    if bool(st.session_state.get("dev_mode", False)):
        st.caption(f"DB write client: {'service_role' if supabase_service is not None else 'anon (NO SERVICE KEY)'}")

    render_persisted_error(student_id)

    # ----------------------------
    # pending_save 재시도
    # ----------------------------
    if state.get("pending_save"):
        with st.container(border=True):
            st.warning("이전 채점은 완료됐지만 저장이 중간에 실패했습니다. 아래 버튼으로 이어서 저장할 수 있어요.")
            if st.button("💾 저장 재시도", key=f"retry_save_{student_id}"):
                ps = state["pending_save"]
                try:
                    sub_id = ps.get("submission_id")
                    if not sub_id:
                        raise ValueError(
                            "submission_id가 없어 저장을 재시도할 수 없습니다. (submission upsert 단계부터 실패했을 가능성)"
                        )

                    save_grading_results(
                        submission_id=str(sub_id),
                        student_user_id=str(ps["student_id"]),
                        items=ps["items"],
                    )
                    state["graded_items"] = ps["items"]
                    state["pending_save"] = None
                    clear_last_error(student_id)

                    st.success("저장 재시도 성공 ✅")
                    st.rerun()

                except Exception as e:
                    persist_last_error(student_id, "저장 재시도 실패", "save_grading_results(retry)", e)
                    show_error("저장 재시도 실패", e, context="save_grading_results(retry)", show_trace=False)

                    _dev_debug_box(
                        student_id,
                        "retry_save payload",
                        {
                            "student_id": ps.get("student_id"),
                            "submission_id": ps.get("submission_id"),
                            "file_hash": ps.get("file_hash"),
                            "storage_url": ps.get("storage_url"),
                            "items_count": len(ps.get("items") or []),
                            "exception": f"{type(e).__name__}: {e}",
                        },
                    )

    uploaded_file = st.file_uploader(
        "이미지/PDF 업로드",
        type=["png", "jpg", "jpeg", "heic", "heif", "pdf"],  # heif도 허용
        key=f"uploader_{student_id}",
    )

    if not uploaded_file:
        _render_items(user, state.get("graded_items") or [])
        return

    try:
        raw = uploaded_file.getvalue()

        # ✅ 여기서 HEIC를 차단하지 않고, normalize_upload가 처리하도록 둔다
        try:
            base_bytes, norm_name = normalize_upload(raw, uploaded_file.name)
        except (UnidentifiedImageError, ValueError) as e:
            # HEIC 디코딩 실패(예: Too many auxiliary image references)도 여기로 온다
            _friendly_heic_error(e)
            return

        state.setdefault("upload_rotation", {})
        upload_key = f"{uploaded_file.name}:{len(raw)}"
        deg = int(state["upload_rotation"].get(upload_key, 0))
        view_bytes = rotate_png_bytes(base_bytes, deg)

        b1, b2, b3, b4 = st.columns([1, 1, 1, 1])
        with b1:
            if st.button("↺ -90°", key=f"rot_l_{student_id}_{upload_key}"):
                state["upload_rotation"][upload_key] = deg - 90
                st.rerun()
        with b2:
            if st.button("↻ +90°", key=f"rot_r_{student_id}_{upload_key}"):
                state["upload_rotation"][upload_key] = deg + 90
                st.rerun()
        with b3:
            if st.button("⟲ 180°", key=f"rot_180_{student_id}_{upload_key}"):
                state["upload_rotation"][upload_key] = deg + 180
                st.rerun()
        with b4:
            if st.button("Reset", key=f"rot_reset_{student_id}_{upload_key}"):
                state["upload_rotation"][upload_key] = 0
                st.rerun()

        st.caption(f"현재 회전: {deg % 360}°")
        render_image(view_bytes)

        file_hash = hashlib.sha256(view_bytes).hexdigest()

        if st.button("AI 채점 요청", key=f"grade_btn_{student_id}_{file_hash}"):

            cached: Optional[Dict[str, Any]] = None
            try:
                cached = check_cached_submission(student_id, file_hash)
            except Exception:
                cached = None

            if cached and cached.get("id"):
                try:
                    items = get_submission_items(str(cached["id"]), limit=300)
                except Exception:
                    items = []

                state["pending_save"] = None
                state["graded_items"] = items or []
                clear_last_error(student_id)

                st.success("⚡ 이미 채점/저장된 파일이에요. 결과를 불러왔습니다.")
                st.rerun()
                return

            try:
                with st.spinner("AI 분석 중..."):
                    storage_url = upload_problem_image(student_id, view_bytes, norm_name)
                    items = grade_image_to_items(storage_url)
            except Exception as grade_err:
                persist_last_error(student_id, "채점 요청 실패", "upload/grade_image", grade_err)
                show_error("채점 요청 실패", grade_err, context="upload_problem_image/grade_image_to_items", show_trace=False)
                if st.button("다시 시도", key=f"grade_retry_{student_id}_{file_hash}"):
                    clear_last_error(student_id)
                    st.rerun()
                _render_items(user, state.get("graded_items") or [])
                return

            try:
                sub_row = upsert_problem_submission(
                    student_user_id=str(student_id),
                    file_hash=str(file_hash),
                    file_name=str(norm_name),
                    storage_path=str(storage_url),
                    storage_url=str(storage_url),
                    status="graded",
                )
                submission_id = sub_row.get("id")
                if not submission_id:
                    raise ValueError("upsert_problem_submission returned without id")

                save_grading_results(
                    submission_id=str(submission_id),
                    student_user_id=str(student_id),
                    items=items,
                )

                state["graded_items"] = items
                state["pending_save"] = None
                clear_last_error(student_id)

                st.success("✅ 채점 완료 + 저장 완료")
                st.rerun()
                return

            except Exception as e:
                submission_id = locals().get("submission_id", None)
                state["pending_save"] = {
                    "student_id": str(student_id),
                    "file_hash": str(file_hash),
                    "file_bytes": view_bytes,
                    "file_name": str(norm_name),
                    "storage_url": str(storage_url),
                    "items": items,
                    "submission_id": submission_id,
                }

                persist_last_error(student_id, "저장 단계 실패(재시도 가능)", "save_grading_results", e)
                show_error("저장 단계 실패(재시도 가능)", e, context="save_grading_results", show_trace=False)

                _dev_debug_box(
                    student_id,
                    "grading save fail debug",
                    {
                        "student_id": student_id,
                        "file_hash": file_hash,
                        "norm_name": norm_name,
                        "storage_url": storage_url,
                        "submission_id": submission_id,
                        "items_count": len(items or []),
                        "cached_found": bool(cached),
                        "exception": f"{type(e).__name__}: {e}",
                    },
                )

                st.warning("위의 '저장 재시도' 버튼으로 이어서 저장할 수 있어요.")

            _render_items(user, state.get("graded_items") or [])

        _render_items(user, state.get("graded_items") or [])

    except DbServiceError as e:
        persist_last_error(student_id, "DB 오류", "grading_panel", e)
        show_error("DB 오류", e, context="grading_panel", show_trace=False)
        _dev_debug_box(student_id, "grading_panel DbServiceError", {"exception": f"{type(e).__name__}: {e}"})

    except Exception as e:
        persist_last_error(student_id, "업로드/처리 실패", "normalize_upload/preview", e)
        show_error("업로드/처리 실패", e, context="normalize_upload/preview", show_trace=False)
        _dev_debug_box(student_id, "normalize_upload/preview error", {"exception": f"{type(e).__name__}: {e}"})