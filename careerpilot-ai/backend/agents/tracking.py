"""
Tracking Agent

Updates and reports on application tracking status:
saved -> applied -> assessment -> interview -> offer -> rejected.

Provides dashboard analytics (counts per status, conversion rates).
"""
from typing import Dict, Any
from collections import Counter
from backend.agents.base import BaseAgent
from backend.db.session import SessionLocal
from backend.db.models import Job, TrackingEvent


class TrackingAgent(BaseAgent):
    name = "tracking"

    VALID_STATUSES = [
        "discovered", "scored", "resume_ready", "awaiting_approval",
        "approved", "applied", "assessment", "interview", "offer", "rejected",
    ]

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        user_id = state.get("user_id")
        job = state.get("current_job", {})
        new_status = state.get("scratch", {}).get("new_status")

        db = SessionLocal()
        try:
            # If a status update was requested for the current job, apply it.
            if job.get("id") and new_status in self.VALID_STATUSES:
                job_row = db.query(Job).filter(Job.id == job["id"]).first()
                if job_row:
                    job_row.status = new_status
                    db.add(TrackingEvent(job_id=job_row.id, status=new_status,
                                          note=f"Updated via tracking agent"))
                    db.commit()

            # Build dashboard analytics for the user
            jobs = db.query(Job).filter(Job.user_id == user_id).all()
            status_counts = Counter(j.status for j in jobs)
            total = len(jobs)
            applied_count = sum(status_counts.get(s, 0) for s in
                                 ["applied", "assessment", "interview", "offer", "rejected"])
            interview_count = sum(status_counts.get(s, 0) for s in ["interview", "offer"])
            conversion_rate = round(100 * interview_count / applied_count, 1) if applied_count else 0.0

            analytics = {
                "total_jobs": total,
                "status_breakdown": dict(status_counts),
                "applied_count": applied_count,
                "interview_count": interview_count,
                "application_to_interview_rate": conversion_rate,
            }
        finally:
            db.close()

        return {
            "scratch": {"analytics": analytics},
            "logs": [f"[tracking] completed: dashboard analytics computed ({total} total jobs)"],
        }
