"""
Learning Agent

Implements the reflection / self-improvement loop:
- Analyzes rejections and any recorded interview feedback
- Cross-references with skill gaps already identified
- Produces updated recommendations to improve future match scores
  (e.g. "you've been rejected from 3 roles requiring Kubernetes -
  prioritize learning it")

This agent's output can feed back into the user's profile preferences
or be surfaced in the dashboard, closing the agentic feedback loop.
"""
import json
from collections import Counter
from typing import Dict, Any
from backend.agents.base import BaseAgent
from backend.db.session import SessionLocal
from backend.db.models import Job, SkillGap

REFLECTION_PROMPT = """You are the Learning agent for CareerPilot AI,
responsible for the reflection / self-improvement loop.

The candidate has been rejected from the following jobs. Each rejection
includes the skill gaps identified at the time of application.

REJECTED JOBS & SKILL GAPS:
{rejection_data}

Based on patterns across these rejections, provide:
1. The top 3 recurring missing skills/technologies (ranked by frequency)
2. A revised prioritized learning plan (3-5 items) to address these gaps
3. One suggestion for adjusting the job search strategy (e.g. target
   different seniority levels, locations, or role types) if patterns
   suggest a mismatch

Output as concise markdown.
"""


class LearningAgent(BaseAgent):
    name = "learning"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        user_id = state.get("user_id")

        db = SessionLocal()
        try:
            rejected_jobs = db.query(Job).filter(
                Job.user_id == user_id, Job.status == "rejected"
            ).all()

            if not rejected_jobs:
                return {"logs": ["[learning] no rejected jobs yet - nothing to learn from"]}

            rejection_data = []
            all_missing_skills = []
            for job in rejected_jobs:
                gaps = db.query(SkillGap).filter(SkillGap.job_id == job.id).all()
                missing = []
                for g in gaps:
                    missing.extend(g.missing_skills or [])
                    all_missing_skills.extend(g.missing_skills or [])
                rejection_data.append({
                    "title": job.title, "company": job.company, "missing_skills": missing,
                })
        finally:
            db.close()

        prompt = REFLECTION_PROMPT.format(rejection_data=json.dumps(rejection_data, indent=2)[:3000])
        reflection = self.invoke_llm(prompt)

        skill_freq = Counter(s.lower() for s in all_missing_skills)
        top_skills = skill_freq.most_common(5)

        return {
            "scratch": {
                "learning_reflection": reflection,
                "top_recurring_skill_gaps": top_skills,
            },
            "logs": [f"[learning] completed: analyzed {len(rejected_jobs)} rejections, "
                     f"identified {len(top_skills)} recurring skill gaps"],
        }
