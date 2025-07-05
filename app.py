# app.py

import streamlit as st
from config import load_secrets
from database import MongoManager
from services import EmailService
from ui import authentication_ui, main_app
from session_state import initialize_session_state

def main():
    """
    Main function to configure, initialize, and run the Streamlit application.
    """
    # --- Page and App Configuration ---
    st.set_page_config(page_title="Lead Intelligence Engine", layout="wide")

    # --- Load Configuration and Initialize Services ---
    # This should be at the top to ensure secrets are loaded once
    @st.cache_resource
    def get_resources():
        secrets = load_secrets()
        db_manager = MongoManager(secrets["MONGO_URI"])
        email_service = EmailService(
            secrets["SMTP_SERVER"],
            secrets["SMTP_PORT"],
            secrets["EMAIL_USER"],
            secrets["EMAIL_PASSWORD"]
        )
        return db_manager, email_service

    db_manager, email_service = get_resources()

    # --- Initialize Session State ---
    initialize_session_state()

    # --- App Router ---
    if not st.session_state.logged_in:
        authentication_ui(db_manager, email_service)
    else:
        main_app(db_manager)

if __name__ == "__main__":
    main()