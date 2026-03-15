# 앱 진입 시 가장 먼저 .env 로드 (Streamlit 실행 경로와 무관하게 프로젝트 루트 .env 사용)
from pathlib import Path
from dotenv import load_dotenv
_env_path = Path(__file__).resolve().parent / ".env"
if _env_path.exists():
    load_dotenv(_env_path)

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

        /* 5. Expander·카드 정리 */
        div[data-testid="stExpander"] {
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }
        div[data-testid="stExpander"] > div[role="button"] {
            font-size: 0.9rem;
        }
        /* 6. 메인 = 내용 위주: 카드 테두리 제거, 여백만 */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: none;
            border-radius: 8px;
            padding: 0.75rem 0;
            box-shadow: none;
        }
        /* 7. 브라우저 탭 느낌: 탭 리스트를 상단 띠처럼 */
        .stTabs [data-baseweb="tab-list"] {
            gap: 0;
            background: #f1f5f9;
            border-bottom: 1px solid #e2e8f0;
            padding: 0 0 0 6px;
            margin: 0 -1rem;
            min-height: 40px;
        }
        .stTabs [data-baseweb="tab"] {
            background: transparent;
            border: 1px solid transparent;
            border-bottom: none;
            border-radius: 8px 8px 0 0;
            padding: 8px 16px;
            margin: 6px 2px 0 0;
            font-size: 0.9rem;
            height: auto;
        }
        .stTabs [data-baseweb="tab"]:first-child { margin-left: 0; }
        .stTabs [aria-selected="true"] {
            background: #fff !important;
            border-color: #e2e8f0 !important;
            border-bottom: 1px solid #fff !important;
            margin-bottom: -1px;
            font-weight: 600;
        }
        /* 8. 상단 탭 라디오(커스텀 탭바) 브라우저 탭 느낌 */
        div[data-testid="stHorizontalBlock"] .stRadio > div {
            flex-wrap: nowrap;
            gap: 0;
            background: #f1f5f9;
            border-radius: 8px 8px 0 0;
            padding: 4px 4px 0;
            border-bottom: 1px solid #e2e8f0;
        }
        div[data-testid="stHorizontalBlock"] .stRadio label {
            padding: 8px 14px;
            border-radius: 6px 6px 0 0;
            font-size: 0.9rem;
            background: transparent;
        }
        div[data-testid="stHorizontalBlock"] .stRadio label[data-checked="true"] {
            background: #fff !important;
            font-weight: 600;
            box-shadow: 0 -1px 0 #e2e8f0;
        }
        /* 9. 서브헤더·캡션 축소 → 내용 위주 */
        h3 { font-size: 1.05rem !important; margin-top: 0.5rem !important; }
        .stCaptionContainer { font-size: 0.8rem !important; }
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
    if st.sidebar.button("🔄 새로고침", use_container_width=True):
        try:
            fetch_users_cached.clear()
        except Exception:
            try:
                st.cache_data.clear()
            except Exception:
                pass
        st.rerun()


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
    st.sidebar.title("StudyT2C")
    from ui.service_intro_dialog import render_service_intro_button_sidebar
    render_service_intro_button_sidebar()
    st.sidebar.caption("계정 선택")
    _refresh_button()

    role_filter = st.sidebar.radio(
        "역할",
        options=["전체", "student", "parent", "teacher"],
        index=0,
        horizontal=False,
    )
    if role_filter == "전체":
        role_filter = "ALL"
    q = st.sidebar.text_input("검색", value="", placeholder="이름 검색")

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

    st.sidebar.caption(f"**{selected_user['handle']}** · {selected_user['role']}")

    if st.sidebar.button("다른 계정 선택", use_container_width=True):
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
    """
    로그인학생 화면 모드 여부.
    - studyt2c.streamlit.app 기본: 로그인 → 로그인학생 화면 (True)
    - 기존 계정 선택(관리자) 화면: ?app=admin 으로 접근 (False)
    """
    try:
        q = getattr(st, "query_params", None)
        if q is not None and hasattr(q, "get"):
            raw = q.get("app") or q.get("admin") or ""
        else:
            q = getattr(st, "experimental_get_query_params", lambda: {})()
            raw = (q.get("app") or q.get("admin") or [""])
            raw = raw[0] if isinstance(raw, (list, tuple)) else raw
        app_val = (raw[0] if isinstance(raw, (list, tuple)) else raw) or ""
    except Exception:
        app_val = ""
    app_val = str(app_val).strip().lower()

    # ?app=admin → 계정 선택(기존) 화면
    if app_val == "admin":
        st.session_state["_student_login_mode"] = False
        return False
    # ?app=student → 명시적 로그인학생 화면
    if app_val in ("student", "1", "true"):
        st.session_state["_student_login_mode"] = True
        return True

    # 쿼리 없음: studyt2c.streamlit.app 기본 → 로그인학생 화면
    if not app_val:
        return True

    # 기타 값이면 config/env 확인
    try:
        import config
        if hasattr(config, "is_student_login_app") and callable(config.is_student_login_app):
            return config.is_student_login_app()
    except Exception:
        pass
    import os
    v = os.environ.get("STUDENT_LOGIN_APP", "")
    # STUDENT_LOGIN_APP이 명시적으로 "0"/"false"면 admin 기본, 없거나 true면 학생 로그인 기본
    if str(v).strip().lower() in ("0", "false", "no"):
        return False
    return True


def main():
    # studyt2c.streamlit.app 전용: 로그인 화면 → 로그인학생 화면(문제 채점기 + AI 튜터만)
    if _is_student_login_app():
        from ui.mvp_login import render_login_page
        from ui.mvp_student_view import render_mvp_student_view
        from ui.service_intro_dialog import maybe_show_service_intro_dialog
        if not st.session_state.get("mvp_user"):
            render_login_page()
            return
        maybe_show_service_intro_dialog()
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

    from ui.service_intro_dialog import maybe_show_service_intro_dialog
    maybe_show_service_intro_dialog()

    _ensure_user_switch_safety(current_user["id"])

    role = current_user.get("role")

    st.title("StudyT2C")
    st.caption(f"{current_user.get('handle')} · {role}")

    route_to_ui(role, current_user)


if __name__ == "__main__":
    main()