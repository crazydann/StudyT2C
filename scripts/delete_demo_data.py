#!/usr/bin/env python3
"""
데모 시드로 넣은 데이터만 삭제 (handle에 '_demo_' 포함 유저 및 연관 데이터).
실제로 쌓인 데이터(david, joshua 등)는 건드리지 않음.

실행: python3 scripts/delete_demo_data.py
(SUPABASE_SERVICE_ROLE_KEY 또는 .env 설정 필요)
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from services.demo_seed import delete_demo_data
except ImportError as e:
    print("❌ import 실패:", e)
    print("   프로젝트 루트에서 실행하세요: python3 scripts/delete_demo_data.py")
    sys.exit(1)


def main():
    print("데모 데이터 삭제 중... (handle에 '_demo_' 포함 유저만 대상)")
    result = delete_demo_data()
    if result.get("ok"):
        print("✅", result.get("message", "완료."))
        if result.get("deleted"):
            print("   삭제된 테이블별:", result["deleted"])
    else:
        print("❌", result.get("message", "실패."))
        sys.exit(1)


if __name__ == "__main__":
    main()
