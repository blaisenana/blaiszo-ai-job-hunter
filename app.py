import streamlit as st
from google import genai
import requests
from pypdf import PdfReader

# 1. Initialization and Secrets Management
GEMINI_API_KEY = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=GEMINI_API_KEY)

ADZUNA_APP_ID = st.secrets["ADZUNA_APP_ID"]
ADZUNA_APP_KEY = st.secrets["ADZUNA_APP_KEY"]

# 2. Adzuna Job Fetching Logic
def fetch_jobs(query, max_results=5):
    url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
    params = {
        "app_id": ADZUNA_APP_ID,
        "app_key": ADZUNA_APP_KEY,
        "results_per_page": max_results,
        "what": f"{query} remote",
        "sort_by": "date",
        "max_days_old": 1,
        "content-type": "application/json"
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json().get('results', [])
    except Exception:
        return []
    return []

# 3. Gemini AI Engine
def generate_response(prompt):
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt
        )
        return response.text
    except Exception as e:
        return f"Error: {e}"

# 4. Streamlit UI Layout
st.set_page_config(page_title="AI Job Hunter", page_icon="🎯")
st.title("🎯 AI-Powered Job Hunter Marketplace")

user_email = st.text_input("📧 Your Email Address")
target_role = st.text_input("🔍 Target Job Title")

# File Upload Handling
resume_option = st.radio("Resume Submission", ("Upload File (PDF / TXT)", "Paste Text"))
user_resume_text = ""

if resume_option == "Upload File (PDF / TXT)":
    uploaded_file = st.file_uploader("Upload your resume file", type=["pdf", "txt"])
    if uploaded_file is not None:
        if uploaded_file.name.endswith(".txt"):
            user_resume_text = uploaded_file.read().decode("utf-8")
        elif uploaded_file.name.endswith(".pdf"):
            pdf_reader = PdfReader(uploaded_file)
            user_resume_text = "\n".join([page.extract_text() for page in pdf_reader.pages])
else:
    user_resume_text = st.text_area("Paste Your Resume Text Here", height=250)

# Execution
if st.button("🚀 Activate My AI Job Agent"):
    if user_email and target_role and user_resume_text:
        listings = fetch_jobs(target_role)
        for job in listings:
            title = job.get('title', 'Unknown')
            company = job.get('company', {}).get('display_name', 'Unknown')
            desc = job.get('description', '')
            link = job.get('redirect_url', '#')
            
            # Job Evaluation
            eval_prompt = f"Grade this job: {desc} against resume: {user_resume_text}. Score 1-10 and explain."
            ai_verdict = generate_response(eval_prompt)
            
            with st.expander(f"💼 {title} — {company}"):
                st.write(f"**AI Evaluation:**\n{ai_verdict}")
                st.markdown(f"[🔗 Apply Here]({link})")
                
                # --- PREMIUM COVER LETTER FEATURE ---
                if st.button(f"✨ Generate Cover Letter for {title}", key=f"btn_{title}"):
                    cl_prompt = f"Write a professional cover letter for the role {title} at {company} using this resume: {user_resume_text}"
                    cover_letter = generate_response(cl_prompt)
                    st.text_area("Your Cover Letter:", value=cover_letter, height=300)
