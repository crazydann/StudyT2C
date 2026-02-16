import hashlib
import streamlit as st
import pandas as pd
from services.llm_service import chat_with_tutor, generate_practice_question, classify_subject
from services.storage_service import upload_problem_image 
from utils.image_utils import normalize_upload
from services.vision_grading import grade_image_to_items
from services.db_service import *
from services.analytics_service import get_student_learning_status
from services.review_service import get_today_reviews, record_review_attempt

def render(supabase, user):
    st.title("🎓 AI 학습 집중 대시보드")
    st.caption(f"환영합니다, {user['handle']} 학생! (현재 모드: {user.get('status', 'break')})")
    
    if "messages" not in st.session_state: st.session_state.messages = []
    if "practice_q" not in st.session_state: st.session_state.practice_q = {}
    if "graded_items" not in st.session_state: st.session_state.graded_items = []

    # 3개의 탭으로 확장 구성
    tab_dash, tab_note, tab_hw = st.tabs(["📊 학습 대시보드", "📝 나의 오답노트", "📚 내 숙제"])

    # ----------------------------------------------------
    # 탭 1: 기존 학습 대시보드 (AI튜터, 문제채점기 등)
    # ----------------------------------------------------
    with tab_dash:
        col_left, col_center, col_right = st.columns([1, 2, 1])
        
        with col_left:
            st.subheader("📊 내 학습 현황")
            status_data = get_student_learning_status(user['id'])
            st.info(f"🚨 오늘의 복습: **{status_data['review_count']}개**")
            
            if status_data.get('subject_counts'):
                st.write("📈 **과목별 질문 비율**")
                chart_data = pd.DataFrame(list(status_data['subject_counts'].items()), columns=['과목', '질문수']).set_index('과목')
                st.bar_chart(chart_data)

            st.write("---")
            st.subheader("🎯 오늘의 복습 큐")
            for item in get_today_reviews(user['id']):
                with st.expander(f"복습: {item.get('extracted_question_text', '문제')[:10]}..."):
                    st.write(item.get('explanation_summary'))
                    c1, c2 = st.columns(2)
                    if c1.button("✅ 맞춤", key=f"r_o_{item['id']}"): record_review_attempt(user['id'], item['id'], True); st.rerun()
                    if c2.button("❌ 또 틀림", key=f"r_x_{item['id']}"): record_review_attempt(user['id'], item['id'], False); st.rerun()

        with col_center:
            st.subheader("💬 AI 튜터")
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]): st.markdown(msg["content"])
            
            u_input = st.chat_input("질문하세요")
            if u_input:
                st.session_state.messages.append({"role": "user", "content": u_input})
                with st.chat_message("user"): st.markdown(u_input)
                with st.chat_message("assistant"):
                    with st.spinner("생각 중..."):
                        subj_class = classify_subject(u_input)
                        
                        current_status = user.get('status', 'studying')
                        ans = chat_with_tutor(u_input, mode=current_status)
                        
                        st.markdown(ans)
                        st.caption(f"분류된 과목: {subj_class.get('subject', 'OTHER')}")
                st.session_state.messages.append({"role": "assistant", "content": ans})
                save_chat_message(user['id'], current_status, subj_class.get('subject', 'OTHER'), u_input, ans)

        with col_right:
            st.subheader("📸 문제 채점기")
            uploaded_file = st.file_uploader("이미지/PDF 업로드", type=["png", "jpg", "jpeg", "heic", "pdf"])
            if uploaded_file:
                try:
                    f_bytes = uploaded_file.getvalue()
                    norm_bytes, n_name = normalize_upload(f_bytes, uploaded_file.name)
                    st.image(norm_bytes, use_column_width=True)
                    if st.button("AI 채점 요청"):
                        f_hash = hashlib.sha256(norm_bytes).hexdigest()
                        cached = check_cached_submission(user['id'], f_hash)
                        if cached: st.session_state.graded_items = cached; st.success("⚡ 캐시 로드 완료")
                        else:
                            with st.spinner("AI 분석 중..."):
                                url = upload_problem_image(user['id'], norm_bytes, n_name)
                                st.session_state.graded_items = save_grading_results(user['id'], url, norm_bytes, grade_image_to_items(url))
                    
                    for item in st.session_state.graded_items:
                        is_corr = item.get("is_correct")
                        with st.expander(f"{item.get('item_no',0)}번 ({'🟢' if is_corr else '🔴'})", expanded=not is_corr):
                            st.write(item.get('explanation_summary'))
                            if user.get('detail_permission'): st.info(f"**상세:** {item.get('explanation_detail')}")
                except Exception as e: st.error(f"오류: {e}")

    # ----------------------------------------------------
    # 탭 2: 오답노트
    # ----------------------------------------------------
    with tab_note:
        st.subheader("📚 나의 전체 오답노트")
        wrong_records = supabase.table("problem_items").select("*").eq("student_user_id", user['id']).eq("is_correct", False).execute().data
        if wrong_records:
            for rec in wrong_records:
                with st.container(border=True):
                    st.markdown(f"**문제:** {rec.get('extracted_question_text')}")
                    st.caption(f"개념: {', '.join(rec.get('key_concepts', []))} | 다음 복습일: {rec.get('next_review_at', '')[:10]}")
                    if user.get('detail_permission'): st.info(rec.get('explanation_detail'))
        else:
            st.success("아직 틀린 문제가 없습니다!")

    # ----------------------------------------------------
    # 탭 3: 내 숙제 (신규 워크플로우)
    # ----------------------------------------------------
    with tab_hw:
        st.subheader("해야 할 숙제")
        resp = supabase.table("homework_assignments").select("*").eq("student_user_id", user['id']).order("created_at", desc=True).execute()
        
        if not resp.data:
            st.info("현재 배정된 숙제가 없습니다.")
        else:
            for hw in resp.data:
                with st.expander(f"📌 {hw['title']}"):
                    st.write(hw['description'])
                    
                    sub_resp = supabase.table("homework_submissions").select("*").eq("assignment_id", hw['id']).execute()
                    if sub_resp.data:
                        st.success("✅ 제출 완료!")
                        
                        # [추가됨 1] 제출한 내 숙제 사진 보여주기
                        storage_path = sub_resp.data[0].get("storage_path", "")
                        if storage_path.startswith("http"):
                            st.image(storage_path, width=300)
                            
                        # [추가됨 2] 선생님 코멘트 보여주기
                        fb_resp = supabase.table("homework_feedback").select("comment_one_liner").eq("submission_id", sub_resp.data[0]['id']).execute()
                        if fb_resp.data:
                            st.info(f"👨‍🏫 선생님 코멘트: {fb_resp.data[0]['comment_one_liner']}")

                    else:
                        st.warning("제출이 필요합니다.")
                        uploaded = st.file_uploader("숙제 사진 업로드", type=['jpg', 'png'], key=f"up_{hw['id']}")
                        if st.button("제출하기", key=f"btn_{hw['id']}"):
                            if uploaded:
                                with st.spinner("숙제 업로드 중..."):
                                    try:
                                        # [수정됨] 문제 채점용 업로드 함수를 재사용해서 진짜 URL(사진)을 클라우드에 저장!
                                        url = upload_problem_image(user['id'], uploaded.getvalue(), uploaded.name)
                                        supabase.table("homework_submissions").insert({
                                            "assignment_id": hw['id'], "student_user_id": user['id'], "storage_path": url
                                        }).execute()
                                        st.success("숙제가 제출되었습니다! (잠시 후 새로고침됩니다)")
                                        time.sleep(1)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"업로드 실패: {e}")
                            else:
                                st.error("파일을 업로드해주세요.")
