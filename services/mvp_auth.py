# services/mvp_auth.py
"""
MVP 테스트용 로그인: studyt2c.streamlit.app 에서 id/pwd 로그인.
- david / joshua (비밀번호 = 아이디와 동일)
- users.password_hash 에 해시 저장
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

import config

MVP_LOGIN_IDS = ["david", "joshua"]
# 비밀번호 해시용 salt (env에서 바꿀 수 있음)
def _salt() -> str:
    return (config.get_env_var("MVP_AUTH_SALT") or "studyt2c-mvp-2025").strip()


def hash_password(plain: str) -> str:
    """단방향 해시 (MVP용)."""
    return hashlib.sha256((_salt() + (plain or "").strip()).encode()).hexdigest()


def verify_login(login_id: str, password: str) -> Optional[Dict[str, Any]]:
    """
    login_id(handle) + password 로 로그인 검증.
    성공 시 앱에서 쓰는 형태의 user dict 반환, 실패 시 None.
    """
    login_id = (login_id or "").strip().lower()
    password = (password or "").strip()
    if not login_id or not password:
        return None

    from services.supabase_client import supabase_service, supabase
    sb = supabase_service if supabase_service is not None else supabase
    try:
        rows = (
            sb.table("users")
            .select("id, handle, role, status, detail_permission, show_practice_answer, password_hash")
            .eq("handle", login_id)
            .limit(1)
            .execute()
            .data
            or []
        )
        if not rows:
            return None
        u = rows[0]
        stored_hash = (u.get("password_hash") or "").strip()
        if not stored_hash:
            return None
        if stored_hash != hash_password(password):
            return None
        role = (u.get("role") or "student").strip().lower()
        if role == "admin":
            role = "teacher"
        return {
            "id": u.get("id"),
            "handle": u.get("handle") or login_id,
            "role": role,
            "status": u.get("status") or "break",
            "detail_permission": bool(u.get("detail_permission", False)),
            "show_practice_answer": bool(u.get("show_practice_answer", False)),
        }
    except Exception:
        return None


def ensure_mvp_students() -> None:
    """
    david, joshua 계정이 없으면 생성하고, password_hash 를 설정.
    (비밀번호 = 아이디와 동일)
    """
    from services.supabase_client import supabase_service
    if not supabase_service:
        return
    for name in MVP_LOGIN_IDS:
        name = name.strip().lower()
        pwd_hash = hash_password(name)
        try:
            existing = (
                supabase_service.table("users")
                .select("id, password_hash")
                .eq("handle", name)
                .limit(1)
                .execute()
                .data
                or []
            )
            if existing:
                row = existing[0]
                if not (row.get("password_hash") or "").strip():
                    supabase_service.table("users").update({
                        "password_hash": pwd_hash,
                        "role": "student",
                    }).eq("id", row["id"]).execute()
            else:
                supabase_service.table("users").insert({
                    "handle": name,
                    "role": "student",
                    "status": "break",
                    "password_hash": pwd_hash,
                }).execute()
        except Exception:
            pass
