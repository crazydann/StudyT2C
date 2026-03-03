import streamlit as st
import streamlit.components.v1 as components
from urllib.parse import urlparse


def storage_path_to_url(supabase, storage_path: str, expires_in: int = 3600) -> str:
    """
    storage_path가:
      - 이미 https:// 로 시작하면 그대로 사용
      - "bucket/path/to/file.ext" 형태면 signed url 생성 시도
      - 실패하면 public url 시도
    """
    if not storage_path:
        return ""

    # 이미 URL인 경우: Supabase signed URL이면 bucket/path를 파싱해 재발급, 그 외에는 그대로 사용
    if storage_path.startswith("http://") or storage_path.startswith("https://"):
        try:
            parsed = urlparse(storage_path)
            if "/storage/v1/object/sign/" in parsed.path:
                # /storage/v1/object/sign/<bucket>/<path/to/file> 형태
                idx = parsed.path.find("/storage/v1/object/sign/") + len("/storage/v1/object/sign/")
                tail = parsed.path[idx:].lstrip("/")
                parts = tail.split("/", 1)
                if len(parts) == 2:
                    bucket, obj_path = parts[0], parts[1]
                    try:
                        res = supabase.storage.from_(bucket).create_signed_url(obj_path, expires_in)
                        if isinstance(res, dict):
                            return (
                                res.get("signedURL")
                                or res.get("signedUrl")
                                or res.get("signed_url")
                                or res.get("url")
                                or ""
                            )
                        if hasattr(res, "get"):
                            return res.get("signedURL") or res.get("signedUrl") or res.get("url") or ""
                    except Exception:
                        pass
        except Exception:
            # 파싱 실패 시 기존 URL 그대로 사용
            return storage_path
        # Supabase 서명 URL이 아니거나 재발급 실패 시, 원본 URL 반환
        return storage_path

    # "bucket/path/to/file" 형태인 경우
    p = storage_path.lstrip("/")
    parts = p.split("/", 1)
    if len(parts) != 2:
        return storage_path

    bucket, obj_path = parts[0], parts[1]

    # 1) signed url
    try:
        res = supabase.storage.from_(bucket).create_signed_url(obj_path, expires_in)
        if isinstance(res, dict):
            return (
                res.get("signedURL")
                or res.get("signedUrl")
                or res.get("signed_url")
                or res.get("url")
                or ""
            )
        if hasattr(res, "get"):
            return res.get("signedURL") or res.get("signedUrl") or res.get("url") or ""
    except Exception:
        pass

    # 2) public url
    try:
        res2 = supabase.storage.from_(bucket).get_public_url(obj_path)
        if isinstance(res2, str):
            return res2
        if isinstance(res2, dict):
            return res2.get("publicUrl") or res2.get("publicURL") or res2.get("url") or ""
        if hasattr(res2, "get"):
            return res2.get("publicUrl") or res2.get("url") or ""
    except Exception:
        pass

    return storage_path


def guess_file_type(url: str) -> str:
    if not url:
        return "unknown"
    u = url.split("?")[0].lower()
    if u.endswith(".pdf"):
        return "pdf"
    if u.endswith(".png") or u.endswith(".jpg") or u.endswith(".jpeg") or u.endswith(".webp"):
        return "image"
    return "unknown"


def render_file_preview(supabase, storage_path: str, key_prefix: str, label: str = "🔗 파일 열기(새 탭)"):
    """
    Streamlit 안전 미리보기:
    - 항상 링크 버튼 제공
    - 이미지면 st.image(url)
    - pdf면 iframe 미리보기 시도
    """
    if not storage_path:
        st.caption("파일 경로 없음")
        return

    view_url = storage_path_to_url(supabase, storage_path)
    if not view_url:
        st.info("파일 URL 생성 실패: 권한/버킷 설정을 확인하세요.")
        st.code(storage_path)
        return

    ftype = guess_file_type(view_url)

    # 링크 버튼
    try:
        st.link_button(label, view_url, use_container_width=True, key=f"{key_prefix}_linkbtn")
    except Exception:
        st.markdown(f"[{label}]({view_url})")

    # 미리보기
    if ftype == "image":
        try:
            st.image(view_url, use_container_width=True)
        except TypeError:
            st.image(view_url, use_column_width=True)
        except Exception:
            st.info("이미지 미리보기를 불러오지 못했습니다. 위 링크로 열어 확인하세요.")

    elif ftype == "pdf":
        st.caption("PDF 미리보기(가능한 경우):")
        try:
            components.iframe(view_url, height=720, scrolling=True)
        except Exception:
            st.info("이 환경에서는 PDF iframe 미리보기가 제한될 수 있어요. 위 링크로 열어 확인하세요.")

    else:
        st.info("미리보기 불가 형식입니다. 위 링크로 열어 확인하세요.")