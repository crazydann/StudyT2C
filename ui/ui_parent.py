from ui.parent_console import render_parent_console
from ui.layout import render_app_header, page_card


def render(supabase, user):
    render_app_header("학부모", user.get("handle", ""))
    with page_card():
        render_parent_console(supabase, user)