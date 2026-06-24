"""
Shared state object passed between all agents in the LangGraph workflow.

This is the single source of truth for one "run" of the CareerPilot pipeline.
Each agent reads what it needs and writes its results back into the state.
LangGraph merges partial state updates (TypedDict + reducers).
"""
from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator


def merge_dicts(a: dict, b: dict) -> dict:
    """Reducer: shallow-merge two dicts (b wins on conflicts)."""
    merged = dict(a or {})
    merged.update(b or {})
    return merged


class CareerPilotState(TypedDict, total=False):
    # ---- Identity / routing ----
    user_id: int
    task: str                      # high-level instruction from user/supervisor
    next_agent: str                # set by supervisor for routing
    plan: List[str]                # ordered list of agent names to execute
    completed_agents: Annotated[List[str], operator.add]  # structured run history (not log text)
    step_count: int                # incremented by supervisor each routing decision; hard safety valve

    # ---- Profile ----
    profile: Dict[str, Any]

    # ---- Job pipeline ----
    raw_jobs: List[Dict[str, Any]]       # output of Job Scout
    scored_jobs: List[Dict[str, Any]]    # output of Job Ranking
    current_job: Dict[str, Any]          # job currently being processed end-to-end

    # ---- Per-job artifacts ----
    skill_gap: Dict[str, Any]
    tailored_resume: str
    cover_letter: str
    outreach_message: str

    # ---- Human-in-the-loop ----
    requires_approval: bool
    approval_status: str           # pending/approved/rejected
    approval_payload: Dict[str, Any]

    # ---- Messages / logs ----
    messages: Annotated[List[Dict[str, str]], operator.add]
    logs: Annotated[List[str], operator.add]

    # ---- Misc shared scratch space ----
    scratch: Annotated[Dict[str, Any], merge_dicts]
