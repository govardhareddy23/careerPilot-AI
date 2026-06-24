"""
LangGraph Workflow for CareerPilot AI

Defines the multi-agent graph:

                        +----------------+
            +---------> |   Supervisor   | <-------------------+
            |           +----------------+                      |
            |                   |                               |
            |          (routes via next_agent)                  |
            |                   v                                |
            |   +------------------------------------+          |
            |   | profile_intelligence | job_scout    |          |
            |   | job_ranking          | skill_gap    |----------+
            |   | resume_optimization  | cover_letter |   (loop back
            |   | application          | interview_prep|   to supervisor
            |   | tracking             |               |   after each
            |   +------------------------------------+   agent runs)
            |                   |
            |          next_agent == "FINISH"
            |                   |
            +-------------------+--> END

Human-in-the-loop: when the Application Agent runs, it sets
`requires_approval=True` and `approval_status="pending"`. The Supervisor
detects this and routes to FINISH, halting the graph. The graph is later
RESUMED (via the same thread/checkpoint) after the user approves/rejects
via the API.

FIX 1: All agent instances are created INSIDE build_graph() and
build_graph() is called INSIDE a lazy get_graph() function.
This ensures no LLM client is constructed at module import time —
only when the first API request actually arrives, by which point
pydantic-settings has already loaded the .env file and all env vars
are set correctly.

FIX 2 (node-name collision): LangGraph forbids a node name that is
identical to a key already present in the State TypedDict schema.
Our CareerPilotState has fields named `skill_gap` and `cover_letter`
(used to store each agent's output), which collided with the node
names "skill_gap" and "cover_letter" we originally registered.

Resolution: the SupervisorAgent's routing vocabulary (the strings it
asks the LLM to choose from, e.g. "skill_gap", "cover_letter") is left
UNCHANGED, since changing that means touching the supervisor's prompt.
Instead, internal LangGraph NODE NAMES are suffixed with "_node"
(e.g. "skill_gap_node") to avoid any collision with state keys, and a
NODE_NAME_MAP translates the supervisor's chosen agent name to the
correct internal node name before routing.
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from backend.core.state import CareerPilotState

# ---- Imports of agent classes only (no instantiation here) ----
from backend.agents.supervisor import SupervisorAgent
from backend.agents.planning import PlanningAgent
from backend.agents.profile_intelligence import ProfileIntelligenceAgent
from backend.agents.job_scout import JobScoutAgent
from backend.agents.job_ranking import JobRankingAgent
from backend.agents.skill_gap import SkillGapAgent
from backend.agents.resume_optimization import ResumeOptimizationAgent
from backend.agents.cover_letter import CoverLetterAgent
from backend.agents.application import ApplicationAgent
from backend.agents.interview_prep import InterviewPrepAgent
from backend.agents.tracking import TrackingAgent

# Module-level cache — populated on first request, never at import time
_graph_cache = None

# Maps the agent name the Supervisor LLM outputs (matching
# backend.agents.supervisor.VALID_AGENTS) to the actual LangGraph node
# name used internally. Any agent name that does NOT collide with a
# CareerPilotState field maps to itself.
NODE_NAME_MAP = {
    "profile_intelligence": "profile_intelligence",
    "job_scout":            "job_scout",
    "job_ranking":           "job_ranking",
    "skill_gap":             "skill_gap_node",       # collides with state["skill_gap"]
    "resume_optimization":   "resume_optimization",
    "cover_letter":          "cover_letter_node",      # collides with state["cover_letter"]
    "application":           "application",
    "interview_prep":        "interview_prep",
    "tracking":               "tracking",
}


def get_graph():
    """Return the compiled graph, building it once on first call.

    Lazy construction guarantees the .env file and all env vars are
    loaded before any LLM client is created.
    """
    global _graph_cache
    if _graph_cache is None:
        _graph_cache = _build_graph()
    return _graph_cache


def _build_graph():
    """Construct and compile the CareerPilot LangGraph workflow.
    Called once, lazily, on first API request.
    """
    # ---- Instantiate agents HERE (not at module level) ----
    # Keyed by INTERNAL node name (post name-collision fix).
    agent_nodes = {
        "profile_intelligence":  ProfileIntelligenceAgent(),
        "job_scout":              JobScoutAgent(),
        "job_ranking":            JobRankingAgent(),
        "skill_gap_node":         SkillGapAgent(),
        "resume_optimization":    ResumeOptimizationAgent(),
        "cover_letter_node":      CoverLetterAgent(),
        "application":            ApplicationAgent(),
        "interview_prep":         InterviewPrepAgent(),
        "tracking":                TrackingAgent(),
    }

    def route_from_supervisor(state: CareerPilotState) -> str:
        next_agent = state.get("next_agent", "FINISH")
        node_name = NODE_NAME_MAP.get(next_agent)
        if next_agent == "FINISH" or node_name is None or node_name not in agent_nodes:
            return END
        return node_name

    graph = StateGraph(CareerPilotState)

    graph.add_node("planning",    PlanningAgent())
    graph.add_node("supervisor",  SupervisorAgent())
    for node_name, agent in agent_nodes.items():
        graph.add_node(node_name, agent)

    graph.set_entry_point("planning")
    graph.add_edge("planning", "supervisor")

    graph.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {**{node_name: node_name for node_name in agent_nodes}, END: END},
    )

    for node_name in agent_nodes:
        graph.add_edge(node_name, "supervisor")

    checkpointer = MemorySaver()
    return graph.compile(checkpointer=checkpointer)

