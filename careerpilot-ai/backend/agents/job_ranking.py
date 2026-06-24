"""
Job Ranking Agent

Scores each discovered job (0-100) against the user's profile based on:
  - Skill match
  - Experience match
  - Location preference
  - Remote preference
  - Salary expectations
  - Company quality (heuristic placeholder)

Writes match_score and score_breakdown back to the Job rows, and selects
the top-ranked job as `current_job` for the downstream per-job pipeline
(skill gap -> resume -> cover letter -> application).
"""
from typing import Dict, Any, List
from backend.agents.base import BaseAgent
from backend.db.session import SessionLocal
from backend.db.models import Job


class JobRankingAgent(BaseAgent):
    name = "job_ranking"

    WEIGHTS = {
        "skill_match": 0.40,
        "experience_match": 0.15,
        "location_match": 0.15,
        "remote_match": 0.10,
        "salary_match": 0.10,
        "company_quality": 0.10,
    }

    def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        profile = state.get("profile", {})
        raw_jobs = state.get("raw_jobs", [])

        user_skills = set(s.lower() for s in profile.get("skills", []))
        preferred_locations = [l.lower() for l in profile.get("preferred_locations", [])]
        remote_pref = (profile.get("remote_preference") or "hybrid").lower()
        min_salary = profile.get("min_salary_expectation", 0)
        years_exp = self._estimate_years_experience(profile.get("experience", []))

        scored_jobs: List[Dict[str, Any]] = []
        db = SessionLocal()
        try:
            for job_data in raw_jobs:
                required_skills = set(s.lower() for s in job_data.get("required_skills", []))

                skill_match = self._skill_match(user_skills, required_skills)
                experience_match = self._experience_match(years_exp, job_data.get("description", ""))
                location_match = self._location_match(preferred_locations, job_data.get("location", ""))
                remote_match = self._remote_match(remote_pref, job_data.get("remote_type", ""))
                salary_match = self._salary_match(min_salary, job_data.get("salary_range", ""))
                company_quality = 70  # heuristic placeholder; could call MCP company-info tool

                breakdown = {
                    "skill_match": skill_match,
                    "experience_match": experience_match,
                    "location_match": location_match,
                    "remote_match": remote_match,
                    "salary_match": salary_match,
                    "company_quality": company_quality,
                }
                total_score = sum(breakdown[k] * w for k, w in self.WEIGHTS.items())
                total_score = round(total_score, 1)

                job_data["match_score"] = total_score
                job_data["score_breakdown"] = breakdown
                job_data["status"] = "scored"
                scored_jobs.append(job_data)

                # persist
                if job_data.get("id"):
                    job_row = db.query(Job).filter(Job.id == job_data["id"]).first()
                    if job_row:
                        job_row.match_score = total_score
                        job_row.score_breakdown = breakdown
                        job_row.status = "scored"
                        db.commit()
        finally:
            db.close()

        scored_jobs.sort(key=lambda j: j["match_score"], reverse=True)
        current_job = scored_jobs[0] if scored_jobs else {}

        return {
            "scored_jobs": scored_jobs,
            "current_job": current_job,
            "logs": [
                f"[job_ranking] completed: scored {len(scored_jobs)} jobs, "
                f"top match '{current_job.get('title', 'N/A')}' "
                f"at {current_job.get('company', 'N/A')} "
                f"({current_job.get('match_score', 0)}/100)"
            ],
        }

    # ---- scoring helpers ----

    @staticmethod
    def _skill_match(user_skills: set, required_skills: set) -> float:
        if not required_skills:
            return 50.0
        overlap = user_skills.intersection(required_skills)
        return round(100 * len(overlap) / len(required_skills), 1)

    @staticmethod
    def _estimate_years_experience(experience: list) -> float:
        # crude heuristic: count entries as ~1.5 years each if no duration parsed
        return len(experience) * 1.5

    @staticmethod
    def _experience_match(years_exp: float, description: str) -> float:
        desc_lower = description.lower()
        if "senior" in desc_lower and years_exp < 3:
            return 40.0
        if "senior" in desc_lower and years_exp >= 3:
            return 90.0
        if "junior" in desc_lower or "entry" in desc_lower:
            return 90.0 if years_exp < 3 else 70.0
        return 75.0  # neutral / mid-level roles

    @staticmethod
    def _location_match(preferred_locations: list, job_location: str) -> float:
        if not preferred_locations:
            return 60.0
        job_loc_lower = job_location.lower()
        if any(loc in job_loc_lower for loc in preferred_locations):
            return 100.0
        if "remote" in job_loc_lower:
            return 80.0
        return 30.0

    @staticmethod
    def _remote_match(remote_pref: str, job_remote_type: str) -> float:
        job_remote_type = (job_remote_type or "").lower()
        if remote_pref == job_remote_type:
            return 100.0
        if remote_pref == "hybrid" and job_remote_type in ("remote", "onsite"):
            return 60.0
        return 40.0

    @staticmethod
    def _salary_match(min_salary: int, salary_range: str) -> float:
        if not min_salary or not salary_range:
            return 60.0
        # crude numeric extraction
        import re
        numbers = re.findall(r"[\d,]+", salary_range)
        if not numbers:
            return 60.0
        try:
            max_offered = int(numbers[-1].replace(",", ""))
            if max_offered >= min_salary:
                return 100.0
            ratio = max_offered / min_salary if min_salary else 1
            return round(max(0, ratio * 100), 1)
        except ValueError:
            return 60.0
