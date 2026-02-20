# ui/ui_student.py
from ui.student.console import render_student_console


def render(supabase, user):
    # 기존 엔트리 유지: app.py에서 ui_student.render(...) 호출하는 구조 호환
    return render_student_console(supabase, user)