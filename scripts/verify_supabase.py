#!/usr/bin/env python3
"""
코드 ↔ Supabase 연결·스키마 점검 스크립트
실행: python3 scripts/verify_supabase.py

비개발자: 이 스크립트를 실행한 뒤 출력 메시지를 확인하세요.
"""

import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import config
except ImportError:
    print("❌ config 로드 실패. 프로젝트 루트에서 실행하세요: python3 scripts/verify_supabase.py")
    sys.exit(1)


def main():
    print("=" * 50)
    print("StudyT2C ↔ Supabase 점검")
    print("=" * 50)

    # 1) 환경 변수
    url = config.get_supabase_url()
    anon = config.get_supabase_anon_key()
    service = config.get_supabase_service_role_key()

    print("\n1. 환경 변수")
    print(f"   SUPABASE_URL: {'✅ 설정됨' if url else '❌ 없음'}")
    print(f"   SUPABASE_ANON_KEY: {'✅ 설정됨' if anon else '❌ 없음'}")
    print(f"   SUPABASE_SERVICE_ROLE_KEY: {'✅ 설정됨' if service else '❌ 없음 (채팅 저장/이력 조회에 필요)'}")

    if not url or not anon:
        print("\n❌ SUPABASE_URL, SUPABASE_ANON_KEY가 필요합니다. .env 파일을 확인하세요.")
        sys.exit(1)

    # 2) 연결 테스트
    print("\n2. Supabase 연결 테스트")
    try:
        from services.supabase_client import supabase
        res = supabase.table("users").select("id").limit(1).execute()
        print(f"   users 테이블 조회: ✅ 성공")
    except Exception as e:
        print(f"   users 테이블 조회: ❌ 실패 - {e}")

    # 3) chat_messages 테이블 확인
    print("\n3. chat_messages 테이블")
    try:
        from services.supabase_client import supabase
        res = supabase.table("chat_messages").select("id, student_user_id, role, content, meta, created_at").limit(1).execute()
        rows = res.data or []
        print("   role, content, meta 컬럼 조회: ✅ 쿼리 성공 (컬럼 존재)")
        if rows:
            r = rows[0]
            has_role = r.get("role") is not None
            has_content = r.get("content") is not None
            has_meta = r.get("meta") is not None
            if not (has_role or has_content):
                print("   (데이터는 role/content가 NULL - 새로 저장하면 채워짐)")
    except Exception as e:
        err = str(e).lower()
        if "column" in err or "does not exist" in err:
            print(f"   ❌ 컬럼 없음: {e}")
            print("   → docs/SUPABASE_점검_가이드.md 의 2단계 SQL 실행 필요")
        else:
            print(f"   ❌ {e}")

    # 4) service role 쓰기 테스트 (선택)
    if service:
        print("\n4. service_role 쓰기 권한")
        print("   (실제 INSERT는 하지 않고, 클라이언트 로드만 확인)")
        try:
            from services.supabase_client import supabase_service
            if supabase_service:
                print("   service_role 클라이언트: ✅ 로드됨")
            else:
                print("   service_role: ❌ None")
        except Exception as e:
            print(f"   ❌ {e}")
    else:
        print("\n4. service_role: ⚠️ 미설정 → 채팅 저장/이력 조회가 실패할 수 있음")

    print("\n" + "=" * 50)
    print("점검 완료. 문제가 있으면 docs/SUPABASE_점검_가이드.md 를 참고하세요.")
    print("=" * 50)


if __name__ == "__main__":
    main()
