import streamlit as st
from supabase import create_client

st.set_page_config(page_title="StudyT2C", layout="wide")

@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_connection()

def render_fake_login():
    st.sidebar.title("🔐 StudyT2C 로그인")
    
    try:
        response = supabase.table("users").select("id, handle, role").execute()
        users = response.data
    except Exception as e:
        st.sidebar.error(f"DB 오류: {e}")
        return None

    if not users:
        st.sidebar.warning("유저 데이터가 없습니다.")
        return None

    user_options = {f"{u['handle']} ({u['role']})": u for u in users}
    
    default_index = 0
    if "current_user" in st.session_state:
        current_handle = st.session_state["current_user"]["handle"]
        for i, key in enumerate(user_options.keys()):
            if current_handle in key:
                default_index = i
                break

    selected_label = st.sidebar.selectbox("계정 선택", options=list(user_options.keys()), index=default_index)
    current_user = user_options[selected_label]
    st.session_state["current_user"] = current_user
    
    st.sidebar.success(f"접속: {current_user['handle']}")
    return current_user

def main():
    current_user = render_fake_login()
    if not current_user:
        st.stop()
        
    role = current_user["role"]
    
    if role == "teacher":
        from ui import ui_teacher  # 수정됨
        ui_teacher.render(supabase, current_user)
    elif role == "parent":
        from ui import ui_parent   # 수정됨
        ui_parent.render(supabase, current_user)
    elif role == "student":
        from ui import ui_student  # 수정됨
        ui_student.render(supabase, current_user)

if __name__ == "__main__":
    main()