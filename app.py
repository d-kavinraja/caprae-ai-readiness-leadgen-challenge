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

# --- Page and App Configuration ---
st.set_page_config(page_title="Lead Intelligence Engine", layout="wide")


# --- Securely Load API Keys and Secrets ---
try:
    GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
    MONGO_URI = st.secrets["MONGO_URI"]
    HASH_SECRET_KEY = st.secrets["HASH_SECRET_KEY"].encode('utf-8') # Encode secret key for bcrypt
    genai.configure(api_key=GEMINI_API_KEY)
except (FileNotFoundError, KeyError):
    st.error("🚨 Critical Error: API keys or secrets are missing. Please configure your .streamlit/secrets.toml file.")
    st.stop()


# --- Database Management Class ---
class MongoManager:
    """Handles all interactions with the MongoDB Atlas database."""
    def __init__(self, uri: str):
        try:
            self.client = pymongo.MongoClient(uri)
            # Test the connection
            self.client.admin.command('ping')
            self.db = self.client["lead_intelligence_app"]
            self.users_collection = self.db["users"]
            # Create a unique index on the username field to prevent duplicates
            self.users_collection.create_index("username", unique=True)
        except pymongo.errors.ConnectionFailure as e:
            st.error(f"Database connection failed: {e}", icon="🚨")
            st.stop()
        except Exception as e:
            st.error(f"An error occurred with the database setup: {e}", icon="🚨")
            st.stop()

    def _hash_password(self, password: str) -> bytes:
        """Hashes a password using bcrypt."""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    def check_password(self, password: str, hashed: bytes) -> bool:
        """Verifies a password against a stored hash."""
        return bcrypt.checkpw(password.encode('utf-8'), hashed)

    def add_user(self, username: str, password: str) -> bool:
        """Adds a new user to the database. Returns True on success, False on failure (e.g., user exists)."""
        if self.users_collection.find_one({"username": username}):
            return False # User already exists
        hashed_password = self._hash_password(password)
        self.users_collection.insert_one({
            "username": username,
            "password_hash": hashed_password,
        })
        return True

    def find_user(self, username: str) -> Dict | None:
        """Finds a user by their username."""
        return self.users_collection.find_one({"username": username})

# --- AI & Scraper Class Definitions (Unchanged from your previous code) ---
class LeadIntelligenceEngine:
    """AI-powered lead analysis and scoring engine"""
    def __init__(self):
        try:
            self.model = genai.GenerativeModel('gemini-1.5-flash-latest')
        except Exception as e:
            st.error(f"Failed to initialize Gemini model: {e}.")
            self.model = None
    # ... (Keep all methods inside this class exactly as they were)
    def analyze_company_profile(self, company_data: Dict) -> Dict:
        """Generate comprehensive company analysis using Gemini AI"""
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


class EnhancedWebScraper:
    """Advanced web scraping to extract comprehensive company details."""
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.88 Safari/537.36'
        })
    # ... (Keep all methods inside this class exactly as they were)
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

# --- Main Application Logic ---

# Initialize session state for login status and results
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = ""
if 'analysis_result' not in st.session_state:
    st.session_state.analysis_result = None
if 'scraped_data' not in st.session_state:
    st.session_state.scraped_data = None


# --- Authentication UI (Login/Signup) ---
def authentication_ui():
    db_manager = MongoManager(MONGO_URI)
    
    with st.sidebar:
        st.header(f"Welcome!")
        selected = option_menu(
            menu_title=None,
            options=["Login", "Sign Up"],
            icons=["box-arrow-in-right", "person-plus-fill"],
            default_index=0,
        )

    if selected == "Login":
        st.header("User Login")
        with st.form("login_form"):
            username = st.text_input("Username").lower()
            password = st.text_input("Password", type="password")
            login_button = st.form_submit_button("Login", type="primary")

            if login_button:
                if not username or not password:
                    st.warning("Please enter both username and password.")
                else:
                    user = db_manager.find_user(username)
                    if user and db_manager.check_password(password, user['password_hash']):
                        st.session_state.logged_in = True
                        st.session_state.username = username
                        st.success("Logged in successfully!")
                        st.rerun() # Rerun the script to show the main app
                    else:
                        st.error("Invalid username or password.")

    elif selected == "Sign Up":
        st.header("Create New Account")
        with st.form("signup_form"):
            new_username = st.text_input("Choose a Username").lower()
            new_password = st.text_input("Choose a Password", type="password")
            signup_button = st.form_submit_button("Sign Up", type="primary")

            if signup_button:
                if not new_username or not new_password:
                    st.warning("Please fill out all fields.")
                elif len(new_password) < 6:
                    st.warning("Password must be at least 6 characters long.")
                else:
                    if db_manager.add_user(new_username, new_password):
                        st.success("Account created! You can now log in.")
                    else:
                        st.error("Username already exists. Please choose another one.")


