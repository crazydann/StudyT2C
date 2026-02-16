import streamlit as st
from shared_summary import render_shared_summary

def render(supabase, user):
    st.title(f"🧑‍🏫 Teacher Console - {user['handle']}")
    
    # 담당 학생 목록 가져오기 (권한 필터링)
    resp = supabase.table("teacher_student_links").select("student_user_id, users!teacher_student_links_student_user_id_fkey(handle)").eq("teacher_user_id", user['id']).execute()
    students = resp.data
    
    if not students:
        return st.warning("담당 학생이 없습니다.")

    if "t_sel_student" not in st.session_state:
        st.session_state.t_sel_student = None

    if st.session_state.t_sel_student is None:
        st.subheader("📋 담당 학생 목록")
        cols = st.columns(3)
        for idx, s in enumerate(students):
            sid = s['student_user_id']
            shandle = s['users']['handle']
            with cols[idx % 3]:
                with st.container(border=True):
                    st.markdown(f"### 🎓 {shandle}")
                    if st.button("상담 페이지 열기", key=f"open_{sid}"):
                        st.session_state.t_sel_student = {"id": sid, "handle": shandle}
                        st.rerun()
    else:
        sid = st.session_state.t_sel_student["id"]
        shandle = st.session_state.t_sel_student["handle"]
        
        if st.button("🔙 목록으로"):
            st.session_state.t_sel_student = None
            st.rerun()
            
        # Shared Summary 렌더링
        render_shared_summary(supabase, sid, shandle, "teacher", user['id'])
        
        # 숙제 배정 기능 (MVP v2.5 핵심 기능 중 하나)
        st.divider()
        st.subheader("➕ 새 숙제 배정")
        with st.form("new_hw"):
            title = st.text_input("숙제 제목")
            desc = st.text_area("설명")
            if st.form_submit_button("배정하기"):
                supabase.table("homework_assignments").insert({
                    "teacher_user_id": user['id'], "student_user_id": sid, "title": title, "description": desc
                }).execute()
                st.success("숙제가 배정되었습니다!")
                st.rerun()