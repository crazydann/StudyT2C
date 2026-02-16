import io
from PIL import Image
import pillow_heif
import fitz  # PyMuPDF

# 플러그인 등록 (이 한 줄이 HEIC를 마법처럼 열어줍니다)
pillow_heif.register_heif_opener()

def normalize_upload(file_bytes: bytes, filename: str) -> tuple[bytes, str]:
    ext = filename.split('.')[-1].lower()
    try:
        if ext == 'pdf':
            # PDF를 이미지(PNG)로 변환
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page = doc.load_page(0)
            pix = page.get_pixmap(dpi=150)
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='PNG')
            return img_byte_arr.getvalue(), filename.rsplit('.', 1)[0] + ".png"
            
        elif ext in ['heic', 'heif']:
            # v2에서 완벽하게 작동했던 HEIC 처리 방식
            image = Image.open(io.BytesIO(file_bytes))
            if image.mode != "RGB": 
                image = image.convert("RGB")
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            return img_byte_arr.getvalue(), filename.rsplit('.', 1)[0] + ".png"
            
        else:
            # 일반 PNG, JPG는 원본 그대로 통과
            return file_bytes, filename
            
    except Exception as e:
        raise Exception(f"파일 변환 실패: {str(e)}")