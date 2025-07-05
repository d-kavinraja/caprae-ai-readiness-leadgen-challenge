# services.py

import streamlit as st
import requests
from bs4 import BeautifulSoup
import re
import json
from urllib.parse import urljoin, urlparse
import google.generativeai as genai
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import random
from typing import List, Dict

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

class LeadIntelligenceEngine:
    def __init__(self):
        try:
            self.model = genai.GenerativeModel('gemini-pro')
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