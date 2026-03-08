import streamlit as st

st.set_page_config(page_title="StudyT2C", layout="wide")


def apply_custom_css():
    st.markdown(
        """
        <style>
        /* 1. 웹 폰트 적용 (Pretendard) */
        @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
        html, body, [class*="css"] {
            font-family: 'Pretendard', system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
        }

        /* 2. Streamlit 기본 메뉴 및 푸터 숨기기 (헤더는 유지) */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}

        /* 3. 전체 레이아웃 폭 및 여백 조정 */
        div.block-container {
            max-width: 1200px;
            padding-top: 1.5rem;
            padding-bottom: 2rem;
        }

        /* 4. 기본 버튼 스타일 (둥글고 가벼운 그림자) */
        .stButton>button, .stDownloadButton>button {
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.25s ease;
        }
        .stButton>button:hover, .stDownloadButton>button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(15, 23, 42, 0.16);
        }

        /* 5. Expander를 카드처럼 보이게 */
        div[data-testid="stExpander"] {
            border-radius: 10px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(15, 23, 42, 0.08);
            background-color: #ffffff;
        }
        div[data-testid="stExpander"] > div[role="button"] {
            background-color: #f8fafc;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


apply_custom_css()

# ✅ HEIC/HEIF 지원(Cloud 포함)
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except Exception:
    pass
    
from services.supabase_client import supabase


def normalize_role(role: str | None) -> str:
    if not role:
        return "unknown"
    role = role.strip().lower()
    if role == "admin":
        return "teacher"
    return role


@st.cache_data(ttl=10)
def fetch_users_cached():
    """
    ✅ 캐시된 유저 목록 (ttl=10초)
    - Parent에서 설정 바꾸면 10초 내 자동 갱신되거나,
      sidebar 새로고침 버튼으로 즉시 갱신 가능
    """
    resp = (
        supabase.table("users")
        .select("id, handle, role, status, detail_permission, show_practice_answer")
        .execute()
    )
    raw_users = resp.data or []

    users = []
    for u in raw_users:
        uid = u.get("id")
        role = normalize_role(u.get("role"))
        if not uid or role == "unknown":
            continue
        users.append(
            {
                "id": uid,
                "handle": u.get("handle") or f"user-{uid}",
                "role": role,
                "_raw_role": (u.get("role") or "").strip().lower(),
                "status": u.get("status") or "break",
                "detail_permission": bool(u.get("detail_permission", False)),
                "show_practice_answer": bool(u.get("show_practice_answer", False)),
            }
        )

    users.sort(key=lambda x: (x.get("role", ""), x.get("handle", "")))
    return users


def _badge(text: str, bg: str = "#1f2937"):
    st.sidebar.markdown(
        f"""
        <div style="
            display:inline-block;
            padding:6px 10px;
            border-radius:999px;
            background:{bg};
            color:white;
            font-size:12px;
            margin:2px 4px 2px 0;
            ">
            {text}
        </div>
        """,
        unsafe_allow_html=True,
    )


def _refresh_button():
    c1, c2 = st.sidebar.columns([1, 1])
    with c1:
        if st.button("🔄 새로고침", use_container_width=True):
            try:
                fetch_users_cached.clear()
            except Exception:
                # 구버전 호환
                try:
                    st.cache_data.clear()
                except Exception:
                    pass
            st.rerun()
    with c2:
        st.caption("ttl=10s")


def _sync_current_user_with_latest(users: list):
    """
    ✅ current_user를 캐시된 users 목록의 최신 필드로 동기화
    (status/permission 변경이 즉시 반영되도록)
    """
    cur = st.session_state.get("current_user")
    if not cur:
        return
    cur_id = cur.get("id")
    if not cur_id:
        return

    latest = None
    for u in users:
        if u.get("id") == cur_id:
            latest = u
            break

    if latest:
        # handle/role/status/permission 등 갱신
        st.session_state["current_user"] = {**cur, **latest}


def sidebar_account_picker(users):
    st.sidebar.title("🔐 계정 선택 (MVP)")
    _refresh_button()

    role_filter = st.sidebar.radio(
        "Role",
        options=["ALL", "student", "parent", "teacher"],
        index=0,
        horizontal=False,
    )
    q = st.sidebar.text_input("검색(handle)", value="", placeholder="예) minsu")

    def match(u):
        if role_filter != "ALL" and u["role"] != role_filter:
            return False
        if q and q.lower() not in (u["handle"] or "").lower():
            return False
        return True

    filtered = [u for u in users if match(u)]
    if not filtered:
        st.sidebar.info("조건에 맞는 계정이 없습니다.")
        return None

    labels = []
    id_by_label = {}
    user_by_id = {}
    for u in filtered:
        raw = u.get("_raw_role", "")
        role_label = u["role"]
        if raw == "admin":
            label = f"{u['handle']}  ·  {role_label} (was admin)"
        else:
            label = f"{u['handle']}  ·  {role_label}"
        labels.append(label)
        id_by_label[label] = u["id"]
        user_by_id[u["id"]] = u

    current = st.session_state.get("current_user")
    default_index = 0
    if current and current.get("id") in user_by_id:
        for i, u in enumerate(filtered):
            if u["id"] == current["id"]:
                default_index = i
                break

    selected_label = st.sidebar.radio(
        "계정 목록",
        options=labels,
        index=default_index,
        label_visibility="collapsed",
    )

    selected_id = id_by_label[selected_label]
    selected_user = user_by_id[selected_id]

    # 선택이 바뀌면 current_user 갱신
    if (not current) or (current.get("id") != selected_user.get("id")):
        st.session_state["current_user"] = selected_user
        st.rerun()

    st.sidebar.divider()

    # ✅ 상태 배지(요약)
    st.sidebar.subheader("📌 현재 상태")
    _badge(f"@{selected_user['handle']}", bg="#0f766e")
    _badge(f"role: {selected_user['role']}", bg="#334155")

    mode = selected_user.get("status") or "break"
    _badge(f"mode: {mode}", bg="#16a34a" if mode == "studying" else "#f59e0b")

    dp = bool(selected_user.get("detail_permission", False))
    spa = bool(selected_user.get("show_practice_answer", False))
    _badge(f"detail: {'ON' if dp else 'OFF'}", bg="#4f46e5" if dp else "#6b7280")
    _badge(f"answer: {'ON' if spa else 'OFF'}", bg="#4f46e5" if spa else "#6b7280")

    st.sidebar.caption("※ 권한/모드는 Parent 화면에서 변경됩니다.")

    if st.sidebar.button("로그아웃(선택 해제)", use_container_width=True):
        st.session_state.pop("current_user", None)
        st.rerun()

    return selected_user


def _ensure_user_switch_safety(current_user_id: str):
    prev = st.session_state.get("active_user_id")
    if prev != current_user_id:
        st.session_state["active_user_id"] = current_user_id
        for k in ["last_file_hash", "last_uploaded_name"]:
            if k in st.session_state:
                st.session_state.pop(k, None)


def route_to_ui(role, user):
    if role == "teacher":
        from ui import ui_teacher
        ui_teacher.render(supabase, user)
    elif role == "parent":
        from ui import ui_parent
        ui_parent.render(supabase, user)
    elif role == "student":
        from ui import ui_student
        ui_student.render(supabase, user)
    else:
        st.error(f"알 수 없는 role: {role}")


def _is_student_login_app() -> bool:
    """STUDENT_LOGIN_APP env이 true면 로그인학생 화면 모드. config 의존 최소화."""
    try:
        import config
        fn = getattr(config, "is_student_login_app", None)
        if callable(fn):
            return fn()
    except Exception:
        pass
    import os
    v = os.environ.get("STUDENT_LOGIN_APP") or ""
    return str(v).strip().lower() in ("1", "true", "yes")


def main():
    # studyt2c.streamlit.app 전용: 로그인 화면 → 로그인학생 화면(문제 채점기 + AI 튜터만)
    if _is_student_login_app():
        from ui.mvp_login import render_login_page
        from ui.mvp_student_view import render_mvp_student_view
        if not st.session_state.get("mvp_user"):
            render_login_page()
            return
        st.title("StudyT2C (MVP 테스트)")
        render_mvp_student_view(supabase, st.session_state["mvp_user"])
        return

    # 기존: admin 등 계정 선택 후 전체 화면
    try:
        users = fetch_users_cached()
    except Exception as e:
        st.error(f"DB 오류: {e}")
        st.stop()

    if not users:
        st.warning("users 테이블에 계정이 없습니다.")
        st.stop()

    # ✅ current_user 최신값 동기화(권한/모드 갱신)
    _sync_current_user_with_latest(users)

    current_user = sidebar_account_picker(users)
    if not current_user:
        st.stop()

    _ensure_user_switch_safety(current_user["id"])

    role = current_user.get("role")

    st.title("StudyT2C (MVP)")
    st.caption(f"현재 계정: {current_user.get('handle')} · role={role}")

    route_to_ui(role, current_user)


if __name__ == "__main__":
    main()