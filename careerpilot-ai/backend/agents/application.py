"""
Application Agent

Prepares the final application package (tailored resume + cover letter +
outreach message + recommended application method) for the current job
and persists it as a pending Application record.

CRITICAL SAFETY REQUIREMENT: This agent NEVER submits an application.
It always sets `requires_approval=True` and `approval_status="pending"`,
halting the LangGraph workflow at a human-in-the-loop checkpoint. The
actual "apply" action is performed only via an explicit API call
(`POST /applications/{id}/approve`) triggered by the user, which marks
the Application as approved/applied - the agent itself stops here.

Flow:
  Discover Job -> Score Job -> Optimize Resume -> Generate Cover Letter
  -> [THIS AGENT: package + request approval] -> (user approves via UI/API)
  -> Apply (external, manual or user-triggered)
"""
from typing import Dict, Any
from backend.agents.base import BaseAgent
from backend.db.session import SessionLocal
from backend.db.models import Application, Job


class ApplicationAgent(BaseAgent):
    name = "application"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        job = state.get("current_job", {})
        user_id = state.get("user_id")

        if not job or not job.get("id"):
            return {"logs": ["[application] no current_job in state - skipping"]}

        tailored_resume = state.get("tailored_resume", "")
        cover_letter = state.get("cover_letter", "")
        outreach_message = state.get("outreach_message", "")
        ats_score = state.get("scratch", {}).get("ats_score", 0.0)

        application_method = self._recommend_method(job)

        db = SessionLocal()
        try:
            existing = db.query(Application).filter(Application.job_id == job["id"]).first()
            if existing:
                app_row = existing
            else:
                app_row = Application(job_id=job["id"], user_id=user_id)
                db.add(app_row)

            app_row.tailored_resume = tailored_resume
            app_row.ats_score = ats_score
            app_row.cover_letter = cover_letter
            app_row.outreach_message = outreach_message
            app_row.approval_status = "pending"
            app_row.application_method = application_method
            db.commit()
            db.refresh(app_row)

            job_row = db.query(Job).filter(Job.id == job["id"]).first()
            if job_row:
                job_row.status = "awaiting_approval"
                db.commit()

            app_id = app_row.id
        finally:
            db.close()

        approval_payload = {
            "application_id": app_id,
            "job_title": job.get("title"),
            "company": job.get("company"),
            "match_score": job.get("match_score"),
            "ats_score": ats_score,
            "application_method": application_method,
            "preview_resume": tailored_resume[:500],
            "preview_cover_letter": cover_letter[:500],
        }

        return {
            "requires_approval": True,
            "approval_status": "pending",
            "approval_payload": approval_payload,
            "logs": [
                f"[application] completed: application package prepared for "
                f"'{job.get('title')}' at {job.get('company')} - "
                f"AWAITING HUMAN APPROVAL (application_id={app_id}). "
                f"No application was submitted automatically."
            ],
        }

    @staticmethod
    def _recommend_method(job: Dict[str, Any]) -> str:
        """
        Maps a job's source/publisher to a recommended application method.

        Real job-board APIs (JSearch) return varied, sometimes compound
        publisher strings (e.g. "LinkedIn", "via Indeed", "ZipRecruiter"),
        not the fixed lowercase labels the old mock data used. We match
        by substring rather than exact equality so this stays robust
        against real-world publisher name variation.
        """
        source = (job.get("source") or "").lower()
        easy_apply_publishers = ("linkedin", "wellfound", "ziprecruiter")
        portal_publishers = ("indeed", "naukri", "internshala", "glassdoor", "monster")

        if any(p in source for p in easy_apply_publishers):
            return "easy_apply"
        if any(p in source for p in portal_publishers):
            return "company_portal"
        return "email"
