import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import json
from urllib.parse import urljoin, urlparse
import google.generativeai as genai
import plotly.express as px
from typing import List, Dict
import pymongo
import bcrypt
from streamlit_option_menu import option_menu
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
import datetime
from datetime import timedelta

# --- Page and App Configuration ---
st.set_page_config(page_title="Lead Intelligence Engine", layout="wide")

# --- Securely Load API Keys and Secrets ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    MONGO_URI = st.secrets["MONGO_URI"]
    HASH_SECRET_KEY = st.secrets["HASH_SECRET_KEY"].encode('utf-8')
    SMTP_SERVER = st.secrets["SMTP_SERVER"]
    SMTP_PORT = st.secrets["SMTP_PORT"]
    EMAIL_USER = st.secrets["EMAIL_USER"]
    EMAIL_PASSWORD = st.secrets["EMAIL_PASSWORD"]
    genai.configure(api_key=GEMINI_API_KEY)
except (FileNotFoundError, KeyError) as e:
    st.error("🚨 Critical Error: API keys or secrets are missing. Please configure your .streamlit/secrets.toml file.")
    st.error(f"Missing configuration: {e}")
    st.stop()

# --- Email Service Class ---
class EmailService:
    def __init__(self, smtp_server: str, smtp_port: int, email_user: str, email_password: str):
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port
        self.email_user = email_user
        self.email_password = email_password
    
    def generate_otp(self) -> str:
        return str(random.randint(100000, 999999))
    
    def send_otp_email(self, recipient_email: str, otp: str, username: str) -> bool:
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = recipient_email
            msg['Subject'] = "Lead Intelligence Engine - Email Verification"
            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                        <h2 style="color: #2E86AB; text-align: center;">🤖 Lead Intelligence Engine</h2>
                        <h3 style="color: #333;">Email Verification Required</h3>
                        <p>Hello <strong>{username}</strong>,</p>
                        <p>Thank you for signing up for Lead Intelligence Engine! To complete your registration, please verify your email address using the OTP below:</p>
                        <div style="background-color: #f8f9fa; padding: 20px; border-radius: 5px; text-align: center; margin: 20px 0;">
                            <h2 style="color: #2E86AB; font-size: 32px; letter-spacing: 5px; margin: 0;">{otp}</h2>
                        </div>
                        <p><strong>Important:</strong> This OTP will expire in 10 minutes for security reasons.</p>
                        <p>If you didn't create an account with us, please ignore this email.</p>
                        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                        <p style="font-size: 12px; color: #666; text-align: center;">
                            This is an automated message from Lead Intelligence Engine.<br>
                            Please do not reply to this email.
                        </p>
                    </div>
                </body>
            </html>
            """
            msg.attach(MIMEText(body, 'html'))
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            return True
        except Exception as e:
            st.error(f"Failed to send email: {str(e)}")
            return False
    
    def send_welcome_email(self, recipient_email: str, username: str) -> bool:
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = recipient_email
            msg['Subject'] = "Welcome to Lead Intelligence Engine!"
            body = f"""
            <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 10px;">
                        <h2 style="color: #2E86AB; text-align: center;">🎉 Welcome to Lead Intelligence Engine!</h2>
                        <p>Hello <strong>{username}</strong>,</p>
                        <p>Congratulations! Your email has been successfully verified and your account is now active.</p>
                        <div style="background-color: #d4edda; padding: 15px; border-radius: 5px; border-left: 4px solid #28a745; margin: 20px 0;">
                            <h4 style="margin: 0; color: #155724;">🚀 Ready to Get Started?</h4>
                            <p style="margin: 5px 0 0 0; color: #155724;">
                                You can now access all features of our AI-powered lead intelligence platform:
                            </p>
                            <ul style="color: #155724; margin: 10px 0 0 20px;">
                                <li>Advanced web scraping capabilities</li>
                                <li>AI-powered lead scoring and analysis</li>
                                <li>Comprehensive company profiling</li>
                                <li>Intelligent lead prioritization</li>
                            </ul>
                        </div>
                        <p>Start analyzing your leads today and unlock valuable business insights!</p>
                        <hr style="margin: 30px 0; border: none; border-top: 1px solid #eee;">
                        <p style="font-size: 12px; color: #666; text-align: center;">
                            Thank you for choosing Lead Intelligence Engine.<br>
                            If you have any questions, feel free to reach out to our support team.
                        </p>
                    </div>
                </body>
            </html>
            """
            msg.attach(MIMEText(body, 'html'))
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.email_user, self.email_password)
                server.send_message(msg)
            return True
        except Exception as e:
            st.error(f"Failed to send welcome email: {str(e)}")
            return False

# --- Enhanced Database Management Class ---
class MongoManager:
    def __init__(self, uri: str):
        try:
            self.client = pymongo.MongoClient(uri)
            self.client.admin.command('ping')
            self.db = self.client["lead_intelligence_app"]
            self.users_collection = self.db["users"]
            self.otp_collection = self.db["otp_verifications"]
            self.analyses_collection = self.db["analyses"]
            self.users_collection.create_index("username", unique=True)
            self.users_collection.create_index("email", unique=True)
            self.otp_collection.create_index("expires_at", expireAfterSeconds=0)
            self.analyses_collection.create_index([("username", pymongo.ASCENDING), ("timestamp", pymongo.DESCENDING)])
        except pymongo.errors.ConnectionFailure as e:
            st.error(f"Database connection failed: {e}", icon="🚨")
            st.stop()
        except Exception as e:
            st.error(f"An error occurred with the database setup: {e}", icon="🚨")
            st.stop()

    def _hash_password(self, password: str) -> bytes:
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    def check_password(self, password: str, hashed: bytes) -> bool:
        return bcrypt.checkpw(password.encode('utf-8'), hashed)

    def add_user(self, username: str, email: str, password: str) -> Dict:
        if self.users_collection.find_one({"username": username}):
            return {"success": False, "message": "Username already exists"}
        if self.users_collection.find_one({"email": email}):
            return {"success": False, "message": "Email already registered"}
        hashed_password = self._hash_password(password)
        user_data = {
            "username": username,
            "email": email,
            "password_hash": hashed_password,
            "email_verified": False,
            "created_at": datetime.datetime.now(datetime.UTC),
            "last_login": None
        }
        self.users_collection.insert_one(user_data)
        return {"success": True, "message": "User created successfully"}

    def find_user(self, username: str) -> Dict | None:
        return self.users_collection.find_one({"username": username})
    
    def find_user_by_email(self, email: str) -> Dict | None:
        return self.users_collection.find_one({"email": email})

    def store_otp(self, email: str, otp: str) -> bool:
        try:
            self.otp_collection.delete_many({"email": email})
            otp_data = {
                "email": email,
                "otp": otp,
                "created_at": datetime.datetime.now(datetime.UTC),
                "expires_at": datetime.datetime.now(datetime.UTC) + timedelta(minutes=10),
                "attempts": 0
            }
            self.otp_collection.insert_one(otp_data)
            return True
        except Exception as e:
            st.error(f"Failed to store OTP: {str(e)}")
            return False

    def verify_otp(self, email: str, otp: str) -> Dict:
        try:
            otp_record = self.otp_collection.find_one({"email": email})
            if not otp_record:
                return {"success": False, "message": "No OTP found for this email"}
            if datetime.datetime.now(datetime.UTC) > otp_record["expires_at"]:
                self.otp_collection.delete_one({"email": email})
                return {"success": False, "messageAs": "OTP has expired. Please request a new one"}
            if otp_record["attempts"] >= 3:
                self.otp_collection.delete_one({"email": email})
                return {"success": False, "message": "Too many failed attempts. Please request a new OTP"}
            if otp_record["otp"] == otp:
                self.users_collection.update_one(
                    {"email": email},
                    {"$set": {"email_verified": True}}
                )
                self.otp_collection.delete_one({"email": email})
                return {"success": True, "message": "Email verified successfully"}
            else:
                self.otp_collection.update_one(
                    {"email": email},
                    {"$inc": {"attempts": 1}}
                )
                remaining_attempts = 3 - (otp_record["attempts"] + 1)
                return {
                    "success": False, 
                    "message": f"Invalid OTP. {remaining_attempts} attempts remaining"
                }
        except Exception as e:
            st.error(f"Error verifying OTP: {str(e)}")
            return {"success": False, "message": "Verification failed due to system error"}

    def update_last_login(self, username: str):
        self.users_collection.update_one(
            {"username": username},
            {"$set": {"last_login": datetime.datetime.now(datetime.UTC)}}
        )

    def store_analysis(self, username: str, company_data: Dict, analysis_result: Dict, additional_insights: Dict = None):
        try:
            analysis_data = {
                "username": username,
                "company_data": company_data,
                "analysis_result": analysis_result,
                "additional_insights": additional_insights or {},
                "timestamp": datetime.datetime.now(datetime.UTC)
            }
            self.analyses_collection.insert_one(analysis_data)
            return {"success": True, "message": "Analysis stored successfully"}
        except Exception as e:
            st.error(f"Failed to store analysis: {str(e)}")
            return {"success": False, "message": "Failed to store analysis"}

    def get_user_analyses(self, username: str) -> List[Dict]:
        return list(self.analyses_collection.find({"username": username}).sort("timestamp", pymongo.DESCENDING))

# --- AI & Scraper Class Definitions ---
class LeadIntelligenceEngine:
    def __init__(self):
        try:
            self.model = genai.GenerativeModel('gemini-2.0-flash')
        except Exception as e:
            st.error(f"Failed to initialize Gemini model: {e}.")
            self.model = None

    def analyze_company_profile(self, company_data: Dict) -> Dict:
        if self.model is None:
            return {
                "lead_score": 0, "score_breakdown": {},
                "rationale": "AI model not initialized.", "priority": "Low",
                "risk_level": "High", "recommended_approach": "Manual review required."
            }
        prompt = f"""
        Analyze this company profile and provide a lead quality score (0-100) with detailed rationale.
        Company Data:
        - Name: {company_data.get('name', 'Unknown')}
        - Website: {company_data.get('website', 'N/A')}
        - Industry: {company_data.get('industry', 'N/A')}
        - Description: {company_data.get('description', 'N/A')}
        - Technologies Detected: {', '.join(company_data.get('technologies', []))}
        - Estimated Team Size: {company_data.get('team_size', 'N/A')}
        - Estimated Funding Stage: {company_data.get('funding_stage', 'N/A')}
        - Contact Emails: {', '.join(company_data.get('contact_emails', []))}
        - Phone Numbers: {', '.join(company_data.get('phone_numbers', []))}
        - Social Media Presence: {json.dumps(company_data.get('social_media', {}))}
        Scoring Criteria:
        1. Business Maturity (e.g., funding, team size): 20%
        2. Growth Potential (e.g., industry trends, tech adoption): 20%
        3. Technology Stack Fit (relevance to our services): 15%
        4. Market Position (e.g., niche, competition): 15%
        5. Contact Info Availability: 10%
        6. Website & Content Quality: 10%
        7. Social Proof (active social media, partnerships): 10%
        Return ONLY a valid JSON response with these fields, no extra text or markdown fences:
        - "lead_score": An integer score (0-100).
        - "score_breakdown": A dictionary where keys are the criteria (e.g., "Business Maturity") and values are strings with the score and a brief justification (e.g., "18/20 - Strong indicators of stability...").
        - "rationale": A comprehensive paragraph explaining the overall score.
        - "priority": "High", "Medium", or "Low".
        - "recommended_approach": A short, actionable outreach strategy.
        - "risk_level": "Low", "Medium", or "High".
        """
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip().replace("```json", "").replace("```", "")
            analysis = json.loads(response_text)
            score = int(analysis.get('lead_score', 50))
            analysis['lead_score'] = max(0, min(100, score))
            analysis['priority'] = "High" if score > 75 else "Medium" if score > 50 else "Low"
            analysis['risk_level'] = "Low" if score > 70 else "Medium" if score > 45 else "High"
            analysis.setdefault("rationale", "No detailed rationale provided by AI.")
            analysis.setdefault("recommended_approach", "Generic outreach recommended.")
            return analysis
        except Exception as e:
            return {"error": f"Error during AI content generation: {str(e)}"}

    def generate_additional_insights(self, company_data: Dict) -> Dict:
        if self.model is None:
            return {"insights": "AI model not initialized."}
        prompt = f"""
        Provide additional insights for a company based on its industry and contact information.
        Company Data:
        - Name: {company_data.get('name', 'Unknown')}
        - Website: {company_data.get('website', 'N/A')}
        - Industry: {company_data.get('industry', 'N/A')}
        - Phone Numbers: {', '.join(company_data.get('phone_numbers', []))}
        - Description: {company_data.get('description', 'N/A')}
        Return ONLY a valid JSON response with these fields, no extra text or markdown fences:
        - "insights": A paragraph providing actionable insights (e.g., market opportunities, outreach strategies, or industry-specific recommendations).
        - "industry_trends": A brief description of current trends in the company's industry.
        - "outreach_strategy": A specific strategy for contacting the company using the available phone numbers.
        """
        try:
            response = self.model.generate_content(prompt)
            response_text = response.text.strip().replace("```json", "").replace("```", "")
            insights = json.loads(response_text)
            insights.setdefault("insights", "No additional insights provided.")
            insights.setdefault("industry_trends", "No industry trends available.")
            insights.setdefault("outreach_strategy", "Generic phone outreach recommended.")
            return insights
        except Exception as e:
            return {"insights": f"Error generating insights: {str(e)}", "industry_trends": "", "outreach_strategy": ""}

class EnhancedWebScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36'
        })

    def scrape_company_data(self, url: str) -> Dict:
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url
        company_data = {'website': url}
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            html_string = str(soup)
            page_text = soup.get_text().lower()
            company_data.update({
                'name': self._extract_company_name(soup, url),
                'description': self._extract_description(soup),
                'industry': self._extract_industry(page_text),
                'contact_emails': self._extract_emails(html_string),
                'phone_numbers': self._extract_phones(html_string),
                'social_media': self._extract_social_media(soup),
                'technologies': self._extract_technologies(html_string),
                'team_size': self._estimate_team_size(page_text),
                'funding_stage': self._estimate_funding_stage(page_text)
            })
        except requests.RequestException as e:
            company_data['error'] = f"Failed to scrape {url}. Reason: {str(e)}"
        return company_data

    def _extract_company_name(self, soup, url) -> str:
        selectors = ['meta[property="og:site_name"]', 'title']
        for selector in selectors:
            element = soup.select_one(selector)
            if element:
                name = element.get('content', '') or element.get_text()
                name = re.sub(r' \| .*', '', name).strip()
                name = re.sub(r' - .*', '', name).strip()
                if name: return name
        return urlparse(url).netloc.replace('www.', '').split('.')[0].title()

    def _extract_description(self, soup) -> str:
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        if meta_desc and meta_desc.get('content'):
            return meta_desc['content'].strip()
        return "No meta description found."

    def _extract_industry(self, content: str) -> str:
        industry_keywords = {
            'Education': ['education', 'college', 'university', 'edtech', 'school', 'academic', 'institute', 'learning'],
            'SaaS': ['software as a service', 'saas', 'cloud solution'], 'FinTech': ['financial technology', 'payments', 'banking'],
            'Healthcare': ['health tech', 'medical', 'patient care', 'biotech', 'hospital'],
            'E-commerce': ['online retail', 'e-commerce', 'marketplace'], 'AI/ML': ['artificial intelligence', 'machine learning', 'data science'],
            'Marketing': ['digital marketing', 'seo', 'advertising agency'],
        }
        for industry, keywords in industry_keywords.items():
            if any(re.search(r'\b' + re.escape(kw) + r'\b', content) for kw in keywords):
                return industry
        return "Unknown"

    def _extract_emails(self, content: str) -> List[str]:
        return list(set(re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content)))[:5]

    def _extract_phones(self, content: str) -> List[str]:
        phone_pattern = r'(\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,5}[-.\s]?\d{3,5}'
        raw_matches = re.findall(phone_pattern, content)
        cleaned_phones = []
        for match in raw_matches:
            digits = re.sub(r'\D', '', match)
            if 8 <= len(digits) <= 15:
                cleaned_phones.append(match.strip())
        return list(set(cleaned_phones))[:3]

    def _extract_social_media(self, soup) -> Dict[str, str]:
        social_links = {}
        platforms = ['linkedin', 'twitter', 'facebook', 'instagram', 'youtube', 'github']
        for a in soup.find_all('a', href=True):
            href = a['href'].lower()
            for platform in platforms:
                if platform not in social_links and platform in href:
                    social_links[platform.title()] = a['href']
        return social_links

    def _extract_technologies(self, content: str) -> List[str]:
        tech_indicators = {
            'React': ['react.js', 'react-dom', 'data-reactroot'], 'Angular': ['angular.js', 'ng-app'],
            'Vue.js': ['vue.js', 'data-v-app'], 'jQuery': ['jquery.js', 'jquery.min.js'],
            'Shopify': ['shopify.com', 'cdn.shopify.com'], 'WooCommerce': ['woocommerce'],
            'Magento': ['magento'], 'BigCommerce': ['bigcommerce'],
            'WordPress': ['wp-content', 'wp-json'], 'Drupal': ['drupal.js', 'sites/default'],
            'Joomla': ['joomla'], 'Contentful': ['contentful'], 'Sanity': ['sanity.io'],
            'Google Analytics': ['google-analytics.com/analytics.js', 'gtag('],
            'HubSpot': ['js.hs-scripts.com', '_hsq.push'], 'Marketo': ['munchkin.js'],
            'Segment': ['cdn.segment.com'], 'Hotjar': ['hotjar.com', 'hj('],
            'Google Tag Manager': ['googletagmanager.com/gtm.js'], 'Node.js': ['node.js'],
            'PHP': ['.php'], 'ASP.NET': ['.aspx'], 'Stripe': ['js.stripe.com'],
            'Braintree': ['js.braintreegateway.com'], 'Zendesk': ['zendesk.com'],
            'Intercom': ['intercom.io', 'widget.intercom.io'],
        }
        found_tech = []
        lower_content = content.lower()
        for tech, indicators in tech_indicators.items():
            if any(indicator in lower_content for indicator in indicators):
                found_tech.append(tech)
        return list(set(found_tech))

    def _estimate_team_size(self, content: str) -> str:
        match = re.search(r'(?:team of|employees|members|we are|we have)\s*([\d,]+(?:\s*to\s*|-)?[\d,]+?)\b', content, re.IGNORECASE)
        if match: return match.group(1).strip()
        size_tiers = {
            '1-10': ['1-10', 'small team', 'startup team'], '11-50': ['11-50'], '51-200': ['51-200', 'mid-sized'],
            '201-500': ['201-500'], '501+': ['501+', '500+', 'large team', 'enterprise']
        }
        for size, terms in size_tiers.items():
            if any(term in content for term in terms): return size
        return "Unknown"

    def _estimate_funding_stage(self, content: str) -> str:
        funding_stages = {
            'Seed/Pre-Seed': ['seed round', 'pre-seed', 'angel investment'], 'Series A': ['series a'],
            'Series B': ['series b'], 'Series C+': ['series c', 'series d'],
            'Venture Capital': ['venture capital', 'backed by vc'],
            'Acquired': ['acquired by', 'acquisition'], 'Bootstrapped': ['bootstrapped', 'self-funded']
        }
        for stage, terms in funding_stages.items():
            if any(re.search(r'\b' + term + r'\b', content, re.IGNORECASE) for term in terms): return stage
        return "Unknown"

# --- Initialize Session State ---
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

# --- Authentication UI ---
def authentication_ui():
    db_manager = MongoManager(MONGO_URI)
    email_service = EmailService(SMTP_SERVER, SMTP_PORT, EMAIL_USER, EMAIL_PASSWORD)
    
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
                                st.session_state.temp_user_data = {
                                    "username": new_username,
                                    "email": new_email
                                }
                                st.success("✅ Account created! Please check your email for the verification code.")
                                st.info("📧 We've sent a 6-digit OTP to your email address. Please enter it below to complete your registration.")
                                st.rerun()
                            else:
                                st.error("❌ Failed to send verification email. Please try again.")
                        else:
                            st.error(f"❌ {result['message']}")
        
        else:
            st.header("📧 Email Verification")
            st.info(f"We've sent a verification code to **{st.session_state.temp_user_data.get('email', '')}**")
            
            with st.form("otp_form"):
                st.markdown("#### Enter Verification Code")
                otp_input = st.text_input(
                    "6-Digit OTP", 
                    placeholder="Enter the 6-digit code from your email",
                    max_chars=6,
                    help="The OTP expires in 10 minutes"
                )
                col1, col2 = st.columns(2)
                with col1:
                    verify_button = st.form_submit_button("Verify Email", type="primary", use_container_width=True)
                with col2:
                    resend_button = st.form_submit_button("Resend Code", use_container_width=True)

                if verify_button:
                    if not otp_input:
                        st.warning("⚠️ Please enter the OTP.")
                    elif len(otp_input) != 6 or not otp_input.isdigit():
                        st.error("❌ Please enter a valid 6-digit OTP.")
                    else:
                        result = db_manager.verify_otp(st.session_state.temp_user_data["email"], otp_input)
                        if result["success"]:
                            email_service.send_welcome_email(
                                st.session_state.temp_user_data["email"],
                                st.session_state.temp_user_data["username"]
                            )
                            st.success("🎉 Email verified successfully! You can now log in.")
                            st.balloons()
                            st.session_state.otp_stage = False
                            st.session_state.temp_user_data = {}
                            st.session_state.logged_in = True
                            st.session_state.username = st.session_state.temp_user_data.get("username", "")
                            st.session_state.email = st.session_state.temp_user_data.get("email", "")
                            st.rerun()
                        else:
                            st.error(f"❌ {result['message']}")

                if resend_button:
                    otp = email_service.generate_otp()
                    if db_manager.store_otp(st.session_state.temp_user_data["email"], otp) and \
                       email_service.send_otp_email(st.session_state.temp_user_data["email"], otp, st.session_state.temp_user_data["username"]):
                        st.success("✅ New verification code sent to your email!")
                    else:
                        st.error("❌ Failed to resend verification code. Please try again.")

            if st.button("← Back to Sign Up", help="Go back to modify your registration details"):
                st.session_state.otp_stage = False
                st.session_state.temp_user_data = {}
                st.rerun()

# --- Main Lead Intelligence App UI ---
def main_app():
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
            st.session_state.logged_in = False
            st.session_state.username = ""
            st.session_state.email = ""
            st.session_state.analysis_result = None
            st.session_state.scraped_data = None
            st.session_state.additional_insights = None
            st.rerun()

    if user_menu == "Lead Analysis":
        st.title("🤖 AI-Powered Lead Intelligence Engine")
        st.markdown("Enter a company website to scrape its data and generate an AI-powered lead score and analysis.")

        with st.form("scrape_form"):
            st.markdown("#### Company Analysis")
            url_input = st.text_input(
                "Company Website URL:", 
                placeholder="e.g., www.hubspot.com, tesla.com, or https://example.com",
                help="Enter the company's website URL (with or without https://)"
            )
            col1, col2 = st.columns([3, 1])
            with col1:
                submitted = st.form_submit_button("🔍 Analyze Company", type="primary", use_container_width=True)
            with col2:
                clear_button = st.form_submit_button("🗑️ Clear Results", use_container_width=True)

        if clear_button:
            st.session_state.analysis_result = None
            st.session_state.scraped_data = None
            st.session_state.additional_insights = None
            st.rerun()

        if submitted and url_input:
            scraper = EnhancedWebScraper()
            analyzer = LeadIntelligenceEngine()
            db_manager = MongoManager(MONGO_URI)
            
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
                    if (st.session_state.scraped_data.get('phone_numbers', []) and 
                        st.session_state.scraped_data.get('industry', 'Unknown') != 'Unknown'):
                        with st.spinner("🧠 Generating additional insights..."):
                            st.session_state.additional_insights = analyzer.generate_additional_insights(st.session_state.scraped_data)
                    else:
                        st.session_state.additional_insights = None
                    
                    db_manager.store_analysis(
                        st.session_state.username,
                        st.session_state.scraped_data,
                        st.session_state.analysis_result,
                        st.session_state.additional_insights
                    )
                    st.success("✅ Analysis complete!")

        if st.session_state.analysis_result and "error" not in st.session_state.analysis_result:
            display_analysis_results()

    elif user_menu == "Search History":
        display_search_history()
    
    elif user_menu == "Account Settings":
        display_account_settings()

def display_analysis_results():
    res = st.session_state.analysis_result
    data = st.session_state.scraped_data
    additional_insights = st.session_state.additional_insights
    
    st.markdown("---")
    st.header(f"📊 Analysis Results: {data.get('name', 'Unknown Company')}")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        score = res.get('lead_score', 0)
        score_color = "green" if score > 75 else "orange" if score > 50 else "red"
        st.metric(
            "Lead Score", 
            f"{score}/100",
            help="AI-generated lead quality score based on multiple factors"
        )
    
    with col2:
        priority = res.get('priority', 'N/A')
        priority_color = "green" if priority == "High" else "orange" if priority == "Medium" else "red"
        st.metric("Priority Level", priority)
    
    with col3:
        risk = res.get('risk_level', 'N/A')
        risk_color = "green" if risk == "Low" else "orange" if risk == "Medium" else "red"
        st.metric("Risk Level", risk)
    
    with col4:
        industry = data.get('industry', 'Unknown')
        st.metric("Industry", industry)

    st.subheader("🤖 AI-Generated Analysis")
    
    st.markdown("##### 🎯 **Recommended Approach**")
    approach = res.get('recommended_approach', 'Not available.')
    st.info(f"💡 {approach}")
    
    st.markdown("##### 📝 **Analysis Rationale**")
    rationale = res.get('rationale', 'Not available.')
    st.write(rationale)
    
    st.markdown("##### 📈 **Score Breakdown**")
    breakdown = res.get('score_breakdown', {})
    
    if breakdown:
        col1, col2 = st.columns([1, 1])
        with col1:
            for i, (criteria, score_desc) in enumerate(breakdown.items()):
                if i % 2 == 0:
                    st.markdown(f"**{criteria}:** {score_desc}")
        with col2:
            for i, (criteria, score_desc) in enumerate(breakdown.items()):
                if i % 2 == 1:
                    st.markdown(f"**{criteria}:** {score_desc}")
        
        parsed_scores = {}
        for k, v in breakdown.items():
            match = re.match(r'(\d+)', v)
            if match:
                parsed_scores[k] = int(match.group(1))
        
        if parsed_scores:
            df = pd.DataFrame(list(parsed_scores.items()), columns=['Criteria', 'Score'])
            fig = px.bar(
                df, 
                x='Score', 
                y='Criteria', 
                orientation='h', 
                title="Lead Score by Criteria",
                text_auto=True,
                color='Score',
                color_continuous_scale='RdYlGn'
            )
            fig.update_layout(
                xaxis_title="Score", 
                yaxis_title="",
                showlegend=False,
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)

    if additional_insights:
        with st.expander("🔍 Additional Insights", expanded=True):
            st.markdown("##### 📝 **Industry-Specific Insights**")
            st.write(additional_insights.get('insights', 'No insights available.'))
            st.markdown("##### 🌍 **Industry Trends**")
            st.write(additional_insights.get('industry_trends', 'No trends available.'))
            st.markdown("##### 📞 **Outreach Strategy**")
            st.info(f"💡 {additional_insights.get('outreach_strategy', 'No strategy available.')}")

    st.markdown("---")
    st.header("🏢 Company Profile Data")
    
    with st.expander("🌐 General & Contact Information", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown(f"**Company Name:** `{data.get('name', 'N/A')}`")
            st.markdown(f"**Website:** `{data.get('website', 'N/A')}`")
            st.markdown(f"**Industry:** `{data.get('industry', 'N/A')}`")
            st.markdown(f"**Team Size:** `{data.get('team_size', 'N/A')}`")
            st.markdown(f"**Funding Stage:** `{data.get('funding_stage', 'N/A')}`")
        
        with col2:
            emails = data.get('contact_emails', [])
            phones = data.get('phone_numbers', [])
            st.markdown(f"**Contact Emails:** `{', '.join(emails) if emails else 'Not Found'}`")
            st.markdown(f"**Phone Numbers:** `{', '.join(phones) if phones else 'Not Found'}`")
            social_media = data.get('social_media', {})
            if social_media:
                st.markdown("**Social Media:**")
                for platform, url in social_media.items():
                    st.markdown(f"- [{platform}]({url})")
            else:
                st.markdown("**Social Media:** `Not Found`")
        
        st.markdown("**Description:**")
        st.write(data.get('description', 'No description available.'))

    with st.expander("💻 Technology Stack", expanded=False):
        technologies = data.get('technologies', [])
        if technologies:
            tech_html = ""
            for tech in technologies:
                tech_html += f'<span style="display: inline-block; background-color: #e3f2fd; color: #1976d2; padding: 4px 8px; margin: 2px; border-radius: 4px; font-size: 12px;">{tech}</span>'
            st.markdown(tech_html, unsafe_allow_html=True)
        else:
            st.info("No specific technologies detected on the website.")

    st.markdown("---")
    st.subheader("📤 Export Options")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📋 Copy Lead Summary", use_container_width=True):
            summary = f"""
