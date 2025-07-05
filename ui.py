# ui.py

import streamlit as st
import pandas as pd
import plotly.express as px
import re
import json
import datetime
from streamlit_option_menu import option_menu

from database import MongoManager
from services import EmailService, EnhancedWebScraper, LeadIntelligenceEngine

def authentication_ui(db_manager: MongoManager, email_service: EmailService):
    with st.sidebar:
        st.header("Welcome!")
        selected = option_menu(
            menu_title=None,
            options=["Login", "Sign Up"],
            icons=["box-arrow-in-right", "person-plus-fill"],
            default_index=0,
        )

    if selected == "Login":
        st.header("🔐 User Login")
        with st.form("login_form"):
            username = st.text_input("Username", placeholder="Enter your username").lower()
            password = st.text_input("Password", type="password", placeholder="Enter your password")
            login_button = st.form_submit_button("Login", type="primary", use_container_width=True)

            if login_button:
                if not username or not password:
                    st.warning("⚠️ Please enter both username and password.")
                else:
                    user = db_manager.find_user(username)
                    if user and db_manager.check_password(password, user['password_hash']):
                        if user.get('email_verified', False):
                            st.session_state.logged_in = True
                            st.session_state.username = username
                            st.session_state.email = user.get('email', '')
                            db_manager.update_last_login(username)
                            st.success("✅ Logged in successfully!")
                            st.rerun()
                        else:
                            st.error("❌ Please verify your email address before logging in.")
                            st.info("💡 Check your email for the verification OTP.")
                    else:
                        st.error("❌ Invalid username or password.")

    elif selected == "Sign Up":
        if not st.session_state.otp_stage:
            st.header("📝 Create New Account")
            with st.form("signup_form"):
                new_username = st.text_input("Username", placeholder="Choose a unique username").lower()
                new_email = st.text_input("Email Address", placeholder="Enter your email address").lower()
                new_password = st.text_input("Password", type="password", placeholder="Create a strong password")
                confirm_password = st.text_input("Confirm Password", type="password", placeholder="Confirm your password")
                st.markdown("---")
                agree_terms = st.checkbox("I agree to the Terms of Service and Privacy Policy")
                signup_button = st.form_submit_button("Create Account", type="primary", use_container_width=True)

                if signup_button:
                    if not all([new_username, new_email, new_password, confirm_password]):
                        st.warning("⚠️ Please fill out all fields.")
                    elif len(new_password) < 6:
                        st.warning("⚠️ Password must be at least 6 characters long.")
                    elif new_password != confirm_password:
                        st.error("❌ Passwords do not match.")
                    elif not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', new_email):
                        st.error("❌ Please enter a valid email address.")
                    elif not agree_terms:
                        st.warning("⚠️ Please agree to the Terms of Service and Privacy Policy.")
                    else:
                        result = db_manager.add_user(new_username, new_email, new_password)
                        if result["success"]:
                            otp = email_service.generate_otp()
                            if db_manager.store_otp(new_email, otp) and email_service.send_otp_email(new_email, otp, new_username):
                                st.session_state.otp_stage = True
                                st.session_state.temp_user_data = {"username": new_username, "email": new_email}
                                st.success("✅ Account created! Please check your email for the verification code.")
                                st.info("📧 We've sent a 6-digit OTP to your email address.")
                                st.rerun()
                            else:
                                st.error("❌ Failed to send verification email. Please try again.")
                        else:
                            st.error(f"❌ {result['message']}")
        
        else: # OTP Verification Stage
            st.header("📧 Email Verification")
            st.info(f"We've sent a verification code to **{st.session_state.temp_user_data.get('email', '')}**")
            
            with st.form("otp_form"):
                otp_input = st.text_input("6-Digit OTP", placeholder="Enter the code from your email", max_chars=6)
                verify_button = st.form_submit_button("Verify Email", type="primary", use_container_width=True)

                if verify_button:
                    if not otp_input or len(otp_input) != 6 or not otp_input.isdigit():
                        st.warning("⚠️ Please enter a valid 6-digit OTP.")
                    else:
                        result = db_manager.verify_otp(st.session_state.temp_user_data["email"], otp_input)
                        if result["success"]:
                            verified_username = st.session_state.temp_user_data["username"]
                            verified_email = st.session_state.temp_user_data["email"]
                            email_service.send_welcome_email(verified_email, verified_username)
                            st.success("🎉 Email verified successfully! You can now log in.")
                            st.balloons()
                            st.session_state.logged_in = True
                            st.session_state.username = verified_username
                            st.session_state.email = verified_email
                            st.session_state.otp_stage = False
                            st.session_state.temp_user_data = {}
                            st.rerun()
                        else:
                            st.error(f"❌ {result['message']}")
            if st.button("← Back to Sign Up"):
                st.session_state.otp_stage = False
                st.session_state.temp_user_data = {}
                st.rerun()

