"""
Job Scout Agent

Generates optimized search queries from the user's profile/preferences
and searches configured job boards (LinkedIn, Indeed, Wellfound, Naukri,
Internshala, Glassdoor, company career pages) via the job-board MCP tool.

Persists newly discovered jobs to the database (deduplicated by URL) and
returns them in state for downstream ranking.
"""
from typing import Dict, Any
from backend.agents.base import BaseAgent
from backend.db.session import SessionLocal
from backend.db.models import Job
from backend.mcp_servers.client_helpers import search_jobs_external

QUERY_GEN_PROMPT = """You are the Job Scout agent for CareerPilot AI.

Based on this user profile summary, generate 2-3 concise, high-signal job
search queries (just role/keyword phrases, not full sentences) that would
find the most relevant openings.

Profile skills: {skills}
Target roles: {target_roles}
Preferred locations: {locations}
Remote preference: {remote_pref}

Respond with ONLY a JSON array of 2-3 short query strings, e.g.
["Backend Engineer Python", "AI Engineer LangChain"]
"""


class JobScoutAgent(BaseAgent):
    name = "job_scout"

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        profile = state.get("profile", {})
        user_id = state.get("user_id")

        import json

        # Query generation via LLM is a nice-to-have (turns role names into
        # punchier search phrases), not a hard requirement - profile's own
        # target_roles already work fine as search queries. If the LLM call
        # fails for ANY reason (quota, network, malformed output), fall back
        # immediately rather than letting the whole agent - and therefore
        # the whole pipeline - die on a non-critical step.
        queries = None
        try:
            prompt = QUERY_GEN_PROMPT.format(
                skills=profile.get("skills", [])[:15],
                target_roles=profile.get("target_roles", []),
                locations=profile.get("preferred_locations", []),
                remote_pref=profile.get("remote_preference", "hybrid"),
            )
            raw = self.invoke_llm(prompt).strip()
            if raw.startswith("```"):
                raw = raw.strip("`").replace("json", "", 1).strip()
            parsed = json.loads(raw)
            if isinstance(parsed, list) and parsed:
                queries = parsed
        except Exception as exc:  # noqa: BLE001 - quota/network/parse errors all fall back the same way
            query_gen_error = str(exc)
        else:
            query_gen_error = None

        if queries is None:
            queries = profile.get("target_roles", ["Software Engineer"])[:2] or ["Software Engineer"]
            fallback_note = f" (LLM query generation skipped: {query_gen_error})" if query_gen_error else " (used target_roles directly)"
        else:
            fallback_note = ""

        # JSearch aggregates LinkedIn/Indeed/Glassdoor/etc. itself and
        # returns the real publisher per result, so we no longer need to
        # fan out across a fake "sources" list (that made sense only for
        # the old mock data). One real call per query is both cheaper on
        # API quota and avoids fetching duplicate results twice.
        location = (profile.get("preferred_locations") or [""])[0]

        discovered = []
        for q in queries:
            results = search_jobs_external(q, location=location, source="jsearch")
            discovered.extend(results)

        # Persist & dedupe
        db = SessionLocal()
        saved_jobs = []
        try:
            for job_data in discovered:
                # Skip jobs with no usable identifier/URL - can't safely
                # dedupe these, and a blank apply link isn't actionable.
                if not job_data.get("url"):
                    continue

                # JSearch rarely populates required_skills reliably; fall
                # back to extracting candidate-known skills mentioned in
                # the raw description so Job Ranking's skill-match scoring
                # has something real to compare against.
                if not job_data.get("required_skills"):
                    job_data["required_skills"] = self._extract_skills_from_text(
                        job_data.get("description", ""), profile.get("skills", [])
                    )

                existing = db.query(Job).filter(
                    Job.url == job_data["url"], Job.user_id == user_id
                ).first()
                if existing:
                    saved_jobs.append(self._to_dict(existing))
                    continue
                job = Job(
                    user_id=user_id,
                    title=job_data["title"],
                    company=job_data["company"],
                    location=job_data["location"],
                    remote_type=job_data.get("remote_type", ""),
                    source=job_data.get("source", ""),
                    url=job_data["url"],
                    description=job_data.get("description", ""),
                    salary_range=job_data.get("salary_range", ""),
                    posted_date=job_data.get("posted_date", ""),
                    required_skills=job_data.get("required_skills", []),
                    status="discovered",
                )
                db.add(job)
                db.commit()
                db.refresh(job)
                saved_jobs.append(self._to_dict(job))
        finally:
            db.close()

        return {
            "raw_jobs": saved_jobs,
            "logs": [f"[job_scout] completed: discovered {len(saved_jobs)} jobs via queries {queries}{fallback_note}"],
        }

    @staticmethod
    def _extract_skills_from_text(description: str, candidate_skills: list) -> list:
        """Best-effort skill extraction: checks which of the candidate's
        own known skills are mentioned in the job description text.
        Cheap, no LLM call, and gives Job Ranking real signal to score
        against when the job-board API doesn't return structured skills.
        """
        desc_lower = description.lower()
        return [s for s in candidate_skills if s.lower() in desc_lower]

    @staticmethod
    def _to_dict(job: Job) -> dict:
        return {
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "remote_type": job.remote_type,
            "source": job.source,
            "url": job.url,
            "description": job.description,
            "salary_range": job.salary_range,
            "posted_date": job.posted_date,
            "required_skills": job.required_skills,
            "status": job.status,
        }