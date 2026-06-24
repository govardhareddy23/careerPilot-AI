"""
Supervisor Agent

Top of the LangGraph hierarchy. Given the user's high-level task and current
state, decides which specialist agent should run next, or whether the
pipeline is complete / needs human approval.

FIX (infinite loop / GraphRecursionError):
The original implementation asked the LLM "what should run next?" on every
single turn with no structural memory of what had already run, and no hard
cap. If the LLM ever re-picked an agent that had already completed (a very
common LLM failure mode under temperature > 0), the graph would loop
forever until LangGraph's generic recursion_limit (default 25) killed it
with an opaque GraphRecursionError.

Resolution — two layers of defense:
  1. DETERMINISTIC PLAN FOLLOWING (primary): the Supervisor now walks
     state["plan"] (produced once by the Planning agent) in order,
     skipping any agent already present in state["completed_agents"].
     This needs no LLM call at all for the common case, which is both
     faster/cheaper AND immune to model non-determinism.
  2. HARD STEP CAP (safety net): state["step_count"] increments every
     supervisor turn. If it exceeds MAX_STEPS, the supervisor force-
     finishes rather than ever reaching LangGraph's recursion error.

The LLM is now only consulted as a fallback for free-form / off-plan
requests (e.g. "just give me a notification" where no plan was set), not
on every single turn of the main pipeline.

FIX (graceful failure cascade): previously, if job_scout/job_ranking
failed or produced zero jobs, the Supervisor would still dutifully route
through every remaining job-dependent agent (skill_gap, resume_optimization,
cover_letter, application, interview_prep), each of which would just log
"no current_job in state - skipping" - a confusing wall of no-op messages.
The Supervisor now detects this condition and stops the plan early with
one clear, actionable log line instead.
"""
from typing import Dict, Any
from backend.agents.base import BaseAgent

VALID_AGENTS = [
    "profile_intelligence",
    "job_scout",
    "job_ranking",
    "skill_gap",
    "resume_optimization",
    "cover_letter",
    "application",
    "interview_prep",
    "tracking",
    "FINISH",
]

# Hard safety valve — supervisor force-finishes after this many of its own
# turns, regardless of what the plan or LLM says. Comfortably above the
# longest realistic plan (9 specialist agents) but far below LangGraph's
# default recursion_limit of 25, so we fail gracefully with a clear log
# message instead of an opaque GraphRecursionError.
MAX_STEPS = 12

SUPERVISOR_FALLBACK_PROMPT = """You are the Supervisor agent for CareerPilot AI, an autonomous
career assistant. No predefined plan covers the current situation, so decide
which specialist agent should act next.

Available agents and what they do:
- profile_intelligence: builds/updates the user's structured profile from resume/links
- job_scout: searches job boards for new openings
- job_ranking: scores discovered jobs against the user profile
- skill_gap: analyzes missing skills/certs for the current job
- resume_optimization: tailors resume for the current job
- cover_letter: generates cover letter & outreach messages for the current job
- application: prepares the application package and requests human approval
- interview_prep: generates interview prep material for shortlisted jobs
- tracking: updates / reports on application tracking status
- FINISH: the requested task is complete

Current task: {task}
Already completed this run: {completed}

Respond with ONLY the single agent name from the list above that should run next.
Do NOT repeat an agent that is already in the completed list.
"""


class SupervisorAgent(BaseAgent):
    name = "supervisor"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        completed = state.get("completed_agents", [])
        plan = state.get("plan", [])
        step_count = state.get("step_count", 0) + 1

        # ---- Hard safety valve ----
        if step_count > MAX_STEPS:
            return {
                "next_agent": "FINISH",
                "step_count": step_count,
                "logs": [f"[supervisor] MAX_STEPS ({MAX_STEPS}) reached - force-finishing to avoid infinite loop"],
            }

        # ---- Human-in-the-loop halt ----
        if state.get("approval_status") == "pending" and state.get("requires_approval"):
            return {
                "next_agent": "FINISH",
                "step_count": step_count,
                "logs": ["[supervisor] Awaiting human approval - halting"],
            }

        # ---- Layer 1: deterministic plan-following (no LLM call) ----
        remaining = [a for a in plan if a in VALID_AGENTS[:-1] and a not in completed]

        # Job-dependent agents are pointless to run if job discovery/ranking
        # never produced a current_job (e.g. job_scout failed on quota, or
        # job_ranking scored zero jobs). Rather than cascading through every
        # remaining step printing "no current_job in state - skipping",
        # stop the plan early with one clear, actionable log line.
        job_dependent_agents = {
            "skill_gap", "resume_optimization", "cover_letter",
            "application", "interview_prep",
        }
        job_pipeline_agents = {"job_scout", "job_ranking"}
        job_pipeline_done = not any(a in remaining for a in job_pipeline_agents)
        no_job_available = job_pipeline_done and not state.get("current_job")

        if remaining and no_job_available and remaining[0] in job_dependent_agents:
            return {
                "next_agent": "FINISH",
                "step_count": step_count,
                "logs": [
                    "[supervisor] no current_job available after job discovery/ranking "
                    "(likely an earlier step failed or found 0 results) - "
                    f"stopping early instead of running {len(remaining)} no-op step(s): {remaining}"
                ],
            }

        if remaining:
            next_agent = remaining[0]
            return {
                "next_agent": next_agent,
                "step_count": step_count,
                "completed_agents": [next_agent],
                "logs": [f"[supervisor] (plan step {len(completed) + 1}/{len(plan)}) routing to '{next_agent}'"],
            }

        # ---- Plan exhausted (or empty) ----
        if plan:
            # Every planned agent has already run - we're done.
            return {
                "next_agent": "FINISH",
                "step_count": step_count,
                "logs": ["[supervisor] plan complete - finishing"],
            }

        # ---- Layer 2: LLM fallback (only when there's no plan to follow) ----
        prompt = SUPERVISOR_FALLBACK_PROMPT.format(
            task=state.get("task", ""),
            completed=completed,
        )
        decision = self.invoke_llm(prompt).strip().lower().replace(" ", "_")
        match = next((a for a in VALID_AGENTS if a.lower() == decision), None)
        next_agent = match or "FINISH"

        # Guard against the LLM fallback re-picking something already done.
        if next_agent in completed:
            next_agent = "FINISH"

        update = {
            "next_agent": next_agent,
            "step_count": step_count,
            "logs": [f"[supervisor] (LLM fallback) routing to '{next_agent}'"],
        }
        if next_agent != "FINISH":
            update["completed_agents"] = [next_agent]
        return update