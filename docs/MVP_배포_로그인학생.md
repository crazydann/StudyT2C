# MVP 테스트 배포: 로그인학생 화면 (studyt2c.streamlit.app)

## 개요

- **studyt2c.streamlit.app**  
  로그인 화면 → 로그인한 학생만 **문제 채점기** + **AI 튜터** 사용 (로그인학생 화면).
- **admin.studyt2c.streamlit.app** (또는 별도 앱)  
  기존처럼 계정 선택 후 학생/학부모/선생 전체 화면.

**같은 배포(같은 앱)를 쓰는 경우**  
studyt2c와 admin이 한 앱을 가리키면, **URL 쿼리**로 구분합니다.

- 로그인 화면: **https://studyt2c.streamlit.app/?app=student**  
  (또는 `?student=1` — 한 번 들어가면 세션 동안 로그인 모드 유지)
- 계정 선택(admin) 화면: **https://studyt2c.streamlit.app/** (쿼리 없음) 또는 **?app=admin**

---

## 1. 로그인 화면이 나오게 하는 방법 (둘 중 하나)

### 방법 A: 같은 앱을 쓸 때 (studyt2c = admin 한 배포)

**로그인 화면**이 나오는 주소로 들어가세요.

- **https://studyt2c.streamlit.app/?app=student**  
  또는 **https://studyt2c.streamlit.app/?student=1**

한 번 이 주소로 들어가면, 같은 세션 동안은 로그인 모드가 유지됩니다.  
계정 선택(admin) 화면은 쿼리 없이 **https://studyt2c.streamlit.app/** 또는 **?app=admin** 으로 들어가면 됩니다.

### 방법 B: 배포를 두 개 쓸 때 (studyt2c / admin 각각 다른 앱)

Streamlit Cloud에서 **studyt2c** 앱의 **Settings → Secrets** 에만:

| 변수 | 값 |
|------|-----|
| `STUDENT_LOGIN_APP` | `true` |

이렇게 두면, 그 앱(studyt2c.streamlit.app)은 쿼리 없이 접속해도 로그인 화면이 나옵니다.

---

## 2. DB: password_hash + david/joshua 비밀번호

Supabase **SQL Editor**에서 **한 번** 실행해 주세요.

- 파일: `supabase/migrations/users_password_hash_mvp.sql`  
- 하는 일:  
  - `users` 테이블에 `password_hash` 컬럼 추가  
  - **david**, **joshua** 계정이 있으면 비밀번호(아이디와 동일) 해시로 갱신  
  - 없으면 두 계정 생성 후 비밀번호 설정  

이 SQL을 실행해야 **david / david**, **joshua / joshua** 로그인이 됩니다.  
(Streamlit Cloud에 `SUPABASE_SERVICE_ROLE_KEY`가 없어도 이 SQL만 실행하면 로그인 가능)

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
