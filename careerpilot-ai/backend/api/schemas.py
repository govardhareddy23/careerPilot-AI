"""
Pydantic request/response schemas for the FastAPI backend.
"""
from pydantic import BaseModel
from typing import List, Dict, Any, Optional


class ProfileCreate(BaseModel):
    name: str
    email: str
    resume_text: str = ""
    github_url: str = ""
    linkedin_url: str = ""
    portfolio_url: str = ""
    leetcode_url: str = ""
    kaggle_url: str = ""
    preferred_locations: List[str] = []
    remote_preference: str = "hybrid"
    min_salary_expectation: int = 0
    target_roles: List[str] = []


class ProfileResponse(BaseModel):
    id: int
    name: str
    email: str
    skills: List[str] = []
    experience: List[Dict[str, Any]] = []
    projects: List[Dict[str, Any]] = []
    education: List[Dict[str, Any]] = []
    certifications: List[str] = []
    achievements: List[str] = []

    class Config:
        from_attributes = True


class RunRequest(BaseModel):
    user_id: int
    task: str


class RunResponse(BaseModel):
    thread_id: str
    state: Dict[str, Any]


class ApprovalDecision(BaseModel):
    approve: bool
    note: Optional[str] = ""


class JobResponse(BaseModel):
    id: int
    title: str
    company: str
    location: str
    remote_type: str
    source: str
    url: str
    salary_range: str
    match_score: float
    score_breakdown: Dict[str, Any] = {}
    status: str

    class Config:
        from_attributes = True


class TrackingUpdateRequest(BaseModel):
    status: str
    note: str = ""
