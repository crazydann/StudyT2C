import uuid
from services.supabase_client import supabase

def upload_problem_image(student_id: str, file_bytes: bytes, file_name: str) -> str:
    """
    Supabase Storage에 이미지를 안전하게 업로드하고,
    AI가 읽을 수 있도록 60분짜리 임시 보안 URL(Signed URL)을 반환합니다.
    """
    # 1. 파일 이름이 겹치지 않게 고유한 이름(UUID) 생성
    file_ext = file_name.split(".")[-1]
    unique_filename = f"{student_id}/{uuid.uuid4()}.{file_ext}"
    bucket_name = "problem_images"
    
    try:
        # 2. 스토리지에 파일 업로드
        supabase.storage.from_(bucket_name).upload(unique_filename, file_bytes)
        
        # 3. 60분(3600초) 동안만 유효한 보안 URL 생성
        signed_url_res = supabase.storage.from_(bucket_name).create_signed_url(unique_filename, 3600)
        
        # Supabase Python 클라이언트 버전에 따라 반환 형식이 다를 수 있음
        if isinstance(signed_url_res, dict) and 'signedURL' in signed_url_res:
             return signed_url_res['signedURL']
        return signed_url_res
    except Exception as e:
        raise Exception(f"이미지 업로드 중 오류 발생: {str(e)}")