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

def render(user):
    st.title("🎓 AI 학습 집중 대시보드")
    st.caption(f"환영합니다, {user['name']} 학생! (현재 모드: {user.get('status', 'break')})")
    
    if "messages" not in st.session_state: st.session_state.messages = []
    if "practice_q" not in st.session_state: st.session_state.practice_q = {}
    if "graded_items" not in st.session_state: st.session_state.graded_items = []

    # 기획서 반영: 대시보드 탭과 오답노트 탭 분리
    tab_dash, tab_note = st.tabs(["📊 학습 대시보드", "📝 나의 오답노트"])

    with tab_dash:
        col_left, col_center, col_right = st.columns([1, 2, 1])

        with col_left:
            st.subheader("📊 내 학습 현황")
            status_data = get_student_learning_status(user['id'])
            st.info(f"🚨 오늘의 복습: **{status_data['review_count']}개**")
            
            # 기획서 반영: 과목별 질문수 차트
            if status_data.get('subject_counts'):
                st.write("📈 **과목별 질문 비율**")
                chart_data = pd.DataFrame(list(status_data['subject_counts'].items()), columns=['과목', '질문수']).set_index('과목')
                st.bar_chart(chart_data)

            st.write("---")
            st.write("📌 **집중 공략 개념**")
            for concept in status_data.get('bookmarked_concepts', []): st.button(f"🔖 {concept}", use_container_width=True)

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
                        # 기획서 반영: 과목 자동 분류
                        subj_class = classify_subject(u_input)
                        ans = chat_with_tutor(u_input, mode=user['status'])
                        st.markdown(ans)
                        st.caption(f"분류된 과목: {subj_class.get('subject', 'OTHER')}")
                st.session_state.messages.append({"role": "assistant", "content": ans})
                save_chat_message(user['id'], user['status'], subj_class.get('subject', 'OTHER'), u_input, ans)

        with col_right:
            st.subheader("📸 문제 채점기")
            uploaded_file = st.file_uploader("이미지/PDF 업로드", type=["png", "jpg", "jpeg", "heic", "pdf"])
            if uploaded_file:
                try:
                    f_bytes = uploaded_file.getvalue()
                    norm_bytes, n_name = normalize_upload(f_bytes, uploaded_file.name)
                    st.image(norm_bytes, use_container_width=True)
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
                            
                            if not is_corr:
                                q_key = f"p_{item['id']}"
                                if st.button("✨ 유사 문제", key=f"b_{item['id']}"):
                                    p_data = generate_practice_question(item.get('key_concepts', []))
                                    if p_data:
                                        db_item = save_practice_item(item['id'], user['id'], p_data['question'], p_data['answer_key'], item.get('key_concepts', []))
                                        p_data['db_id'] = db_item['id']; st.session_state.practice_q[q_key] = p_data
                                
                                if q_key in st.session_state.practice_q:
                                    q_d = st.session_state.practice_q[q_key]
                                    st.info(f"**Q.**\n{q_d.get('question', '')}")
                                    s_ans = st.text_input("정답(숫자)", key=f"i_{q_key}")
                                    if st.button("제출", key=f"s_{q_key}"):
                                        is_r = (s_ans.strip() == str(q_d.get('answer_key')))
                                        update_practice_result(q_d['db_id'], s_ans, is_r, user['id'], item['id'])
                                        if is_r: st.success("정답!"); del st.session_state.practice_q[q_key]
                                        else: st.error("오답!")
                except Exception as e: st.error(f"오류: {e}")

    # 기획서 반영: 오답노트 전용 탭
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