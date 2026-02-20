"""
image_utils.py (shim)

프로젝트 내 import 호환을 위한 연결용 파일입니다.
실제 구현은 utils/image_utils.py 에 있습니다.

- 기존 코드: from image_utils import normalize_upload
- 새 구조: from utils.image_utils import normalize_upload

둘 다 동작하도록 유지합니다.
"""

from utils.image_utils import normalize_upload  # noqa: F401