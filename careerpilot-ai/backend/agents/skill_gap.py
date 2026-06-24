"""
Skill Gap Agent

Compares the current job's requirements against the user's profile and
identifies missing skills, certifications, and technologies. Generates
prioritized learning recommendations (courses, docs, projects).
"""
import json
from typing import Dict, Any
from backend.agents.base import BaseAgent
from backend.db.session import SessionLocal
from backend.db.models import SkillGap

GAP_PROMPT = """You are the Skill Gap agent for CareerPilot AI.

Compare the candidate's profile against the job requirements below and
identify gaps. Respond with ONLY valid JSON in this exact format:

{{
  "missing_skills": ["..."],
  "missing_certifications": ["..."],
  "missing_technologies": ["..."],
  "learning_recommendations": [
    {{"resource": "name/title of resource", "type": "course|doc|project|cert", "priority": "high|medium|low"}}
  ]
}}

CANDIDATE SKILLS: {candidate_skills}
CANDIDATE CERTIFICATIONS: {candidate_certs}

JOB TITLE: {job_title}
JOB REQUIRED SKILLS: {job_skills}
JOB DESCRIPTION: {job_description}
"""


class SkillGapAgent(BaseAgent):
    name = "skill_gap"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        profile = state.get("profile", {})
        job = state.get("current_job", {})

        if not job:
            return {"logs": ["[skill_gap] no current_job in state - skipping"]}

        prompt = GAP_PROMPT.format(
            candidate_skills=profile.get("skills", []),
            candidate_certs=profile.get("certifications", []),
            job_title=job.get("title", ""),
            job_skills=job.get("required_skills", []),
            job_description=job.get("description", "")[:2000],
        )
        raw = self.invoke_llm(prompt).strip()
        if raw.startswith("```"):
            raw = raw.strip("`").replace("json", "", 1).strip()

        try:
            gap_data = json.loads(raw)
        except json.JSONDecodeError:
            gap_data = {
                "missing_skills": [], "missing_certifications": [],
                "missing_technologies": [], "learning_recommendations": [],
            }

        # persist
        if job.get("id"):
            db = SessionLocal()
            try:
                gap_row = SkillGap(
                    job_id=job["id"],
                    missing_skills=gap_data.get("missing_skills", []),
                    missing_certifications=gap_data.get("missing_certifications", []),
                    missing_technologies=gap_data.get("missing_technologies", []),
                    learning_recommendations=gap_data.get("learning_recommendations", []),
                )
                db.add(gap_row)
                db.commit()
            finally:
                db.close()

        return {
            "skill_gap": gap_data,
            "logs": [
                f"[skill_gap] completed: {len(gap_data.get('missing_skills', []))} missing skills identified"
            ],
        }