def main_app(db_manager: MongoManager):
    st.sidebar.success(f"👋 Welcome, {st.session_state.username}!")
    
    with st.sidebar:
        st.markdown("---")
        user_menu = option_menu(
            menu_title="Navigation",
            options=["Lead Analysis", "Search History", "Account Settings"],
            icons=["robot", "clock-history", "gear"],
            default_index=0,
        )
        st.markdown("---")
        if st.button("🚪 Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    if user_menu == "Lead Analysis":
        display_lead_analysis_page(db_manager)
    elif user_menu == "Search History":
        display_search_history(db_manager)
    elif user_menu == "Account Settings":
        display_account_settings(db_manager)

def display_lead_analysis_page(db_manager: MongoManager):
    st.title("🤖 AI-Powered Lead Intelligence Engine")
    st.markdown("Enter a company website to scrape its data and generate an AI-powered lead score and analysis.")

    with st.form("scrape_form"):
        url_input = st.text_input("Company Website URL:", placeholder="e.g., www.hubspot.com")
        submitted = st.form_submit_button("🔍 Analyze Company", type="primary", use_container_width=True)

    if submitted and url_input:
        scraper = EnhancedWebScraper()
        analyzer = LeadIntelligenceEngine()
        with st.spinner(f"🔍 Scraping data from {url_input}..."):
            st.session_state.scraped_data = scraper.scrape_company_data(url_input)
        
        if "error" in st.session_state.scraped_data:
            st.error(f"❌ {st.session_state.scraped_data['error']}")
        else:
            with st.spinner("🧠 AI is analyzing the company profile..."):
                st.session_state.analysis_result = analyzer.analyze_company_profile(st.session_state.scraped_data)
            
            if "error" in st.session_state.analysis_result:
                st.error(f"❌ {st.session_state.analysis_result['error']}")
            else:
                db_manager.store_analysis(
                    st.session_state.username,
                    st.session_state.scraped_data,
                    st.session_state.analysis_result
                )
                st.success("✅ Analysis complete!")

    if st.session_state.analysis_result and "error" not in st.session_state.analysis_result:
        display_analysis_results()

def display_analysis_results():
    res = st.session_state.analysis_result
    data = st.session_state.scraped_data
    
    st.markdown("---")
    st.header(f"📊 Analysis Results: {data.get('name', 'Unknown Company')}")
    
    col1, col2, col3, col4 = st.columns(4)
    score = res.get('lead_score', 0)
    col1.metric("Lead Score", f"{score}/100")
    col2.metric("Priority Level", res.get('priority', 'N/A'))
    col3.metric("Risk Level", res.get('risk_level', 'N/A'))
    col4.metric("Industry", data.get('industry', 'Unknown'))

    st.subheader("🤖 AI-Generated Analysis")
    st.info(f"💡 **Recommended Approach:** {res.get('recommended_approach', 'Not available.')}")
    st.write(res.get('rationale', 'Not available.'))
    
    with st.expander("📈 View Score Breakdown", expanded=False):
        breakdown = res.get('score_breakdown', {})
        if breakdown:
            df = pd.DataFrame(list(breakdown.items()), columns=['Criteria', 'Score Description'])
            st.table(df)

    st.markdown("---")
    st.header("🏢 Company Profile Data")
    
    with st.expander("🌐 General & Contact Information", expanded=True):
        st.markdown(f"**- Company Name:** `{data.get('name', 'N/A')}`")
        st.markdown(f"**- Website:** `{data.get('website', 'N/A')}`")
        st.markdown(f"**- Contact Emails:** `{', '.join(data.get('contact_emails', [])) or 'Not Found'}`")
        st.markdown(f"**- Phone Numbers:** `{', '.join(data.get('phone_numbers', [])) or 'Not Found'}`")
        st.write(f"**Description:** {data.get('description', 'No description available.')}")

    with st.expander("💻 Technology Stack", expanded=False):
        technologies = data.get('technologies', [])
        if technologies:
            st.write(', '.join(technologies))
        else:
            st.info("No specific technologies detected.")

def display_search_history(db_manager: MongoManager):
    st.header("📜 Search History")
    analyses = db_manager.get_user_analyses(st.session_state.username)
    
    if not analyses:
        st.info("No previous analyses found.")
        return
    
    for analysis in analyses:
        company_name = analysis["company_data"].get("name", "N/A")
        timestamp = analysis["timestamp"].strftime('%Y-%m-%d %H:%M:%S')
        with st.expander(f"{company_name} - {timestamp}"):
            st.json(analysis)

def display_account_settings(db_manager: MongoManager):
    st.header("⚙️ Account Settings")
    user = db_manager.find_user(st.session_state.username)
    
    if user:
        st.info(f"**Username:** {user.get('username', 'N/A')}")
        st.info(f"**Email:** {user.get('email', 'N/A')}")
        st.info(f"**Member Since:** {user.get('created_at').strftime('%B %d, %Y')}")