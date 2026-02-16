from datetime import datetime, timedelta
from services.supabase_client import supabase

def record_review_attempt(student_id, problem_item_id, is_correct):
    next_days = 3 if is_correct else 1
    next_review = (datetime.utcnow() + timedelta(days=next_days)).isoformat()
    supabase.table("problem_items").update({"next_review_at": next_review}).eq("id", problem_item_id).execute()
    supabase.table("attempts").insert({"student_user_id": student_id, "problem_item_id": problem_item_id, "is_correct": is_correct, "attempt_type": "review"}).execute()

def get_today_reviews(student_id):
    now = datetime.utcnow().isoformat()
    return supabase.table("problem_items").select("*").eq("student_user_id", student_id).lte("next_review_at", now).execute().data