import hashlib
from datetime import datetime, timedelta
from services.supabase_client import supabase

def save_chat_message(student_id, mode, subject, question, answer):
    try: supabase.table("chat_messages").insert({"student_user_id": student_id, "subject": subject, "question": question, "answer": answer, "mode": mode}).execute()
    except: pass

def toggle_bookmark(message_id, is_bookmarked):
    supabase.table("chat_messages").update({"is_bookmarked": is_bookmarked}).eq("id", message_id).execute()

def log_audit(actor_id, target_id, action, old_val, new_val):
    supabase.table("audit_logs").insert({"actor_user_id": actor_id, "target_student_user_id": target_id, "action": action, "old_value": str(old_val), "new_value": str(new_val)}).execute()

def save_grading_results(student_id, file_path, file_bytes, items):
    file_hash = hashlib.sha256(file_bytes).hexdigest()
    sub_res = supabase.table("problem_submissions").insert({"student_user_id": student_id, "file_hash": file_hash, "storage_path": file_path}).execute()
    sub_id = sub_res.data[0]["id"]
    next_review = (datetime.utcnow() + timedelta(days=1)).isoformat()
    
    records, attempt_records = [], []
    for item in items:
        records.append({
            "submission_id": sub_id, "student_user_id": student_id, "item_no": item.get("item_no"),
            "extracted_question_text": item.get("question_text"), "is_correct": item.get("is_correct"),
            "explanation_summary": item.get("explanation_summary"), "explanation_detail": item.get("explanation_detail"),
            "key_concepts": item.get("key_concepts"), "next_review_at": None if item.get("is_correct") else next_review
        })
    inserted_items = supabase.table("problem_items").insert(records).execute().data
    
    # 원본 문제 풀이 시도(Attempt) 기록 (기획서 반영)
    for item in inserted_items:
        attempt_records.append({"student_user_id": student_id, "problem_item_id": item['id'], "attempt_type": "original", "is_correct": item['is_correct']})
    supabase.table("attempts").insert(attempt_records).execute()
    return inserted_items

def check_cached_submission(student_id, file_hash):
    res = supabase.table("problem_submissions").select("id").eq("student_user_id", student_id).eq("file_hash", file_hash).execute()
    if res.data: return supabase.table("problem_items").select("*").eq("submission_id", res.data[0]["id"]).order("item_no").execute().data
    return None

def save_practice_item(problem_item_id, student_id, question, answer_key, concepts):
    return supabase.table("practice_items").insert({
        "problem_item_id": problem_item_id, "student_user_id": student_id,
        "generated_question": question, "expected_answer": answer_key, "key_concepts": concepts
    }).execute().data[0]

def update_practice_result(practice_id, student_answer, is_correct, student_id, problem_item_id):
    supabase.table("practice_items").update({"student_answer": student_answer, "is_correct": is_correct, "solved_at": datetime.utcnow().isoformat()}).eq("id", practice_id).execute()
    supabase.table("attempts").insert({"student_user_id": student_id, "problem_item_id": problem_item_id, "practice_item_id": practice_id, "attempt_type": "practice", "is_correct": is_correct}).execute()