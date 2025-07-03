# 🧠 Caprae AI Readiness LeadGen Challenge

An AI-Powered Lead Intelligence Engine that scrapes, analyzes, and scores company profiles using Google's **Gemini LLM**, advanced web scraping, and secure user authentication.

🔗 [Live App on Streamlit](https://caprae-ai-readiness-leadgen-challenge.streamlit.app/)  
📁 [GitHub Repository](https://github.com/d-kavinraja/caprae-ai-readiness-leadgen-challenge)

---

## 📌 Project Overview

The Lead Intelligence Engine empowers users to input a company website URL and instantly retrieve:

- Contact info (emails, phone numbers)
- Tech stack
- Social presence
- Team size & funding stage

This data is then analyzed by a **Gemini-powered AI model**, which returns:

- ✅ Lead Score (0–100)
- 🏷️ Priority & Risk Level
- 🧠 Rationale & Suggested Outreach

---

## 🔧 Features

- 🔐 User Authentication (MongoDB + bcrypt)
- 🧽 Clean Web Scraping (BeautifulSoup)
- 🧠 Gemini 1.5 Flash API Integration
- 📊 Interactive Score Breakdown (Plotly)
- 🚀 Streamlit-based Frontend
- 🔒 Secrets Management using `st.secrets` (safe for Streamlit Cloud)

---

## 🖼️ Demo Screenshots

| Login Page | Lead Analysis |
|------------|----------------|
| ![Login](https://github.com/user-attachments/assets/d0307e26-dda9-4fe2-a15a-52724f401bd2)| ![Analysis](https://github.com/user-attachments/assets/582753a9-4fb9-4646-8768-000480b11f9a)


---

## 🛠️ Tech Stack

| Layer         | Technology                             |
|--------------|-----------------------------------------|
| Frontend     | Streamlit, Plotly, Option Menu          |
| Backend      | Python, Regex, BeautifulSoup            |
| LLM Engine   | Gemini 1.5 Flash via Google Generative AI API |
| Database     | MongoDB Atlas                           |
| Auth         | bcrypt password hashing                 |
| Hosting      | Streamlit Community Cloud               |

---

## 🔐 Setting Up Secrets in Streamlit Cloud

1. Go to your deployed Streamlit app.
2. Navigate to **Settings → Secrets**.
3. Add the following:

```toml
GEMINI_API_KEY = "your_gemini_api_key"
MONGO_URI = "your_mongodb_connection_string"
HASH_SECRET_KEY = "your_custom_secret"
```
## 🚀 Running Locally
1. Clone the repository
```
git clone https://github.com/d-kavinraja/caprae-ai-readiness-leadgen-challenge.git
cd caprae-ai-readiness-leadgen-challenge
```

2. Create a local .streamlit/secrets.toml file
```
 .streamlit/secrets.toml
GEMINI_API_KEY = "your_gemini_api_key"
MONGO_URI = "your_mongodb_connection_string"
HASH_SECRET_KEY = "your_secret_key"
```

3. Install dependencies
```
pip install -r requirements.txt
```
4. Run the app
```
streamlit run app.py
```
## 📈 How It Works

    1. User logs in or signs up (data stored in MongoDB Atlas).

    2. User enters a company URL.

    3. EnhancedWebScraper fetches: Name, description, technologies, emails, phones, social links, etc.

    4. LeadIntelligenceEngine prompts Gemini API to generate:

        Lead score (0–100)

        Score breakdown

        Risk level & outreach suggestion

    5. Streamlit UI visualizes everything using Plotly & metrics.