# --- Main Lead Intelligence App UI ---
def main_app():
    st.sidebar.success(f"Logged in as **{st.session_state.username}**")
    if st.sidebar.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.username = ""
        st.rerun()

    st.title("🤖 AI-Powered Lead Intelligence Engine")
    st.markdown("Enter a company website to scrape its data and generate an AI-powered lead score and analysis.")

    with st.form("scrape_form"):
        url_input = st.text_input("Enter Company Website URL:", placeholder="e.g., www.hubspot.com")
        submitted = st.form_submit_button("Analyze Company", type="primary")

    if submitted and url_input:
        scraper = EnhancedWebScraper()
        analyzer = LeadIntelligenceEngine()
        with st.spinner(f"Scraping {url_input}..."):
            st.session_state.scraped_data = scraper.scrape_company_data(url_input)
        if "error" in st.session_state.scraped_data:
            st.error(st.session_state.scraped_data["error"])
        else:
            with st.spinner("🧠 Gemini is analyzing the company profile..."):
                st.session_state.analysis_result = analyzer.analyze_company_profile(st.session_state.scraped_data)
            if "error" in st.session_state.analysis_result:
                st.error(st.session_state.analysis_result["error"])
            else:
                st.success("Analysis complete!")

    # Display results if they exist in the session state
    if st.session_state.analysis_result and "error" not in st.session_state.analysis_result:
        res = st.session_state.analysis_result
        data = st.session_state.scraped_data
        st.markdown("---")
        st.header(f"Analysis for: {data.get('name', 'Unknown Company')}")
        col1, col2, col3 = st.columns(3)
        col1.metric("Lead Score", f"{res.get('lead_score', 0)}/100")
        col2.metric("Priority", res.get('priority', 'N/A'))
        col3.metric("Risk Level", res.get('risk_level', 'N/A'))
        # ... (rest of the display logic is the same)
        st.subheader("AI-Generated Analysis")
        st.markdown("##### **Recommended Approach**")
        st.info(res.get('recommended_approach', 'Not available.'))
        st.markdown("##### **Rationale**")
        st.write(res.get('rationale', 'Not available.'))
        st.markdown("##### **Score Breakdown**")
        breakdown = res.get('score_breakdown', {})
        if breakdown:
            parsed_scores = {k: int(re.match(r'(\d+)', v).group(1)) for k, v in breakdown.items() if re.match(r'(\d+)', v)}
            if parsed_scores:
                df = pd.DataFrame(list(parsed_scores.items()), columns=['Criteria', 'Score'])
                fig = px.bar(df, x='Score', y='Criteria', orientation='h', title="Lead Score by Criteria", text_auto=True)
                fig.update_layout(xaxis_title="Score", yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)
        st.markdown("---")
        st.header("Scraped Company Data")
        with st.expander("🌐 General & Contact Information", expanded=True):
            st.markdown(f"**Company Name:** `{data.get('name')}`")
            st.markdown(f"**Website:** `{data.get('website')}`")
            st.markdown(f"**Industry:** `{data.get('industry')}`")
            st.markdown(f"**Emails:** `{', '.join(data.get('contact_emails')) if data.get('contact_emails') else 'Not Found'}`")
            st.markdown(f"**Phone Numbers:** `{', '.join(data.get('phone_numbers')) if data.get('phone_numbers') else 'Not Found'}`")
            st.markdown(f"**Description:** {data.get('description')}")

# --- App Router ---
if not st.session_state.logged_in:
    authentication_ui()
else:
    main_app()