"""
Resume Optimization Agent

For the current job, generates a tailored, ATS-optimized resume version
by:
  - Retrieving relevant project/experience chunks from the RAG store
  - Re-ordering/rewriting bullet points to emphasize job-relevant skills
  - Estimating an ATS match score (keyword coverage heuristic)
"""
import re
from typing import Dict, Any
from backend.agents.base import BaseAgent
from backend.rag.store import PersonalDocStore

RESUME_PROMPT = """You are the Resume Optimization agent for CareerPilot AI.

Rewrite/tailor the candidate's resume content to maximize relevance for
the target job below. Emphasize matching skills and relevant projects,
use strong action verbs, and naturally incorporate the job's key
terminology for ATS scanning. Keep it truthful - only reorganize and
rephrase existing content, do not invent experience.

Output a clean resume in markdown with sections: Summary, Skills,
Experience, Projects, Education, Certifications.

--- CANDIDATE PROFILE ---
Skills: {skills}
Experience: {experience}
Projects: {projects}
Education: {education}
Certifications: {certifications}

--- RELEVANT CONTEXT FROM PAST DOCUMENTS ---
{rag_context}

--- TARGET JOB ---
Title: {job_title}
Company: {company}
Required skills: {job_skills}
Description: {job_description}
"""


class ResumeOptimizationAgent(BaseAgent):
    name = "resume_optimization"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        profile = state.get("profile", {})
        job = state.get("current_job", {})
        user_id = state.get("user_id")

        if not job:
            return {"logs": ["[resume_optimization] no current_job in state - skipping"]}

        # RAG retrieval for grounding
        rag_context = ""
        try:
            store = PersonalDocStore(user_id=user_id)
            chunks = store.query(
                f"{job.get('title', '')} {' '.join(job.get('required_skills', []))}",
                n_results=4,
            )
            rag_context = "\n---\n".join(chunks)
        except Exception:
            rag_context = ""

        prompt = RESUME_PROMPT.format(
            skills=profile.get("skills", []),
            experience=profile.get("experience", []),
            projects=profile.get("projects", []),
            education=profile.get("education", []),
            certifications=profile.get("certifications", []),
            rag_context=rag_context or "N/A",
            job_title=job.get("title", ""),
            company=job.get("company", ""),
            job_skills=job.get("required_skills", []),
            job_description=job.get("description", "")[:2000],
        )

        tailored_resume = self.invoke_llm(prompt)
        ats_score = self._estimate_ats_score(tailored_resume, job.get("required_skills", []))

        return {
            "tailored_resume": tailored_resume,
            "scratch": {"ats_score": ats_score},
            "logs": [f"[resume_optimization] completed: tailored resume generated (ATS score ~{ats_score})"],
        }

    @staticmethod
    def _estimate_ats_score(resume_text: str, required_skills: list) -> float:
        if not required_skills:
            return 75.0
        resume_lower = resume_text.lower()
        hits = sum(1 for s in required_skills if re.search(re.escape(s.lower()), resume_lower))
        return round(100 * hits / len(required_skills), 1)
