import os
import json
import time  # Added for rate limiting
import requests
from google import genai
from google.genai import types
from pydantic import BaseModel, Field
from typing import List, Optional

# =====================================================================
# CONFIGURATION & API KEYS
# =====================================================================
GEMINI_API_KEY = "your-actual-gemini-key"
ADZUNA_APP_ID = "your-actual-adzuna-id"
ADZUNA_APP_KEY = "your-actual-adzuna-key"

SEARCH_ROLES = [
    "Platform Architect", 
    "DevOps Architect", 
    "Senior Platform Engineer", 
    "Solutions Architect",
    "Release Engineer",
    "Cloud Operations Engineer",
    "DevOps Engineer"
]
LOCATION = "us" 

client = genai.Client(api_key=GEMINI_API_KEY)

# =====================================================================
# DATA STRUCTURES
# =====================================================================
class JobEvaluation(BaseModel):
    match_score: int = Field(..., description="A score from 1 to 10 evaluating alignment with Senior Infrastructure/Cloud roles.")
    key_matches: List[str] = Field(..., description="List of technologies found that match (e.g., Kubernetes, Terraform, CI/CD).")
    missing_critical_skills: List[str] = Field(..., description="Important skills required for this role that aren't core infrastructure skills.")
    verdict_summary: str = Field(..., description="A 2-sentence summary explaining why this job is or isn't a good match.")

# =====================================================================
# LIVE SEARCH TOOL
# =====================================================================
def fetch_jobs(query: str, country: str = "us", max_results: int = 10) -> list:
    url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
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
        else:
            print(f"Error fetching data from Adzuna: {response.status_code}")
            return []
    except Exception as e:
        print(f"API connection failed: {e}")
        return []

# =====================================================================
# AI EVALUATION AGENT
# =====================================================================
def analyze_job_description(title: str, description: str) -> Optional[JobEvaluation]:
    system_instruction = (
        "You are an expert technical recruiter matching elite candidates to Senior Platform Engineering "
        "and Cloud/DevOps Architect roles. Evaluate the job description against a profile with the following strict criteria:\n\n"
        "1. Core Tooling: Deep expertise in Kubernetes (CKA preferred), Terraform (IaC), Docker, Containerd, "
        "and enterprise CI/CD pipelines (Jenkins, Concourse CI, GitHub Administration).\n"
        "2. Cloud Infrastructure: Multi-cloud architecture across AWS (Solutions Architect Associate), "
        "Google Cloud (Professional Cloud Architect), and Azure (AZ-305).\n"
        "3. Observability & Management: Splunk, Jira platform administration, and Linux system engineering.\n"
        "4. Industry Context: Prioritize complex, highly-regulated environments (Healthcare, Banking, Finance, Telecommunications) "
        "requiring DevSecOps, RBAC, and strict security compliance frameworks.\n\n"
        "Assign a score from 1 to 10. Be uncompromising. Rate a job 8 or higher only if it genuinely demands "
        "high-level architecture, infrastructure automation, or systems optimization."
    )
    
    prompt = f"Analyze this job posting:\nTitle: {title}\nDescription: {description}\n\nProvide the structured evaluation."
    
    try:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_schema=JobEvaluation,
            ),
        )
        data = json.loads(response.text)
        return JobEvaluation(**data)
    except Exception as e:
        # Check specifically for rate limiting to warn the user
        if "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
            print(f"⚠️ Hit API Rate Limit limit. Pacing execution...")
        else:
            print(f"AI Evaluation failed for {title}: {e}")
        return None

# =====================================================================
# ORCHESTRATION PIPELINE
# =====================================================================
def run_job_hunting_agent():
    print("🚀 Initializing AI Job Hunter Agent...")
    curated_leads = []
    
    for role in SEARCH_ROLES:
        print(f"\n🔍 Scanning market for Remote: '{role}'...")
        raw_listings = fetch_jobs(query=role, max_results=20)
        
        if not raw_listings:
            continue
            
        print(f"Found {len(raw_listings)} listings. Handing off to AI Agent for vetting...")
        
        for job in raw_listings:
            title = job.get('title', 'Unknown Title')
            company = job.get('company', {}).get('display_name', 'Unknown Company')
            desc = job.get('description', '')
            link = job.get('redirect_url', '#')
            
            clean_desc = "".join([c for c in desc if ord(c) < 128]) 
            
            evaluation = analyze_job_description(title, clean_desc)
            
            if evaluation:
                if evaluation.match_score >= 7:
                    curated_leads.append({
                        "title": title,
                        "company": company,
                        "score": evaluation.match_score,
                        "matches": evaluation.key_matches,
                        "summary": evaluation.verdict_summary,
                        "link": link
                    })
                    print(f"  ✅ MATCH FOUND: {title} at {company} (Score: {evaluation.match_score}/10)")
                else:
                    print(f"  ❌ Skipped: {title} (Score: {evaluation.match_score}/10)")
                    print(f"     Reason: {evaluation.verdict_summary}")
            

    print("\n" + "="*50)
    print("     🎯 DAILY HIGH-VALUE JOB RECRUITING REPORT")
    print("="*50)
    
    if not curated_leads:
        print("No high-alignment roles discovered today.")
    else:
        curated_leads.sort(key=lambda x: x['score'], reverse=True)
        for i, lead in enumerate(curated_leads, 1):
            print(f"\n[{i}] {lead['title']} - {lead['company']}")
            print(f"    Match Rating: {lead['score']}/10")
            print(f"    Core Tech Aligned: {', '.join(lead['matches'])}")
            print(f"    AI Evaluation: {lead['summary']}")
            print(f"    Apply Here: {lead['link']}")
            print("-" * 40)

if __name__ == "__main__":
    run_job_hunting_agent()      
