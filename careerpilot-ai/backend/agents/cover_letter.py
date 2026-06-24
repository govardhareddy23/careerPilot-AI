"""
Cover Letter Agent

Generates a tailored cover letter plus short-form recruiter outreach,
networking, and referral request messages for the current job.
"""
from typing import Dict, Any
from backend.agents.base import BaseAgent

COVER_LETTER_PROMPT = """You are the Cover Letter agent for CareerPilot AI.

Write a concise, compelling, and personalized cover letter (under 350 words)
for the candidate applying to the role below. Reference 1-2 specific
projects/experiences from their profile that align with the job. Avoid
generic filler phrases. Professional but warm tone.

CANDIDATE NAME: {name}
CANDIDATE SKILLS: {skills}
CANDIDATE EXPERIENCE: {experience}
CANDIDATE PROJECTS: {projects}

TARGET JOB: {job_title} at {company}
JOB DESCRIPTION: {job_description}

Output ONLY the cover letter text.
"""

OUTREACH_PROMPT = """You are the Cover Letter agent for CareerPilot AI, also
responsible for short networking/outreach messages.

Generate three short messages (2-4 sentences each) for the candidate
applying to {job_title} at {company}:

1. A recruiter outreach message (LinkedIn-style, friendly, direct)
2. A referral request message (to a connection at the company)
3. A general networking message (to someone in a similar role at the company)

Format as:
RECRUITER: ...
REFERRAL: ...
NETWORKING: ...
"""


class CoverLetterAgent(BaseAgent):
    name = "cover_letter"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        profile = state.get("profile", {})
        job = state.get("current_job", {})

        if not job:
            return {"logs": ["[cover_letter] no current_job in state - skipping"]}

        cl_prompt = COVER_LETTER_PROMPT.format(
            name=profile.get("name", "Candidate"),
            skills=profile.get("skills", []),
            experience=profile.get("experience", []),
            projects=profile.get("projects", []),
            job_title=job.get("title", ""),
            company=job.get("company", ""),
            job_description=job.get("description", "")[:1500],
        )
        cover_letter = self.invoke_llm(cl_prompt)

        outreach_prompt = OUTREACH_PROMPT.format(
            job_title=job.get("title", ""), company=job.get("company", "")
        )
        outreach_message = self.invoke_llm(outreach_prompt)

        return {
            "cover_letter": cover_letter,
            "outreach_message": outreach_message,
            "logs": ["[cover_letter] completed: cover letter and outreach messages generated"],
        }
