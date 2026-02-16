import pandas as pd
from services.supabase_client import supabase

def get_student_learning_status(student_id: str) -> dict:
    chat_data = supabase.table("chat_messages").select("subject").eq("student_user_id", student_id).execute().data
    review_res = supabase.table("problem_items").select("id", count="exact").eq("student_user_id", student_id).lte("next_review_at", "now()").execute()
    wrong_items = supabase.table("problem_items").select("key_concepts").eq("student_user_id", student_id).eq("is_correct", False).execute().data
    
    # 과목별 질문 수 집계 (바 차트용)
    subject_counts = {}
    if chat_data:
        df = pd.DataFrame(chat_data)
        if not df.empty and 'subject' in df.columns:
            subject_counts = df['subject'].value_counts().to_dict()
            
    concepts = list(set([c for item in wrong_items for c in item.get('key_concepts', [])]))
    
    return {
        "chat_count": len(chat_data) if chat_data else 0,
        "subject_counts": subject_counts,
        "review_count": review_res.count if review_res.count else 0,
        "bookmarked_concepts": concepts[:5]
    }

def get_student_stats(student_id: str) -> dict:
    status = get_student_learning_status(student_id)
    wrong_res = supabase.table("problem_items").select("id", count="exact").eq("student_user_id", student_id).eq("is_correct", False).execute()
    
    # 시스템 경고(Alert) 생성 로직
    alerts = []
    if status['chat_count'] == 0: alerts.append("⚠️ 최근 3일간 AI 튜터 질문 이력이 없습니다. (학습 독려 필요)")
    if len(status['bookmarked_concepts']) > 3: alerts.append("⚠️ 특정 개념에서 반복적인 오답이 발생하고 있습니다.")
    
    return {
        "chat_count": status['chat_count'], 
        "total_wrong": wrong_res.count if wrong_res.count else 0, 
        "top_weak_concepts": status['bookmarked_concepts'],
        "alerts": alerts
    }