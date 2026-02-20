import io
from PIL import Image


def rotate_png_bytes(png_bytes: bytes, degrees: int) -> bytes:
    """
    PNG bytes를 90도 단위로 회전 (degrees: 0/90/180/270 or 음수 가능)
    """
    deg = degrees % 360
    if deg == 0:
        return png_bytes

    img = Image.open(io.BytesIO(png_bytes))
    img2 = img.rotate(deg, expand=True)  # 반시계 기본
    out = io.BytesIO()
    img2.save(out, format="PNG")
    return out.getvalue()