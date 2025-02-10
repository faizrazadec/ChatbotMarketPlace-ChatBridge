# app.py
import streamlit as st
from database import init_db, init_file_storage
from pages import login_page, main_app


def main():
    # Initialize the database and file storage at startup
    init_db()
    init_file_storage()

    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False

    if st.session_state.logged_in:
        main_app()
    else:
        login_page()


if __name__ == "__main__":
    main()
