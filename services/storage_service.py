import logging
import uuid
from typing import Any

from services.supabase_client import supabase

logger = logging.getLogger("studyt2c.storage")


class StorageServiceError(Exception):
    """스토리지 업로드/URL 발급 관련 에러를 명확히 전달하기 위한 예외."""


def upload_problem_image(student_id: str, file_bytes: bytes, file_name: str) -> str:
    """
    Supabase Storage에 이미지를 업로드하고,
    AI가 읽을 수 있도록 Signed URL(기본 60분)을 반환합니다.

    실패 시 StorageServiceError 발생 (UI에서 잡아 메시지 표출)
    """
    if not student_id:
        raise StorageServiceError("student_id가 비어 있습니다.")
    if not file_bytes:
        raise StorageServiceError("업로드할 파일 바이트가 비어 있습니다.")
    if not file_name:
        file_name = "upload.bin"

    file_ext = file_name.split(".")[-1].lower() if "." in file_name else "bin"
    unique_filename = f"{student_id}/{uuid.uuid4()}.{file_ext}"
    bucket_name = "problem_images"

    try:
        # upload()가 성공/실패를 어떤 형태로 반환하든 예외 기반으로 처리
        supabase.storage.from_(bucket_name).upload(unique_filename, file_bytes)

        signed_url_res: Any = supabase.storage.from_(bucket_name).create_signed_url(unique_filename, 3600)

        # supabase client 버전별 반환 형식 처리
        if isinstance(signed_url_res, dict):
            if "signedURL" in signed_url_res:
                return signed_url_res["signedURL"]
            if "signedUrl" in signed_url_res:
                return signed_url_res["signedUrl"]
            if "data" in signed_url_res and isinstance(signed_url_res["data"], dict):
                d = signed_url_res["data"]
                if "signedUrl" in d:
                    return d["signedUrl"]
                if "signedURL" in d:
                    return d["signedURL"]

        if isinstance(signed_url_res, str):
            return signed_url_res

        # 마지막 fallback
        raise StorageServiceError(f"Signed URL 응답 형식을 해석할 수 없습니다: {signed_url_res}")

    except StorageServiceError:
        raise
    except Exception as e:
        logger.exception("upload_problem_image failed: %s", e)
        raise StorageServiceError(f"이미지 업로드 중 오류 발생: {e}")