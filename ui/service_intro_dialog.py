# ui/service_intro_dialog.py
"""서비스 소개 팝업(비밀번호 보호) 및 콘텐츠."""

import streamlit as st

SERVICE_INTRO_PASSWORD = "dannyho"

SERVICE_INTRO_MD = r"""
# StudyT2C — 오프라인 수업을 위한 개인화 보조 OS

## 우리가 해결하려는 문제 (본질)
온라인 학습 솔루션은 기능적으로 훨씬 강력한 것들이 많습니다.  
하지만 많은 학원 현장에서는 그 솔루션들이 **오프라인 수업과 자연스럽게 이어지지 않아서**, 결국 "수업의 중심"이 되기 어렵습니다.

학원은 여전히 오프라인 수업을 핵심으로 운영합니다.  
그럼에도 오프라인 수업은 구조적으로 **학생별 개인화**가 어렵습니다.

- 같은 반에서 같은 내용을 배우더라도 학생마다 강점/취약점이 다르고,
- 숙제/복습 과정에서 그 차이가 가장 크게 드러나지만,
- 그 데이터가 수업 설계로 연결되기 전에 **사람 손에서 소실**되거나 **정리 부담** 때문에 활용되지 못합니다.

**StudyT2C의 본질은 "온라인 학습을 대체"하는 것이 아니라,  
기존 오프라인 수업을 지지하고 강화하면서, 오프라인 수업의 개인화를 극대화하는 것**입니다.

---

## StudyT2C의 한 문장 정의
StudyT2C는 **학원 관리 프로그램이 아니라**,  
오프라인 수업을 유지한 채 **숙제·복습 데이터를 기반으로 학생별 강점/취약점을 구조화**하고,  
그 결과가 **다음 오프라인 수업의 맞춤 보강/지도**로 이어지게 만드는 **개인화 보조 솔루션(OS)** 입니다.

---

## 우리가 만드는 변화 (전/후)
### Before: 개인화가 '의지'에 의존
- 숙제/복습에서 학생의 약점이 보이지만 정리/기록이 어렵다
- 선생님은 "감"과 "기억"으로 보강을 결정한다
- 학부모는 "우리 아이가 어떻게 변하고 있는지"를 체감하기 어렵다
- 결국 개인화는 일부 선생님의 역량/시간에 좌우된다

### After: 개인화가 '시스템'이 됨
- 숙제/복습 과정에서 학생의 패턴이 자동으로 구조화된다
- 그 결과가 다음 수업의 **맞춤 보강 포인트/지도 방식**으로 연결된다
- 학부모는 시간에 따른 성취도/성향을 리포트로 확인한다
- 학원은 데이터 기반으로 학생 성취도를 끌어올리고 신뢰를 강화한다

---

## 핵심 가치 (기능보다 본질)
### 1) 오프라인 수업을 중심에 둔다
StudyT2C는 "수업을 온라인으로 옮기자"가 아니라,  
**오프라인 수업을 그대로 진행하면서 그 수업이 더 개인화되게 돕는 보조 솔루션**입니다.

### 2) 개인화의 근거는 '숙제/복습 데이터'다
학생의 실제 실력은 수업보다 **숙제/복습**에서 더 정확히 드러납니다.  
StudyT2C는 이 과정에서 나타나는
- 강점/취약점,
- 실수 유형,
- 개념의 빈틈,
- 시간에 따른 변화(추이)
를 구조화해 **개인화 수업의 근거 데이터**로 만듭니다.

### 3) 결과는 "다음 수업에서의 행동"으로 귀결된다
우리가 제공하는 것은 단순 진단이 아니라,  
선생님이 다음 수업에서 바로 적용할 수 있는
- 보강해야 할 개념/유형,
- 지도 우선순위,
- 맞춤 과제/복습 제안
같은 **"실행 가능한 개인화"**입니다.

---

## 이해관계자별 가치
### 학원(원장/실장)
- "수업 품질"을 개인화로 강화 → 학원 경쟁력/평판 상승
- 학부모 신뢰도 상승 → 재등록/상담 설득력 강화
- 선생님 역량 편차를 줄이고, 운영을 표준화

### 선생님
- 학생별 취약점을 '기억'이 아니라 '근거'로 관리
- 다음 수업 준비가 더 빨라지고, 보강이 더 정확해짐
- 개인화가 늘어나도 번아웃이 덜해짐(정리/보고 부담 감소)

### 학부모
- 우리 아이의 학습 성향/평가/성취도 추이를 한눈에 확인
- "어떤 점이 좋아지고, 어떤 점이 막혀 있는지"가 투명해짐
- 학원 수업이 우리 아이에게 맞게 조정되고 있다는 확신 획득

---

## 타깃 (GTM: B2B 학원 중심)
- **1차 고객(결제자):** 원생 30~199명 규모 동네 보습~중간 규모 수학/과학 학원
- **1차 사용자:** 선생님(개인화 보강)
- **2차 가치 체감:** 학부모(신뢰 리포트)

> 학부모 리포트는 B2C 구독이 아니라, **학원이 오프라인 수업 품질을 증명하는 도구**로 설계합니다.

---

## MVP는 '본질을 증명'하는 최소 흐름만
MVP의 목표는 "기능이 많음"이 아니라,  
**숙제/복습 데이터 → 개인화 인사이트 → 오프라인 수업 보강**이 실제로 연결되는 것을 증명하는 것입니다.

- 학생: 숙제/복습 제출(사진/PDF) + 질문
- 시스템: 오답/취약 패턴 구조화
- 선생님: 다음 수업 맞춤 보강 포인트
- 학부모: 주간 성취/추이 리포트

---

## 실행 계획 (Next Steps)
- 원생 30~199명 학원 3곳 파일럿
- 각 학원 1~2개 반(30~60명)으로 4주 운영
- 검증 지표:
  - 선생님 수업 준비 시간 변화(전/후)
  - 학부모 리포트 열람률/반응
  - 학원 재등록/상담에서의 리포트 활용도

---

## 연락 / 파일럿 문의
- (연락처/이메일/오픈채팅)
- 현재 상태: MVP 구현 단계(본질 흐름을 먼저 증명 중)
"""


