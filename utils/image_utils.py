# utils/image_utils.py
import io
import os
import sys
import tempfile
import subprocess
from typing import Tuple

from PIL import Image, ImageOps, UnidentifiedImageError

# pillow-heif (HEIC/HEIF decode)
try:
    import pillow_heif  # type: ignore

    # ✅ plugin opener 등록(가능하면)
    try:
        pillow_heif.register_heif_opener()
    except Exception:
        pass
except Exception:
    pillow_heif = None

# PyMuPDF (PDF -> image)
try:
    import fitz  # type: ignore
except Exception:
    fitz = None


SUPPORTED_IMAGE_EXTS = {"png", "jpg", "jpeg", "heic", "heif", "webp"}


def _safe_exif_transpose(img: Image.Image) -> Image.Image:
    """EXIF orientation 반영(아이폰 가로/세로 뒤집힘 방지)"""
    try:
        return ImageOps.exif_transpose(img)
    except Exception:
        return img


def _is_pdf_bytes(b: bytes) -> bool:
    return bool(b) and b[:4] == b"%PDF"


def _is_heif_like_bytes(b: bytes) -> bool:
    """
    HEIF/HEIC/AVIF는 보통 ISO BMFF 'ftyp' 박스가 앞쪽(4~12)에 있음.
    ftypheic / ftypheix / ftypmif1 / ftypmsf1 / ftyphevc / ftypavif 등.
    """
    if not b or len(b) < 12:
        return False
    if b[4:8] != b"ftyp":
        return False
    brand = b[8:12]
    return brand in {b"heic", b"heix", b"mif1", b"msf1", b"hevc", b"avif"}


def shutil_which(cmd: str):
    """shutil.which 대체(표준 라이브러리 import 최소화용)"""
    try:
        import shutil
        return shutil.which(cmd)
    except Exception:
        return None


