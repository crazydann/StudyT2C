import streamlit as st
import pandas as pd
from datetime import date
import time

def render_shared_summary(supabase, student_id, student_handle, viewer_role, viewer_id):
    st.subheader(f"📊 {student_handle} 학생 종합 리포트")
    
    # 1) 핵심 지표 요약 (Mockup Data)
    st.markdown("##### 📌 주간 학습 요약")
    c1, c2, c3 = st.columns(3)
    c1.metric("이번 주 숙제 진행률", "66%", "1건 미제출 (목표: 3건)")
    c2.metric("복습 큐 소화율", "85%", "오늘 10문제 남음")
    c3.metric("최근 정답률 추이", "72%", "-3% 하락")
    
    st.error("🚨 취약 개념 Top 1: **이차방정식의 근의 공식** (대표 오답 링크)")
    st.info("🤖 AI 코멘트: 개념 적용은 잘하나 계산 실수가 반복됩니다. 오답 노트 복습이 필요합니다.")
    st.divider()

    # 2) Teacher Notes & Weekly Plan
    st.markdown("##### 📝 상담 기록 및 주간 계획")
    
    # DB에서 가장 최근 노트 및 플랜 가져오기
    note_resp = supabase.table("teacher_notes").select("note_text").eq("student_user_id", student_id).order("created_at", desc=True).limit(1).execute()
    plan_resp = supabase.table("weekly_plans").select("plan_text").eq("student_user_id", student_id).order("created_at", desc=True).limit(1).execute()
    
    current_note = note_resp.data[0]['note_text'] if note_resp.data else ""
    current_plan = plan_resp.data[0]['plan_text'] if plan_resp.data else ""

    if viewer_role == "teacher":
        # 선생님 뷰: 편집 및 저장 가능
        with st.form(key=f"plan_form_{student_id}"):
            new_note = st.text_area("Teacher Notes (상담 메모)", value=current_note, height=100)
            new_plan = st.text_area("Weekly Plan (다음 주 계획 - 7줄 권장)", value=current_plan, height=150)
            
            if st.form_submit_button("저장/업데이트"):
                try:
                    today_str = date.today().isoformat() # 오늘 날짜 자동 생성
                    
                    # Notes 저장
                    supabase.table("teacher_notes").insert({
                        "teacher_user_id": viewer_id, 
                        "student_user_id": student_id, 
                        "note_text": new_note
                    }).execute()
                    
                    # Plan 저장
                    supabase.table("weekly_plans").insert({
                        "teacher_user_id": viewer_id, 
                        "student_user_id": student_id, 
                        "week_start_date": today_str, 
                        "plan_text": new_plan, 
                        "status": "final"
                    }).execute()
                    
                    st.success("✅ 성공적으로 저장되었습니다! (잠시 후 새로고침됩니다)")
                    time.sleep(0.8) # 성공 메시지를 사용자가 읽을 수 있도록 0.8초 대기
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"저장 중 오류가 발생했습니다: {e}")
                
    elif viewer_role == "parent":
        # 학부모 뷰: 읽기 전용
        st.text_area("Teacher Notes", value=current_note, height=100, disabled=True)
        st.text_area("Weekly Plan (Final)", value=current_plan, height=150, disabled=True)

    st.divider()
    
    # 3) Homework Workflow 요약
    st.markdown("##### 📚 최근 숙제 현황")
    hw_resp = supabase.table("homework_assignments").select("id, title, due_at").eq("student_user_id", student_id).order("created_at", desc=True).limit(3).execute()
    
    if not hw_resp.data:
        st.write("배정된 숙제가 없습니다.")
    else:
        for hw in hw_resp.data:
            with st.expander(f"📌 숙제: {hw['title']} (마감: {hw['due_at'][:10] if hw['due_at'] else '없음'})"):
                # [수정됨] 사진 URL(storage_path)도 함께 가져오기
                sub_resp = supabase.table("homework_submissions").select("id, status, storage_path").eq("assignment_id", hw['id']).execute()
                
                if sub_resp.data:
                    st.success("✅ 제출 완료")
                    
                    # [추가됨] 학생이 제출한 사진 화면에 띄워주기
                    storage_path = sub_resp.data[0].get("storage_path", "")
                    if storage_path.startswith("http"):
                        st.image(storage_path, width=400)
                    elif storage_path:
                        st.caption("(텍스트로만 제출된 이전 테스트 데이터입니다.)")

                    # 코멘트 로드
                    fb_resp = supabase.table("homework_feedback").select("comment_one_liner").eq("submission_id", sub_resp.data[0]['id']).execute()
                    if fb_resp.data:
                        st.info(f"👨‍🏫 선생님 코멘트: {fb_resp.data[0]['comment_one_liner']}")
                    elif viewer_role == "teacher":
                        with st.form(key=f"fb_{hw['id']}"):
                            fb = st.text_input("1줄 코멘트 작성")
                            if st.form_submit_button("남기기"):
                                supabase.table("homework_feedback").insert({"submission_id": sub_resp.data[0]['id'], "teacher_user_id": viewer_id, "comment_one_liner": fb}).execute()
                                st.rerun()
                else:
                    st.warning("⏳ 미제출 상태입니다.")
