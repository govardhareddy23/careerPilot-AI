"""
Planning Agent

Decomposes a high-level natural-language user request into an ordered
list of specialist agents to invoke. The Supervisor then executes (and
can dynamically re-order) this plan.

Example:
  "Find me backend jobs in Bangalore and prepare applications"
  -> ["profile_intelligence", "job_scout", "job_ranking", "skill_gap",
      "resume_optimization", "cover_letter", "application"]
  (profile_intelligence is only included if the profile hasn't been
  extracted yet - see _profile_needs_extraction below)

QUOTA-SAVING NOTE:
Free-tier Gemini keys allow very few requests/day (e.g. 20 for
gemini-2.5-flash). Since the full job-application flow is the single
most common request and is entirely predictable, we match it (and a
few other common intents) via cheap keyword heuristics BEFORE ever
calling the LLM. This shaves one full LLM call off every standard run.
The LLM is only invoked as a fallback for requests that don't match any
known pattern.

BUGFIX: the heuristic plan previously NEVER included "profile_intelligence",
which meant skills/experience/projects/etc. were never extracted from the
resume - every downstream agent (job ranking, resume optimization, cover
letter) silently worked off an empty profile. The plan now checks the
actual database state and prepends "profile_intelligence" whenever the
profile's skills list is still empty, regardless of which heuristic or
LLM branch produced the rest of the plan.
"""
import json
from typing import Dict, Any, Optional, List
from backend.agents.base import BaseAgent

ALL_AGENTS = [
    "profile_intelligence", "job_scout", "job_ranking", "skill_gap",
    "resume_optimization", "cover_letter", "application", "interview_prep",
    "tracking",
]

FULL_APPLICATION_FLOW = [
    "job_scout", "job_ranking", "skill_gap",
    "resume_optimization", "cover_letter", "application",
]

PLANNING_PROMPT = """You are the Planning agent for CareerPilot AI.

Given the user's request, produce an ordered JSON list of agent names
(from this fixed set) representing the steps needed to fulfil the request:

["profile_intelligence", "job_scout", "job_ranking", "skill_gap",
 "resume_optimization", "cover_letter", "application", "interview_prep",
 "tracking"]

Rules:
- Only include agents actually needed for the request.
- If the user wants to find/apply to jobs and hasn't set up a profile yet,
  start with "profile_intelligence".
- A full "apply to a job" flow is typically:
  job_scout -> job_ranking -> skill_gap -> resume_optimization ->
  cover_letter -> application
- Respond with ONLY a JSON array of strings, no commentary.

User request: {task}
"""


def _profile_needs_extraction(user_id: int) -> bool:
    """
    Checks the database directly: has profile_intelligence already
    successfully extracted this user's skills? If skills is still empty
    (agent never ran, or a prior run failed before persisting), the plan
    must include profile_intelligence so downstream agents (ranking,
    resume optimization, cover letter) have real data to work with.

    Fails open (returns True -> include the agent) on any DB error, since
    running profile_intelligence unnecessarily is harmless (it's
    idempotent), while skipping it when needed silently breaks everything
    downstream.
    """
    try:
        from backend.db.session import SessionLocal
        from backend.db.models import UserProfile
        db = SessionLocal()
        try:
            profile = db.query(UserProfile).filter(UserProfile.id == user_id).first()
            if not profile:
                return True
            return not profile.skills  # empty list or None -> needs extraction
        finally:
            db.close()
    except Exception:
        return True


def _heuristic_plan(task: str) -> Optional[List[str]]:
    """
    Cheap, no-LLM-call plan matching for common requests.
    Returns None if the task doesn't clearly match a known pattern,
    in which case the caller should fall back to the LLM.

    NOTE: this function only decides the JOB-PIPELINE portion of the
    plan. Whether to prepend "profile_intelligence" is decided
    separately by the caller based on actual DB state, not keywords.
    """
    t = task.lower()

    wants_apply = any(kw in t for kw in (
        "apply", "application package", "prepare an application",
        "tailor", "cover letter",
    ))
    wants_find = any(kw in t for kw in (
        "find", "search", "discover", "look for", "relevant jobs", "job openings",
    ))
    wants_score = any(kw in t for kw in ("score", "rank", "match"))
    wants_track = any(kw in t for kw in ("track", "status", "dashboard", "analytics"))
    wants_interview = any(kw in t for kw in ("interview prep", "interview questions", "mock interview"))
    wants_profile = any(kw in t for kw in ("update my profile", "analyze my resume", "build my profile"))

    # Full end-to-end flow: finding + scoring + preparing an application
    if wants_find and (wants_score or wants_apply) and wants_apply:
        plan = list(FULL_APPLICATION_FLOW)
        if wants_interview:
            plan.append("interview_prep")
        if wants_track:
            plan.append("tracking")
        return plan

    # Just discovery + scoring, no application prep requested
    if wants_find and wants_score and not wants_apply:
        return ["job_scout", "job_ranking"]

    # Just discovery
    if wants_find and not wants_score and not wants_apply:
        return ["job_scout", "job_ranking"]  # ranking is cheap/deterministic, always pair them

    if wants_interview and not (wants_find or wants_apply):
        return ["interview_prep"]

    if wants_track and not (wants_find or wants_apply):
        return ["tracking"]

    if wants_profile and not (wants_find or wants_apply):
        return ["profile_intelligence"]

    return None  # ambiguous - let the LLM decide


class PlanningAgent(BaseAgent):
    name = "planning"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        task = state.get("task", "")
        user_id = state.get("user_id")

        # ---- Try the free heuristic path first (saves an LLM call) ----
        plan = _heuristic_plan(task)
        source = "heuristic"

        if plan is None:
            # ---- Fallback: ask the LLM for an ambiguous/custom request ----
            prompt = PLANNING_PROMPT.format(task=task)
            raw = self.invoke_llm(prompt).strip()
            if raw.startswith("```"):
                raw = raw.strip("`").replace("json", "", 1).strip()
            try:
                plan = json.loads(raw)
                if not isinstance(plan, list):
                    raise ValueError("plan is not a list")
            except (json.JSONDecodeError, ValueError):
                plan = ["job_scout", "job_ranking"]  # safe fallback
            source = "LLM"

        # ---- Always verify against real DB state: does this profile
        # actually have extracted skills yet? If not, profile_intelligence
        # MUST run first, regardless of which branch produced the plan
        # above or whether keywords happened to mention "profile". ----
        if "profile_intelligence" not in plan and _profile_needs_extraction(user_id):
            plan = ["profile_intelligence"] + plan

        return {
            "plan": plan,
            "logs": [f"[planning] ({source}, DB-verified) generated plan: {plan}"],
        }