"""
CareerPilot AI - FastAPI Backend

Exposes REST endpoints for:
  - Profile management (create/update profile, upload resume)
  - Running the agentic LangGraph workflow (with human-in-the-loop support)
  - Approving/rejecting prepared applications
  - Job listing & tracking dashboard
  - Manual agent triggers (e.g. notification, learning)

Run with: uvicorn backend.api.main:app --reload
"""
import uuid
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session

from backend.db.session import get_db, init_db, SessionLocal
from backend.db.models import UserProfile, Job, Application, TrackingEvent
from backend.api.schemas import (
    ProfileCreate, ProfileResponse, RunRequest, RunResponse,
    ApprovalDecision, JobResponse, TrackingUpdateRequest,
)
from backend.core.graph import get_graph
from backend.utils.resume_parser import extract_text

app = FastAPI(title="CareerPilot AI", version="1.0.0")


@app.on_event("startup")
def on_startup():
    init_db()


# ---------------------------------------------------------------------
# Profile endpoints
# ---------------------------------------------------------------------

@app.post("/profiles", response_model=ProfileResponse)
def create_profile(payload: ProfileCreate, db: Session = Depends(get_db)):
    existing = db.query(UserProfile).filter(UserProfile.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Profile with this email already exists")

    profile = UserProfile(**payload.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@app.get("/profiles/{user_id}", response_model=ProfileResponse)
def get_profile(user_id: int, db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@app.post("/profiles/{user_id}/resume")
async def upload_resume(user_id: int, file: UploadFile = File(...), db: Session = Depends(get_db)):
    profile = db.query(UserProfile).filter(UserProfile.id == user_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    content = await file.read()
    text = extract_text(file.filename, content)
    profile.resume_text = text
    db.commit()
    return {"message": "Resume uploaded", "char_count": len(text)}


# ---------------------------------------------------------------------
# Agentic workflow endpoints
# ---------------------------------------------------------------------

@app.post("/run", response_model=RunResponse)
def run_workflow(payload: RunRequest):
    """
    Kick off (or continue) the CareerPilot agentic workflow for a user.

    A new `thread_id` is generated per logical session. The LangGraph
    checkpointer persists state under this thread, so subsequent calls
    with the same thread_id (e.g. resuming after approval) continue
    from where the graph left off.
    """
    thread_id = str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}

    initial_state = {
        "user_id": payload.user_id,
        "task": payload.task,
        "messages": [{"role": "user", "content": payload.task}],
        "logs": [],
        "completed_agents": [],
        "step_count": 0,
        "requires_approval": False,
        "approval_status": "none",
        "scratch": {},
    }

    final_state = get_graph().invoke(initial_state, config=config)

    return RunResponse(thread_id=thread_id, state=_serialize_state(final_state))


@app.post("/run/{thread_id}/resume", response_model=RunResponse)
def resume_workflow(thread_id: str, payload: RunRequest):
    """Resume a paused workflow (e.g. after human approval) using the same thread_id."""
    config = {"configurable": {"thread_id": thread_id}, "recursion_limit": 50}

    update = {
        "task": payload.task,
        "messages": [{"role": "user", "content": payload.task}],
    }
    final_state = get_graph().invoke(update, config=config)
    return RunResponse(thread_id=thread_id, state=_serialize_state(final_state))


def _serialize_state(state: dict) -> dict:
    """Trim large fields for API responses (full text still in DB)."""
    safe = dict(state)
    for key in ("tailored_resume", "cover_letter", "outreach_message"):
        if safe.get(key):
            safe[key] = safe[key][:1000] + ("..." if len(safe[key]) > 1000 else "")
    return safe


# ---------------------------------------------------------------------
# Human-in-the-loop approval endpoints
# ---------------------------------------------------------------------

@app.post("/applications/{application_id}/decision")
def decide_application(application_id: int, payload: ApprovalDecision, db: Session = Depends(get_db)):
    """
    Approve or reject a prepared application package.

    NOTE: Approving here does NOT auto-submit the application to the job
    board. It marks the package as approved, after which the user
    performs the actual submission themselves (Easy Apply / portal /
    email), then can update job status to 'applied' via the tracking
    endpoint. This preserves the "never apply automatically" guarantee.
    """
    app_row = db.query(Application).filter(Application.id == application_id).first()
    if not app_row:
        raise HTTPException(status_code=404, detail="Application not found")

    app_row.approval_status = "approved" if payload.approve else "rejected"
    db.commit()

    job = db.query(Job).filter(Job.id == app_row.job_id).first()
    if job:
        job.status = "approved" if payload.approve else "rejected"
        db.add(TrackingEvent(job_id=job.id, status=job.status, note=payload.note))
        db.commit()

    return {
        "application_id": application_id,
        "approval_status": app_row.approval_status,
        "message": (
            "Application approved. Please submit it manually via the "
            f"recommended method: {app_row.application_method}."
            if payload.approve else
            "Application rejected and job marked as rejected."
        ),
    }


# ---------------------------------------------------------------------
# Jobs & tracking dashboard
# ---------------------------------------------------------------------

@app.get("/users/{user_id}/jobs", response_model=list[JobResponse])
def list_jobs(user_id: int, status: str | None = None, db: Session = Depends(get_db)):
    query = db.query(Job).filter(Job.user_id == user_id)
    if status:
        query = query.filter(Job.status == status)
    return query.order_by(Job.match_score.desc()).all()


@app.get("/users/{user_id}/dashboard")
def dashboard(user_id: int, db: Session = Depends(get_db)):
    from collections import Counter
    jobs = db.query(Job).filter(Job.user_id == user_id).all()
    status_counts = Counter(j.status for j in jobs)
    return {
        "total_jobs": len(jobs),
        "status_breakdown": dict(status_counts),
        "top_matches": [
            {"id": j.id, "title": j.title, "company": j.company, "match_score": j.match_score}
            for j in sorted(jobs, key=lambda x: x.match_score, reverse=True)[:5]
        ],
    }


@app.patch("/jobs/{job_id}/status")
def update_job_status(job_id: int, payload: TrackingUpdateRequest, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    job.status = payload.status
    db.add(TrackingEvent(job_id=job.id, status=payload.status, note=payload.note))
    db.commit()
    return {"job_id": job_id, "status": job.status}


@app.get("/applications/{application_id}")
def get_application(application_id: int, db: Session = Depends(get_db)):
    app_row = db.query(Application).filter(Application.id == application_id).first()
    if not app_row:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == app_row.job_id).first()

    return {
        "id": app_row.id,
        "job_id": app_row.job_id,
        "job_title": job.title if job else "",
        "company": job.company if job else "",
        "job_url": job.url if job else "",       # real apply link - needed to actually submit manually
        "match_score": job.match_score if job else 0.0,
        "is_demo_data": bool(job and "[DEMO DATA" in (job.title or "")),  # True if this job came from the mock fallback
        "tailored_resume": app_row.tailored_resume,
        "cover_letter": app_row.cover_letter,
        "outreach_message": app_row.outreach_message,
        "ats_score": app_row.ats_score,
        "approval_status": app_row.approval_status,
        "application_method": app_row.application_method,
    }


@app.get("/health")
def health():
    return {"status": "ok"}