Lead Analysis Summary
Company: {data.get('name', 'N/A')}
Website: {data.get('website', 'N/A')}
Lead Score: {res.get('lead_score', 0)}/100
Priority: {res.get('priority', 'N/A')}
Risk Level: {res.get('risk_level', 'N/A')}
Recommended Approach: {res.get('recommended_approach', 'N/A')}
            """.strip()
            st.code(summary)
    
    with col2:
        export_data = {
            "company_data": data,
            "analysis_result": res,
            "additional_insights": additional_insights or {},
            "analysis_date": datetime.datetime.now().isoformat(),
            "analyzed_by": st.session_state.username
        }
        json_data = json.dumps(export_data, indent=2)
        st.download_button(
            label="📄 Download JSON Report",
            data=json_data,
            file_name=f"lead_analysis_{data.get('name', 'company').replace(' ', '_').lower()}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True
        )
    
    with col3:
        csv_data = pd.DataFrame([{
            'Company Name': data.get('name', 'N/A'),
            'Website': data.get('website', 'N/A'),
            'Industry': data.get('industry', 'N/A'),
            'Lead Score': res.get('lead_score', 0),
            'Priority': res.get('priority', 'N/A'),
            'Risk Level': res.get('risk_level', 'N/A'),
            'Team Size': data.get('team_size', 'N/A'),
            'Funding Stage': data.get('funding_stage', 'N/A'),
            'Contact Emails': ', '.join(data.get('contact_emails', [])),
            'Phone Numbers': ', '.join(data.get('phone_numbers', [])),
            'Technologies': ', '.join(data.get('technologies', [])),
            'Recommended Approach': res.get('recommended_approach', 'N/A'),
            'Analysis Date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'Analyzed By': st.session_state.username
        }])
        csv_string = csv_data.to_csv(index=False)
        st.download_button(
            label="📊 Download CSV Report",
            data=csv_string,
            file_name=f"lead_analysis_{data.get('name', 'company').replace(' ', '_').lower()}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

def display_search_history():
    st.header("📜 Search History")
    st.markdown("View your past company analyses below.")
    
    db_manager = MongoManager(MONGO_URI)
    analyses = db_manager.get_user_analyses(st.session_state.username)
    
    if not analyses:
        st.info("No previous analyses found.")
        return
    
    history_data = [
        {
            "Company Name": analysis["company_data"].get("name", "N/A"),
            "Website": analysis["company_data"].get("website", "N/A"),
            "Lead Score": analysis["analysis_result"].get("lead_score", 0),
            "Industry": analysis["company_data"].get("industry", "N/A"),
            "Timestamp": analysis["timestamp"].strftime('%Y-%m-%d %H:%M:%S'),
            "Action": index
        }
        for index, analysis in enumerate(analyses)
    ]
    
    df = pd.DataFrame(history_data)
    st.dataframe(
        df[["Company Name", "Website", "Lead Score", "Industry", "Timestamp"]],
        use_container_width=True,
        hide_index=True
    )
    
    st.markdown("##### Select an Analysis to View")
    selected_index = st.selectbox(
        "Choose an analysis:",
        options=range(len(history_data)),
        format_func=lambda i: f"{history_data[i]['Company Name']} ({history_data[i]['Timestamp']})"
    )
    
    if st.button("View Selected Analysis", use_container_width=True):
        selected_analysis = analyses[selected_index]
        st.session_state.scraped_data = selected_analysis["company_data"]
        st.session_state.analysis_result = selected_analysis["analysis_result"]
        st.session_state.additional_insights = selected_analysis.get("additional_insights", None)
        st.session_state.user_menu = "Lead Analysis"
        st.rerun()

def display_account_settings():
    st.header("⚙️ Account Settings")
    
    db_manager = MongoManager(MONGO_URI)
    user = db_manager.find_user(st.session_state.username)
    
    if user:
        st.subheader("👤 Profile Information")
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**Username:** {user.get('username', 'N/A')}")
            st.info(f"**Email:** {user.get('email', 'N/A')}")
            st.info(f"**Email Verified:** {'✅ Yes' if user.get('email_verified', False) else '❌ No'}")
        with col2:
            created_at = user.get('created_at')
            last_login = user.get('last_login')
            if created_at:
                st.info(f"**Member Since:** {created_at.strftime('%B %d, %Y')}")
            if last_login:
                st.info(f"**Last Login:** {last_login.strftime('%B %d, %Y at %I:%M %p')}")
        
        st.markdown("---")
        st.subheader("🔧 Account Actions")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("🔄 Change Password", use_container_width=True):
                st.info("Password change functionality would be implemented here with proper security measures.")
        with col2:
            if st.button("📧 Update Email", use_container_width=True):
                st.info("Email update functionality would be implemented here with re-verification.")
        with col3:
            if st.button("❌ Delete Account", use_container_width=True, type="secondary"):
                st.warning("Account deletion would be implemented here with proper confirmation steps.")
        
        st.markdown("---")


# --- App Router ---
def main():
    if not st.session_state.logged_in:
        authentication_ui()
    else:
        main_app()

if __name__ == "__main__":
    main()
