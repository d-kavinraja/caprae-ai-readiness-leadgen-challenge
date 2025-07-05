# config.py

import streamlit as st
import google.generativeai as genai

def load_secrets():
    """
    Loads all necessary API keys and secrets from Streamlit's secrets manager.
    Returns a dictionary of secrets or stops the app if critical keys are missing.
    """
    try:
        secrets = {
            "GEMINI_API_KEY": st.secrets["GEMINI_API_KEY"],
            "MONGO_URI": st.secrets["MONGO_URI"],
            "HASH_SECRET_KEY": st.secrets["HASH_SECRET_KEY"].encode('utf-8'),
            "SMTP_SERVER": st.secrets["SMTP_SERVER"],
            "SMTP_PORT": st.secrets["SMTP_PORT"],
            "EMAIL_USER": st.secrets["EMAIL_USER"],
            "EMAIL_PASSWORD": st.secrets["EMAIL_PASSWORD"],
        }
        # Configure the Generative AI model
        genai.configure(api_key=secrets["GEMINI_API_KEY"])
        return secrets
    except (FileNotFoundError, KeyError) as e:
        st.error("🚨 Critical Error: API keys or secrets are missing. Please configure your .streamlit/secrets.toml file.")
        st.error(f"Missing configuration: {e}")
        st.stop()