def _render_service_intro_content():
    """서비스 소개 본문을 프레임·스크롤 가능한 영역으로 렌더."""
    with st.container(border=True):
        st.markdown(SERVICE_INTRO_MD)


@st.dialog("서비스 소개", width="large")
def show_service_intro_dialog():
    """비밀번호 확인 후 서비스 소개 본문 표시."""
    authenticated = st.session_state.get("service_intro_authenticated", False)

    if not authenticated:
        st.caption("서비스 소개를 보려면 암호를 입력하세요.")
        pwd = st.text_input("암호", type="password", key="service_intro_pwd", label_visibility="collapsed", placeholder="암호 입력")
        col1, col2, _ = st.columns([1, 1, 2])
        with col1:
            if st.button("확인", key="service_intro_confirm", type="primary"):
                if (pwd or "").strip() == SERVICE_INTRO_PASSWORD:
                    st.session_state["service_intro_authenticated"] = True
                    st.rerun()
                else:
                    st.error("암호가 올바르지 않습니다.")
        return

    _render_service_intro_content()
    st.markdown("---")
    if st.button("닫기", key="service_intro_close", use_container_width=True):
        st.session_state.pop("open_service_intro_dialog", None)
        st.session_state.pop("service_intro_authenticated", None)
        st.rerun()


def render_service_intro_button_sidebar():
    """사이드바 StudyT2C 옆에 쓸 '서비스 소개' 버튼(파란색 강조)."""
    if st.sidebar.button(
        "서비스 소개",
        key="sidebar_service_intro_btn",
        use_container_width=True,
        type="primary",
    ):
        st.session_state["open_service_intro_dialog"] = True
        st.rerun()


def render_service_intro_button_inline():
    """상단 바(로고 옆)에 쓸 '서비스 소개' 링크/버튼. 컨테이너 내에서 호출."""
    if st.button("서비스 소개", key="topbar_service_intro_btn", type="primary"):
        st.session_state["open_service_intro_dialog"] = True
        st.rerun()


def maybe_show_service_intro_dialog():
    """session_state에 따라 서비스 소개 다이얼로그 열기. main() 등에서 호출."""
    if st.session_state.get("open_service_intro_dialog"):
        show_service_intro_dialog()
