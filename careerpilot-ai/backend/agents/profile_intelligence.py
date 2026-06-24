"""
Profile Intelligence Agent

Collects and analyzes the user's resume, GitHub, LinkedIn, portfolio,
LeetCode, and Kaggle profiles. Extracts structured data (skills,
experience, projects, education, certifications, achievements) using
the LLM, persists it to the UserProfile table, and indexes the raw
text into the per-user RAG vector store for later retrieval by other
agents (resume optimization, cover letters, interview prep, etc).

Note: live scraping of LinkedIn/GitHub/etc requires their respective
APIs or scraping infrastructure (often auth-gated). This implementation
provides the extraction pipeline and a pluggable `fetch_external_profile`
function - swap in real API calls (GitHub REST API, LinkedIn via
authorized scraping service, etc.) as needed.
"""
import json
from typing import Dict, Any
from backend.agents.base import BaseAgent
from backend.db.session import SessionLocal
from backend.db.models import UserProfile
from backend.rag.store import PersonalDocStore
from backend.mcp_servers.client_helpers import fetch_github_profile

EXTRACTION_PROMPT = """You are the Profile Intelligence agent for CareerPilot AI.

Analyze the following combined text from the user's resume and any linked
profiles (GitHub, portfolio, etc). Extract a structured JSON object with
EXACTLY these keys:

{{
  "skills": ["list of technical & soft skills"],
  "experience": [{{"title": "", "company": "", "duration": "", "description": ""}}],
  "projects": [{{"name": "", "description": "", "tech_stack": []}}],
  "education": [{{"degree": "", "institution": "", "year": ""}}],
  "certifications": ["list"],
  "achievements": ["list"]
}}

Respond with ONLY valid JSON, no commentary or markdown fences.

--- COMBINED PROFILE TEXT ---
{combined_text}
"""


class ProfileIntelligenceAgent(BaseAgent):
    name = "profile_intelligence"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        user_id = state.get("user_id")
        db = SessionLocal()
        try:
            profile_row = db.query(UserProfile).filter(UserProfile.id == user_id).first()
            if not profile_row:
                return {"logs": [f"[profile_intelligence] No profile found for user_id={user_id}"]}

            combined_text_parts = [profile_row.resume_text or ""]

            # Pluggable external fetchers (MCP tools) - GitHub shown as example
            if profile_row.github_url:
                gh_summary = fetch_github_profile(profile_row.github_url)
                combined_text_parts.append(f"\nGITHUB PROFILE:\n{gh_summary}")

            combined_text = "\n".join(p for p in combined_text_parts if p)[:15000]

            if not combined_text.strip():
                return {"logs": ["[profile_intelligence] No source text available to analyze"]}

            prompt = EXTRACTION_PROMPT.format(combined_text=combined_text)
            raw = self.invoke_llm(prompt).strip()
            if raw.startswith("```"):
                raw = raw.strip("`").replace("json", "", 1).strip()

            extracted = json.loads(raw)

            # Persist structured fields
            profile_row.skills = extracted.get("skills", [])
            profile_row.experience = extracted.get("experience", [])
            profile_row.projects = extracted.get("projects", [])
            profile_row.education = extracted.get("education", [])
            profile_row.certifications = extracted.get("certifications", [])
            profile_row.achievements = extracted.get("achievements", [])
            db.commit()

            # Index into RAG store for later retrieval.
            # IMPORTANT: this must never be allowed to discard the
            # already-extracted-and-committed profile data above. A RAG/
            # embeddings failure (e.g. deprecated model name, quota, network)
            # should degrade gracefully - the agent still returns the real
            # profile so downstream agents (resume optimization, job
            # ranking, etc.) work correctly, just without RAG grounding.
            try:
                store = PersonalDocStore(user_id=user_id)
                docs = []
                if profile_row.resume_text:
                    docs.append({
                        "id": f"resume_{user_id}",
                        "text": profile_row.resume_text,
                        "metadata": {"type": "resume"},
                    })
                for i, proj in enumerate(extracted.get("projects", [])):
                    docs.append({
                        "id": f"project_{user_id}_{i}",
                        "text": json.dumps(proj),
                        "metadata": {"type": "project"},
                    })
                store.add_documents(docs)
                rag_status = "indexed"
            except Exception as rag_exc:  # noqa: BLE001
                rag_status = f"RAG indexing failed (non-fatal): {rag_exc}"

            profile_dict = {
                "skills": profile_row.skills,
                "experience": profile_row.experience,
                "projects": profile_row.projects,
                "education": profile_row.education,
                "certifications": profile_row.certifications,
                "achievements": profile_row.achievements,
                "preferred_locations": profile_row.preferred_locations,
                "remote_preference": profile_row.remote_preference,
                "min_salary_expectation": profile_row.min_salary_expectation,
                "target_roles": profile_row.target_roles,
            }

            return {
                "profile": profile_dict,
                "logs": [
                    "[profile_intelligence] completed: profile extracted and saved",
                    f"[profile_intelligence] RAG status: {rag_status}",
                ],
            }

        except json.JSONDecodeError as e:
            return {"logs": [f"[profile_intelligence] ERROR parsing LLM output: {e}"]}
        finally:
            db.close()
