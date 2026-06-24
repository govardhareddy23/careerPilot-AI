"""
Interview Preparation Agent

For shortlisted/interview-stage jobs, generates:
  - Company research summary
  - Technical interview questions
  - Behavioral questions
  - DSA roadmap (for SWE roles)
  - Mock interview session notes/script
"""
import json
from typing import Dict, Any
from backend.agents.base import BaseAgent
from backend.db.session import SessionLocal
from backend.db.models import InterviewPrep

PREP_PROMPT = """You are the Interview Preparation agent for CareerPilot AI.

For the job below, generate interview prep material. Respond with ONLY
valid JSON in this exact format:

{{
  "company_research": "2-3 paragraph summary of likely company focus, culture, and recent direction based on the job description",
  "technical_questions": ["list of 6-8 likely technical questions"],
  "behavioral_questions": ["list of 5 behavioral/STAR-format questions"],
  "dsa_roadmap": ["list of 5-8 DSA topics to review, ordered by priority"],
  "mock_session_notes": "a short mock interview opening script the candidate can practice with"
}}

JOB TITLE: {job_title}
COMPANY: {company}
REQUIRED SKILLS: {required_skills}
DESCRIPTION: {description}

CANDIDATE SKILLS: {candidate_skills}
SKILL GAPS: {skill_gaps}
"""


class InterviewPrepAgent(BaseAgent):
    name = "interview_prep"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        job = state.get("current_job", {})
        profile = state.get("profile", {})
        skill_gap = state.get("skill_gap", {})

        if not job:
            return {"logs": ["[interview_prep] no current_job in state - skipping"]}

        prompt = PREP_PROMPT.format(
            job_title=job.get("title", ""),
            company=job.get("company", ""),
            required_skills=job.get("required_skills", []),
            description=job.get("description", "")[:1500],
            candidate_skills=profile.get("skills", []),
            skill_gaps=skill_gap.get("missing_skills", []),
        )
        raw = self.invoke_llm(prompt).strip()
        if raw.startswith("```"):
            raw = raw.strip("`").replace("json", "", 1).strip()

        try:
            prep_data = json.loads(raw)
        except json.JSONDecodeError:
            prep_data = {
                "company_research": raw[:1000], "technical_questions": [],
                "behavioral_questions": [], "dsa_roadmap": [], "mock_session_notes": "",
            }

        if job.get("id"):
            db = SessionLocal()
            try:
                db.add(InterviewPrep(
                    job_id=job["id"],
                    company_research=prep_data.get("company_research", ""),
                    technical_questions=prep_data.get("technical_questions", []),
                    behavioral_questions=prep_data.get("behavioral_questions", []),
                    dsa_roadmap=prep_data.get("dsa_roadmap", []),
                    mock_session_notes=prep_data.get("mock_session_notes", ""),
                ))
                db.commit()
            finally:
                db.close()

        return {
            "scratch": {"interview_prep": prep_data},
            "logs": ["[interview_prep] completed: interview prep material generated"],
        }
