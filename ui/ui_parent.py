import streamlit as st
import time
import pandas as pd
from services.analytics_service import get_student_stats
from services.llm_service import generate_parent_report
from services.db_service import log_audit
from shared_summary import render_shared_summary

def render(supabase, user):
    st.title(f"👨‍👩‍👧 학부모 대시보드 - {user['handle']}")
    
    # 1) 연결된 자녀 목록만 가져오기 (권한 필터링)
    resp = supabase.table("parent_student_links").select("student_user_id, users!parent_student_links_student_user_id_fkey(handle)").eq("parent_user_id", user['id']).execute()
    children = resp.data
    
    if not children:
        return st.warning("연결된 자녀가 없습니다.")
        
    child_options = {c['users']['handle']: c['student_user_id'] for c in children}
    sel_handle = st.selectbox("자녀 선택", options=list(child_options.keys()))
    sel_id = child_options[sel_handle]
    
    # 자녀의 상세 정보(기존 로직 호환용)를 users 테이블에서 가져오기
    student_resp = supabase.table("users").select("*").eq("id", sel_id).execute()
    student = student_resp.data[0] if student_resp.data else None
    
    # 2) 탭 분리: 상담 요약 리포트 vs 상세 통계 및 설정
    tab1, tab2 = st.tabs(["📊 상담 요약 리포트 (Shared)", "⚙️ 설정 및 상세 통계"])
    
    with tab1:
        # 선생님과 동일한 Shared Summary 렌더링 (읽기 전용 모드)
        render_shared_summary(supabase, sel_id, sel_handle, "parent", user['id'])
        
    with tab2:
        if not student:
            st.error("학생 상세 정보를 불러올 수 없습니다.")
            return

        stats = get_student_stats(student['id'])
        col_l, col_r = st.columns([2, 1])
        
        with col_l:
            st.subheader("📊 핵심 KPI 지표")
            m1, m2, m3 = st.columns(3)
            m1.metric("질문 횟수", f"{stats['chat_count']}회")
            m2.metric("오답 문항", f"{stats['total_wrong']}개")
            acc = max(0, 100 - (stats['total_wrong'] * 2)) 
            m3.metric("최근 정답률 추정", f"{acc}%")
            
            st.write("📈 **주간 학습 참여도 추이**")
            trend_data = pd.DataFrame({"일자": ["월", "화", "수", "목", "금"], "참여도": [2, 5, 3, 7, stats['chat_count']]}).set_index("일자")
            st.line_chart(trend_data)

            st.subheader("🚨 시스템 자동 알림 (Alerts)")
            if stats.get('alerts'):
                for alert in stats['alerts']: st.error(alert)
            else:
                st.success("정상적으로 학습을 진행 중입니다.")
                
            st.divider()
            if st.button("🤖 AI 리포트 생성"):
                with st.spinner("데이터 분석 중..."):
                    report = generate_parent_report(sel_handle, stats)
                    st.write(report)

        with col_r:
            st.subheader("⚙️ 권한 제어 및 감사(Audit)")
            p_toggle = st.toggle("상세해설 허용", value=student.get("detail_permission", False))
            a_toggle = st.toggle("유사문제 정답표기", value=student.get("show_practice_answer", False))
            s_mode = st.radio("모드", ["studying", "break"], index=0 if student.get("status")=="studying" else 1)
            
            if st.button("설정 저장"):
                log_audit(user['id'], student['id'], "UPDATE_PERMISSIONS", 
                          f"Mode:{student.get('status')}, Detail:{student.get('detail_permission')}", 
                          f"Mode:{s_mode}, Detail:{p_toggle}")
                supabase.table("users").update({"detail_permission": p_toggle, "show_practice_answer": a_toggle, "status": s_mode}).eq("id", student['id']).execute()
                st.success("저장 완료!"); time.sleep(0.5); st.rerun()