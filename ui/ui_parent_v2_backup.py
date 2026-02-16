import streamlit as st
import time
import pandas as pd
from services.analytics_service import get_student_stats
from services.llm_service import generate_parent_report
from services.supabase_client import supabase
from services.db_service import log_audit

def render(parent_user):
    st.title("👨‍👩‍👧 학부모 관리 대시보드")
    students = supabase.table("users").select("*").eq("role", "student").execute().data
    if not students: return st.warning("학생 없음")
    
    sel_name = st.selectbox("학생 선택", [s['name'] for s in students])
    student = next(s for s in students if s['name'] == sel_name)
    stats = get_student_stats(student['id'])
    
    col_l, col_r = st.columns([2, 1])
    
    with col_l:
        st.subheader("📊 핵심 KPI 지표")
        m1, m2, m3 = st.columns(3)
        m1.metric("질문 횟수", f"{stats['chat_count']}회")
        m2.metric("오답 문항", f"{stats['total_wrong']}개")
        # 기획서 반영: 정답률 지표 (임시 계산식 적용)
        acc = max(0, 100 - (stats['total_wrong'] * 2)) 
        m3.metric("최근 정답률 추정", f"{acc}%")
        
        # 기획서 반영: 실데이터 모의 라인 차트 추이
        st.write("📈 **주간 학습 참여도 추이**")
        trend_data = pd.DataFrame({"일자": ["월", "화", "수", "목", "금"], "참여도": [2, 5, 3, 7, stats['chat_count']]}).set_index("일자")
        st.line_chart(trend_data)

        # 기획서 반영: 시스템 Alerts 리스트
        st.subheader("🚨 시스템 자동 알림 (Alerts)")
        if stats.get('alerts'):
            for alert in stats['alerts']: st.error(alert)
        else:
            st.success("정상적으로 학습을 진행 중입니다.")
            
        st.divider()
        if st.button("🤖 AI 리포트 생성"):
            with st.spinner("데이터 분석 중..."):
                report = generate_parent_report(student['name'], stats)
                st.write(report)

    with col_r:
        st.subheader("⚙️ 권한 제어 및 감사(Audit)")
        p_toggle = st.toggle("상세해설 허용", value=student.get("detail_permission", False))
        a_toggle = st.toggle("유사문제 정답표기", value=student.get("show_practice_answer", False))
        s_mode = st.radio("모드", ["studying", "break"], index=0 if student.get("status")=="studying" else 1)
        
        if st.button("설정 저장"):
            # 기획서 반영: 부모의 조작을 감사 로그(audit_logs)에 기록
            log_audit(parent_user['id'], student['id'], "UPDATE_PERMISSIONS", 
                      f"Mode:{student.get('status')}, Detail:{student.get('detail_permission')}", 
                      f"Mode:{s_mode}, Detail:{p_toggle}")
            
            supabase.table("users").update({"detail_permission": p_toggle, "show_practice_answer": a_toggle, "status": s_mode}).eq("id", student['id']).execute()
            st.success("저장 완료!"); time.sleep(0.5); st.rerun()