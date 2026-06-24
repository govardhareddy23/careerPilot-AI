"""
Salary Intelligence Agent

Analyzes market salary data for the current job's role/location/experience
level and provides salary negotiation suggestions.

Note: real implementation would call a salary-data MCP tool (e.g. wrapping
Levels.fyi, Glassdoor, PayScale APIs). Here the LLM provides estimates
based on general market knowledge, clearly framed as estimates.
"""
from typing import Dict, Any
from backend.agents.base import BaseAgent

SALARY_PROMPT = """You are the Salary Intelligence agent for CareerPilot AI.

For the job below, provide:
1. An estimated market salary range for this role, location, and experience
   level (clearly state these are general estimates, not live data)
2. How the job's posted salary range (if any) compares to that estimate
3. 3-4 specific, actionable salary negotiation talking points the candidate
   could use, tailored to their profile strengths

JOB TITLE: {job_title}
COMPANY: {company}
LOCATION: {location}
POSTED SALARY RANGE: {salary_range}
CANDIDATE YEARS OF EXPERIENCE (estimate): {years_exp}
CANDIDATE KEY STRENGTHS: {strengths}

Output as concise markdown.
"""


class SalaryIntelligenceAgent(BaseAgent):
    name = "salary_intelligence"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        job = state.get("current_job", {})
        profile = state.get("profile", {})

        if not job:
            return {"logs": ["[salary_intelligence] no current_job in state - skipping"]}

        years_exp = len(profile.get("experience", [])) * 1.5
        strengths = (profile.get("skills", []) + profile.get("achievements", []))[:8]

        prompt = SALARY_PROMPT.format(
            job_title=job.get("title", ""),
            company=job.get("company", ""),
            location=job.get("location", ""),
            salary_range=job.get("salary_range", "Not posted"),
            years_exp=years_exp,
            strengths=strengths,
        )
        analysis = self.invoke_llm(prompt)

        return {
            "scratch": {"salary_analysis": analysis},
            "logs": ["[salary_intelligence] completed: salary analysis and negotiation tips generated"],
        }
