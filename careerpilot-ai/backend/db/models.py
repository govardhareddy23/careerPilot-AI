"""
Database models for CareerPilot AI.
Covers: user profiles, jobs, rankings, skill gaps, applications,
resumes/cover letters, interview prep, tracking, notifications.
"""
from sqlalchemy import (
    Column, Integer, String, Float, Text, DateTime, ForeignKey, Boolean, JSON
)
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()


class UserProfile(Base):
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)

    # Raw source data
    resume_text = Column(Text, default="")
    github_url = Column(String, default="")
    linkedin_url = Column(String, default="")
    portfolio_url = Column(String, default="")
    leetcode_url = Column(String, default="")
    kaggle_url = Column(String, default="")

    # Structured extracted data (JSON)
    skills = Column(JSON, default=list)          # ["Python", "LangGraph", ...]
    experience = Column(JSON, default=list)      # [{title, company, years, desc}]
    projects = Column(JSON, default=list)        # [{name, description, tech}]
    education = Column(JSON, default=list)       # [{degree, institution, year}]
    certifications = Column(JSON, default=list)  # [str]
    achievements = Column(JSON, default=list)    # [str]

    # Preferences
    preferred_locations = Column(JSON, default=list)
    remote_preference = Column(String, default="hybrid")  # remote/hybrid/onsite
    min_salary_expectation = Column(Integer, default=0)
    target_roles = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"))

    title = Column(String, nullable=False)
    company = Column(String, nullable=False)
    location = Column(String, default="")
    remote_type = Column(String, default="")  # remote/hybrid/onsite
    source = Column(String, default="")       # linkedin/indeed/naukri/etc
    url = Column(String, default="")
    description = Column(Text, default="")
    salary_range = Column(String, default="")
    posted_date = Column(String, default="")

    required_skills = Column(JSON, default=list)

    match_score = Column(Float, default=0.0)
    score_breakdown = Column(JSON, default=dict)  # {skill_match, exp_match, ...}

    status = Column(String, default="discovered")
    # discovered -> scored -> resume_ready -> awaiting_approval -> approved
    # -> applied -> assessment -> interview -> offer -> rejected

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    skill_gaps = relationship("SkillGap", back_populates="job", cascade="all, delete-orphan")
    application = relationship("Application", back_populates="job", uselist=False, cascade="all, delete-orphan")


class SkillGap(Base):
    __tablename__ = "skill_gaps"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))

    missing_skills = Column(JSON, default=list)
    missing_certifications = Column(JSON, default=list)
    missing_technologies = Column(JSON, default=list)
    learning_recommendations = Column(JSON, default=list)  # [{resource, type, priority}]

    created_at = Column(DateTime, default=datetime.utcnow)

    job = relationship("Job", back_populates="skill_gaps")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), unique=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"))

    tailored_resume = Column(Text, default="")
    ats_score = Column(Float, default=0.0)
    cover_letter = Column(Text, default="")
    outreach_message = Column(Text, default="")

    approval_status = Column(String, default="pending")  # pending/approved/rejected
    applied_at = Column(DateTime, nullable=True)

    application_method = Column(String, default="")  # easy_apply/portal/email

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    job = relationship("Job", back_populates="application")


class InterviewPrep(Base):
    __tablename__ = "interview_prep"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))

    company_research = Column(Text, default="")
    technical_questions = Column(JSON, default=list)
    behavioral_questions = Column(JSON, default=list)
    dsa_roadmap = Column(JSON, default=list)
    mock_session_notes = Column(Text, default="")

    created_at = Column(DateTime, default=datetime.utcnow)


class TrackingEvent(Base):
    __tablename__ = "tracking_events"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    status = Column(String, nullable=False)
    note = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class AgentRun(Base):
    """Audit log of every agent execution - useful for the Learning Agent
    and for demonstrating observability."""
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String, nullable=False)
    input_summary = Column(Text, default="")
    output_summary = Column(Text, default="")
    status = Column(String, default="success")  # success/error
    duration_ms = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("user_profiles.id"))
    channel = Column(String, default="email")  # email/telegram/discord
    title = Column(String, default="")
    body = Column(Text, default="")
    sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
