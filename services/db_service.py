# services/db_service.py
"""
Facade module for DB functions.

Existing code should continue to do:
  from services.db_service import ...

Internals are split into services/db/*.py
"""
from services.db.base import DbServiceError  # re-export

# users
from services.db.users import list_users_by_role

# chat
from services.db.chat import save_chat_message, list_chat_messages

# grading/submissions/items
from services.db.grading import (
    check_cached_submission,
    upsert_problem_submission,
    list_grading_submissions,
    get_submission_items,
    get_submission_stats,
    save_grading_results,
)

# feedback (wrongnote)
from services.db.feedback import (
    upsert_problem_item_feedback,
    get_problem_item_feedback_map,
)

# homework
from services.db.homework import (
    list_homework_status_for_student,
    upsert_homework_non_submit_reason,
    get_homework_non_submit_reason_map,
)

# practice
from services.db.practice import (
    save_practice_item,
    update_practice_result,
)

# notes
from services.db.notes import (
    get_teacher_student_note,
    upsert_teacher_student_note,
)

__all__ = [
    # error
    "DbServiceError",
    # users
    "list_users_by_role",
    # chat
    "save_chat_message",
    "list_chat_messages",
    # grading
    "check_cached_submission",
    "upsert_problem_submission",
    "list_grading_submissions",
    "get_submission_items",
    "get_submission_stats",
    "save_grading_results",
    # feedback
    "upsert_problem_item_feedback",
    "get_problem_item_feedback_map",
    # homework
    "list_homework_status_for_student",
    "upsert_homework_non_submit_reason",
    "get_homework_non_submit_reason_map",
    # practice
    "save_practice_item",
    "update_practice_result",
    # notes
    "get_teacher_student_note",
    "upsert_teacher_student_note",
]