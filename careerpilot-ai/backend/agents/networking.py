"""
Networking Agent

Identifies likely recruiters, hiring managers, alumni, and relevant
professionals at the target company, and generates personalized
outreach messages for each persona.

Note: Real implementation would use LinkedIn Sales Navigator API / People
Search MCP tool. Here we generate persona-targeted message templates that
the user can send once they identify the actual people (e.g. via LinkedIn
search), keeping the human firmly in control of actual outreach.
"""
from typing import Dict, Any
from backend.agents.base import BaseAgent

NETWORKING_PROMPT = """You are the Networking agent for CareerPilot AI.

For the candidate applying to {job_title} at {company}, generate:

1. A LinkedIn search strategy: what job titles/keywords to search for to find
   recruiters, hiring managers, and alumni at {company} (list 4-6 search terms)
2. A personalized message template for a RECRUITER at the company
3. A personalized message template for a HIRING MANAGER / team lead
4. A personalized message template for an ALUMNI connection (someone from
   the candidate's school/previous company who now works at {company})

Each message should be 2-4 sentences, reference the specific role, and
include a placeholder like [Name] for personalization.

CANDIDATE BACKGROUND: {background}

Output as markdown with clear headers for each of the 4 items.
"""


class NetworkingAgent(BaseAgent):
    name = "networking"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        job = state.get("current_job", {})
        profile = state.get("profile", {})

        if not job:
            return {"logs": ["[networking] no current_job in state - skipping"]}

        background = f"Skills: {profile.get('skills', [])[:10]}, " \
                      f"Education: {profile.get('education', [])}"

        prompt = NETWORKING_PROMPT.format(
            job_title=job.get("title", ""),
            company=job.get("company", ""),
            background=background,
        )
        networking_content = self.invoke_llm(prompt)

        return {
            "scratch": {"networking_plan": networking_content},
            "logs": ["[networking] completed: networking strategy and message templates generated"],
        }