def _mac_sips_heic_to_png(file_bytes: bytes) -> Image.Image:
    """
    macOS 내장 sips로 HEIC -> PNG 변환 (pillow_heif/libheif가 거부하는 HEIC 대응)
    - 로컬 Mac MVP에서 가장 안정적인 우회책
    """
    if not shutil_which("sips"):
        raise UnidentifiedImageError(
            "HEIC 디코딩 실패. macOS sips가 없어서 우회 변환을 할 수 없습니다."
        )

    with tempfile.TemporaryDirectory() as td:
        in_path = os.path.join(td, "input.heic")
        out_path = os.path.join(td, "output.png")

        with open(in_path, "wb") as f:
            f.write(file_bytes)

        try:
            subprocess.run(
                ["sips", "-s", "format", "png", in_path, "--out", out_path],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        except Exception as e:
            raise UnidentifiedImageError(f"sips 변환 실패: {e}")

        with open(out_path, "rb") as f:
            png_bytes = f.read()

    img = Image.open(io.BytesIO(png_bytes))
    img = _safe_exif_transpose(img)
    return img


def _heif_bytes_to_pil(file_bytes: bytes) -> Image.Image:
    """
    HEIC/HEIF bytes -> PIL Image

    ✅ 우선순위:
      1) pillow-heif plugin 등록 + PIL.Image.open(BytesIO) 경로 (Cloud에서도 가능)
      2) pillow_heif.read_heif 직접 호출
      3) (macOS 로컬) sips fallback
      4) Cloud/리눅스에서는 변환 불가 안내
    """
    # pillow-heif 자체가 없으면 즉시 안내
    if pillow_heif is None:
        raise UnidentifiedImageError(
            "HEIC/HEIF 파일로 보이지만 pillow-heif가 설치되어 있지 않습니다. "
            "requirements.txt에 pillow-heif를 추가 후 재배포하세요."
        )

    # 1) plugin + PIL open 경로 (aux 이미지 많은 HEIC에서 read_heif보다 잘 되는 경우가 있음)
    try:
        try:
            # 이미 import 되었더라도 안전하게 한번 더
            from pillow_heif import register_heif_opener  # type: ignore
            register_heif_opener()
        except Exception:
            pass

        img = Image.open(io.BytesIO(file_bytes))
        img = _safe_exif_transpose(img)
        if img.mode != "RGB":
            img = img.convert("RGB")
        return img
    except Exception:
        pass

    # 2) read_heif 직접 호출
    try:
        heif = pillow_heif.read_heif(file_bytes)
        img = Image.frombytes(
            heif.mode,
            heif.size,
            heif.data,
            "raw",
            heif.mode,
            heif.stride,
        )
        img = _safe_exif_transpose(img)
        if img.mode != "RGB":
            img = img.convert("RGB")
        return img

    except Exception as e:
        msg = str(e)

        # 3) macOS면 sips로 우회 (Cloud에는 없음)
        if sys.platform == "darwin" and shutil_which("sips"):
            try:
                img = _mac_sips_heic_to_png(file_bytes)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                return img
            except Exception:
                pass

        # 4) Cloud/리눅스: sips 없음 → 안내
        raise UnidentifiedImageError(
            f"HEIC 디코딩 실패({msg}). "
            "이 HEIC는 Live Photo/보조 이미지가 포함된 형식일 수 있어 서버에서 변환이 어렵습니다. "
            "JPG/PNG로 변환 후 업로드해 주세요."
        )


def _open_image_bytes(file_bytes: bytes, filename: str = "") -> Image.Image:
    """
    일반 이미지/JPG/PNG/WEBP + HEIC/HEIF까지 안정적으로 open.
    """
    # bytes 기반 감지 우선
    if _is_heif_like_bytes(file_bytes):
        return _heif_bytes_to_pil(file_bytes)

    ext = ""
    if filename and "." in filename:
        ext = filename.rsplit(".", 1)[-1].lower()

    if ext in {"heic", "heif"}:
        # HEIC/HEIF는 전용 디코더 우선
        return _heif_bytes_to_pil(file_bytes)

    # 일반 이미지 시도
    try:
        img = Image.open(io.BytesIO(file_bytes))
        img = _safe_exif_transpose(img)
        return img
    except UnidentifiedImageError:
        # 혹시 헤더 감지가 실패한 HEIF면 한 번 더 시도
        if pillow_heif is not None:
            return _heif_bytes_to_pil(file_bytes)
        raise


def _render_pdf_first_page(pdf_bytes: bytes, dpi: int = 180) -> Image.Image:
    if fitz is None:
        raise ValueError("PDF 변환을 위해 PyMuPDF(fitz)가 필요합니다. requirements에 PyMuPDF가 있는지 확인하세요.")

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    if doc.page_count < 1:
        raise ValueError("빈 PDF 입니다.")

    page = doc.load_page(0)
    zoom = dpi / 72.0
    mat = fitz.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=mat, alpha=False)

    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    img = _safe_exif_transpose(img)
    return img


def normalize_upload(file_bytes: bytes, filename: str) -> Tuple[bytes, str]:
    """
    업로드 파일(이미지/HEIC/PDF)을 분석 가능한 PNG bytes로 정규화한다.
    return: (png_bytes, normalized_filename.png)
    """
    if not filename:
        filename = "upload"

    name = os.path.basename(filename)
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""

    # bytes 헤더 우선
    if _is_pdf_bytes(file_bytes) or ext == "pdf":
        img = _render_pdf_first_page(file_bytes)
        if img.mode != "RGB":
            img = img.convert("RGB")
        out = io.BytesIO()
        img.save(out, format="PNG")
        new_name = (name.rsplit(".", 1)[0] if "." in name else name) + ".png"
        return out.getvalue(), new_name

    # 이미지(확장자 없거나 이상해도 bytes 기반으로 열기)
    if ext in SUPPORTED_IMAGE_EXTS or ext == "" or _is_heif_like_bytes(file_bytes):
        img = _open_image_bytes(file_bytes, filename=name)

        # RGB로 통일
        if img.mode == "RGBA":
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            if img.mode != "RGB":
                img = img.convert("RGB")

        out = io.BytesIO()
        img.save(out, format="PNG")
        new_name = (name.rsplit(".", 1)[0] if "." in name else name) + ".png"
        return out.getvalue(), new_name

    raise ValueError(f"지원하지 않는 파일 형식입니다: .{ext}")