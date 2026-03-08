# MVP 테스트 배포: 로그인학생 화면 (studyt2c.streamlit.app)

## 개요

- **studyt2c.streamlit.app**  
  로그인 화면 → 로그인한 학생만 **문제 채점기** + **AI 튜터** 사용 (로그인학생 화면).
- **admin.studyt2c.streamlit.app** (또는 별도 앱)  
  기존처럼 계정 선택 후 학생/학부모/선생 전체 화면.

같은 코드베이스로 두 URL에서 다르게 동작하려면 **배포별 환경 변수**만 다르게 설정하면 됩니다.

---

## 1. studyt2c.streamlit.app 배포 설정

Streamlit Cloud에서 해당 앱의 **Settings → Secrets (또는 Environment variables)** 에서:

| 변수 | 값 | 비고 |
|------|-----|------|
| `STUDENT_LOGIN_APP` | `true` | 로그인 모드 사용 |
| `SUPABASE_URL` | (동일) | |
| `SUPABASE_ANON_KEY` | (동일) | |
| `SUPABASE_SERVICE_ROLE_KEY` | (동일) | david/joshua 자동 생성에 필요 |
| `GROQ_API_KEY` | (동일) | AI 튜터용 |

---

## 2. DB: password_hash 컬럼

Supabase **SQL Editor**에서 한 번 실행:

- 파일: `supabase/migrations/users_password_hash_mvp.sql`  
- 내용: `users` 테이블에 `password_hash` 컬럼 추가.

---

## 3. MVP 테스트 계정 (자동 생성)

`STUDENT_LOGIN_APP=true` 이고 `SUPABASE_SERVICE_ROLE_KEY` 가 설정된 상태에서,  
**로그인 화면을 한 번만 열면** 아래 두 계정이 없을 때 자동으로 생성됩니다.

| 아이디 | 비밀번호 |
|--------|----------|
| david  | david    |
| joshua | joshua   |

이미 `handle` 이 david / joshua 인 행이 있으면, `password_hash` 만 채워 줍니다.

---

## 4. 로그인학생 화면에서 보이는 것

- **AI 튜터** (채팅)
- **문제 채점기** (이미지 업로드 → 채점)

대시보드(할 일, 취약점 등), 내 숙제, 오답노트, 기록 탭은 **나오지 않습니다.**

---

## 5. admin 쪽 (전체 MVP) 배포

- **admin.studyt2c.streamlit.app** 등 다른 앱에서는 `STUDENT_LOGIN_APP` 을 **설정하지 않거나** `false` 로 두면,  
  기존처럼 사이드바 계정 선택 후 학생/학부모/선생 전체 화면이 나옵니다.
