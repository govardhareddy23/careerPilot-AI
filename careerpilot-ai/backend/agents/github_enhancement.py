"""
GitHub Enhancement Agent

Analyzes the user's GitHub repositories and suggests improvements:
better READMEs, documentation, architecture diagrams, missing tests,
Dockerization, and CI/CD pipelines.
"""
from typing import Dict, Any
from backend.agents.base import BaseAgent
from backend.mcp_servers.client_helpers import fetch_github_profile

GITHUB_PROMPT = """You are the GitHub Enhancement agent for CareerPilot AI.

Given this summary of the candidate's public repositories, provide
actionable improvement suggestions to make their profile more impressive
to recruiters. For each repo (or generally if details are sparse), suggest:
- README improvements
- Missing documentation
- Whether an architecture diagram would help
- Missing tests
- Dockerization opportunities
- CI/CD pipeline suggestions

Be specific and concise. Output as markdown with one section per repo
(or a general section if repo-level detail isn't available).

REPOSITORY SUMMARY:
{repo_summary}
"""


class GitHubEnhancementAgent(BaseAgent):
    name = "github_enhancement"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        profile_row = state.get("profile", {})
        github_url = state.get("scratch", {}).get("github_url") or profile_row.get("github_url", "")

        if not github_url:
            return {"logs": ["[github_enhancement] no github_url available - skipping"]}

        repo_summary = fetch_github_profile(github_url)
        prompt = GITHUB_PROMPT.format(repo_summary=repo_summary)
        suggestions = self.invoke_llm(prompt)

        return {
            "scratch": {"github_suggestions": suggestions},
            "logs": ["[github_enhancement] completed: repository improvement suggestions generated"],
        }
