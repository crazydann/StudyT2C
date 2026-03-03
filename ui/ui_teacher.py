from ui.teacher_console import render_teacher_console
from ui.layout import render_app_header, page_card


def render(supabase, user):
    render_app_header("Teacher Console", user.get("handle", ""))
    with page_card():
        render_teacher_console(supabase, user)