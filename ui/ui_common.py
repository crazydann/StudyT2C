import streamlit as st


def st_image_fullwidth(img_bytes_or_url):
    """
    Streamlit 버전 호환용 이미지 렌더링.
    - 신버전: use_container_width
    - 구버전: use_column_width
    """
    try:
        st.image(img_bytes_or_url, use_container_width=True)
    except TypeError:
        st.image(img_bytes_or_url, use_column_width=True)


def get_role_state(role_key: str, user_id: str) -> dict:
    """
    ✅ 역할(teacher/parent 등) + 유저별 session_state 분리 헬퍼
    - role_key 예: "teacher", "parent"
    - user_id: 현재 로그인한 유저 id

    return: 해당 유저의 state dict
    """
    root_key = f"{role_key}_states"
    if root_key not in st.session_state:
        st.session_state[root_key] = {}

    states = st.session_state[root_key]
    if user_id not in states:
        states[user_id] = {}
    return states[user_id]