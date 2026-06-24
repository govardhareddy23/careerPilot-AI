"""
Portfolio Enhancement Agent

Analyzes the user's portfolio (given as URL or text description) and
suggests: missing projects, better project descriptions, SEO
improvements, technical blog topics, and personal branding improvements.
"""
from typing import Dict, Any
from backend.agents.base import BaseAgent

PORTFOLIO_PROMPT = """You are the Portfolio Enhancement agent for CareerPilot AI.

Based on the candidate's profile (projects, skills, target roles), suggest
portfolio website improvements:
- 2-3 new project ideas that would strengthen their profile for their target roles
- How to better describe existing projects (focus on impact/metrics)
- SEO improvements (meta tags, keywords, page titles)
- 3 technical blog post topics they could write to demonstrate expertise
- Personal branding suggestions (tagline, about section angle)

Output as concise markdown with headers for each category.

CANDIDATE PROJECTS: {projects}
CANDIDATE SKILLS: {skills}
TARGET ROLES: {target_roles}
PORTFOLIO URL: {portfolio_url}
"""


class PortfolioEnhancementAgent(BaseAgent):
    name = "portfolio_enhancement"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        profile = state.get("profile", {})

        prompt = PORTFOLIO_PROMPT.format(
            projects=profile.get("projects", []),
            skills=profile.get("skills", []),
            target_roles=profile.get("target_roles", []),
            portfolio_url=profile.get("portfolio_url", "N/A"),
        )
        suggestions = self.invoke_llm(prompt)

        return {
            "scratch": {"portfolio_suggestions": suggestions},
            "logs": ["[portfolio_enhancement] completed: portfolio improvement suggestions generated"],
        }
