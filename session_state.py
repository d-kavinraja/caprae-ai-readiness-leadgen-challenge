# session_state.py

import streamlit as st

def initialize_session_state():
    """Initializes the Streamlit session state variables if they don't exist."""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'username' not in st.session_state:
        st.session_state.username = ""
    if 'email' not in st.session_state:
        st.session_state.email = ""
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    if 'scraped_data' not in st.session_state:
        st.session_state.scraped_data = None
    if 'otp_stage' not in st.session_state:
        st.session_state.otp_stage = False
    if 'temp_user_data' not in st.session_state:
        st.session_state.temp_user_data = {}
    if 'additional_insights' not in st.session_state:
        st.session_state.additional_insights = None