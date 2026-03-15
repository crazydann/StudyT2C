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
    """캐시된 유저 목록 (ttl=10초). 설정 변경 시 10초 내 자동 갱신."""
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


# 어드민: 메인 상단 역할 선택 + 계정 선택 (왼쪽 프레임 제거)
def _admin_role_options():
    return [
        ("student", "학생"),
        ("parent", "부모"),
        ("teacher", "선생님"),
    ]


def _filter_users_by_role(users: list, role: str):
    if role == "student":
        from ui.ui_common import MVP_STUDENT_HANDLES
        out = [u for u in users if u.get("role") == "student" and (u.get("handle") or "").strip().lower() in MVP_STUDENT_HANDLES]
        # David 먼저, 그다음 Joshua
        out.sort(key=lambda u: (0 if (u.get("handle") or "").strip().lower() == "david" else 1, (u.get("handle") or "").lower()))
        return out
    out = [u for u in users if u.get("role") == role]
    out.sort(key=lambda u: (u.get("handle") or "").lower())
    return out


def _render_admin_header_card(users):
    """메인 상단: StudyT2C + 역할 버튼(학생/부모/선생님) + 서비스 소개 + 설정."""
    from ui.service_intro_dialog import render_service_intro_button_inline

    role_opts = _admin_role_options()
    if "admin_role" not in st.session_state:
        st.session_state["admin_role"] = "student"

    with st.container(border=True):
        row = st.columns([2, 3, 1])
        with row[0]:
            st.markdown("### StudyT2C")
            st.caption("오프라인 수업 개인화 보조 · 계정 선택")
        with row[1]:
            r1, r2, r3 = st.columns(3)
            for col, (role_key, role_label) in zip([r1, r2, r3], role_opts):
                with col:
                    if st.button(role_label, key=f"admin_role_{role_key}", type="primary" if st.session_state.get("admin_role") == role_key else "secondary", use_container_width=True):
                        st.session_state["admin_role"] = role_key
                        st.session_state.pop("current_user", None)
                        st.rerun()
        with row[2]:
            render_service_intro_button_inline()
            with st.expander("설정", expanded=False):
                if "admin_dev_mode" not in st.session_state:
                    st.session_state["admin_dev_mode"] = st.session_state.get("dev_mode", False)
                st.toggle("개발 모드", key="admin_dev_mode")
                st.session_state["dev_mode"] = st.session_state.get("admin_dev_mode", False)
                if st.button("다른 계정 선택", key="admin_clear_user"):
                    st.session_state.pop("current_user", None)
                    st.rerun()


def main_account_picker_or_console(users):
    """
    왼쪽 프레임 없이 메인만 사용: 상단 카드(역할 버튼 + 설정) + 계정 선택 또는 콘솔.
    """
    _sync_current_user_with_latest(users)
    role = st.session_state.get("admin_role", "student")
    current = st.session_state.get("current_user")

    # 역할과 맞는 계정인지 확인; 아니면 선택 해제
    if current and current.get("role") != role:
        st.session_state.pop("current_user", None)
        current = None

    _render_admin_header_card(users)

    filtered = _filter_users_by_role(users, role)
    if not filtered:
        st.info(f"해당 역할({role})의 계정이 없습니다.")
        return None

    # 계정 미선택 시: 첫 계정으로 자동 선택 후 바로 화면 진입 (학생=David, 부모=첫 부모, 선생=첫 선생)
    if not current or current.get("id") not in {u["id"] for u in filtered}:
        st.session_state["current_user"] = filtered[0]
        st.session_state["_admin_role_users"] = filtered
        st.rerun()

    st.session_state["_admin_role_users"] = filtered  # 학생 전환 등에서 사용
    return current


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

    # 어드민: 서비스 소개는 '서비스 소개' 버튼을 눌렀을 때만 노출. 첫 진입(계정 미선택) 시 대화 상태 초기화.
    if not st.session_state.get("current_user"):
        st.session_state.pop("open_service_intro_dialog", None)
        st.session_state.pop("service_intro_authenticated", None)

    st.session_state["_admin_flow"] = True  # 어드민 플로우에서만 설정; 콘솔에서 dev_mode 중복 키 방지
    current_user = main_account_picker_or_console(users)
    if not current_user:
        st.stop()

    from ui.service_intro_dialog import maybe_show_service_intro_dialog
    maybe_show_service_intro_dialog()

    _ensure_user_switch_safety(current_user["id"])

    role = current_user.get("role")
    # 어드민 학생 뷰: 현재 학생 옆에 David/Joshua 전환
    role_users = st.session_state.get("_admin_role_users") or []
    if role == "student" and st.session_state.get("_admin_flow") and len(role_users) >= 1:
        row = st.columns([1, 3])
        with row[0]:
            options = [u["handle"] for u in role_users]
            idx = next((i for i, u in enumerate(role_users) if u.get("id") == current_user.get("id")), 0)
            sel = st.selectbox("학생", options, index=idx, key="admin_student_switcher", label_visibility="collapsed")
            if options and sel != current_user.get("handle"):
                chosen = next((u for u in role_users if (u.get("handle") or "") == sel), None)
                if chosen:
                    st.session_state["current_user"] = chosen
                    st.rerun()
        with row[1]:
            st.caption(f"**{current_user.get('handle')}** · {role}")
    else:
        st.caption(f"**{current_user.get('handle')}** · {role}")

    route_to_ui(role, current_user)


if __name__ == "__main__":
    main()