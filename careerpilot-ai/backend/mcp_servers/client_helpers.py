"""
MCP (Model Context Protocol) integration helpers.

These functions act as "tools" that agents call. In production, each
function would call out to an MCP server (e.g. a GitHub MCP server,
a job-board MCP server, a notification MCP server) over the MCP
client SDK. Here they are implemented as direct, swappable Python
functions with the same signatures, so:

  1. The agent code is already written against the MCP "tool" interface.
  2. Swapping in real MCP servers later requires no agent code changes -
     only replacing the body of each function with an MCP client call.

See backend/mcp_servers/ for the corresponding server stubs that would
be registered with an MCP-compatible orchestrator.
"""
import requests
from typing import Dict, Any
from backend.core.config import get_settings


def fetch_github_profile(github_url: str) -> str:
    """Fetch a summary of a user's public GitHub repos via the GitHub REST API.

    MCP equivalent: `github.get_user_repos` tool call.
    """
    try:
        username = github_url.rstrip("/").split("/")[-1]
        resp = requests.get(f"https://api.github.com/users/{username}/repos", timeout=10)
        resp.raise_for_status()
        repos = resp.json()
        summary_lines = []
        for repo in repos[:15]:
            summary_lines.append(
                f"- {repo.get('name')}: {repo.get('description') or 'No description'} "
                f"(language: {repo.get('language')}, stars: {repo.get('stargazers_count')})"
            )
        return "\n".join(summary_lines) if summary_lines else "No public repositories found."
    except Exception as exc:  # noqa: BLE001
        return f"Could not fetch GitHub profile: {exc}"


def search_jobs_external(query: str, location: str = "", source: str = "linkedin") -> list:
    """Search REAL jobs via the JSearch API (aggregates LinkedIn, Indeed,
    Glassdoor, ZipRecruiter, and more behind one endpoint).

    MCP equivalent: `jobboard.search` tool call on a job-search MCP server.

    Requires JSEARCH_API_KEY to be set in .env (RapidAPI key for JSearch:
    https://rapidapi.com/letscrape-6bRBa3QguO5/api/jsearch).

    Falls back to mock data (clearly labeled) if no key is configured,
    so the pipeline still runs for local testing without a key.
    """
    settings = get_settings()
    api_key = settings.jsearch_api_key.strip()

    if not api_key:
        return _mock_jobs(query, location, source, reason="JSEARCH_API_KEY not set in .env")

    try:
        search_query = f"{query} in {location}" if location else query
        resp = requests.get(
            "https://jsearch.p.rapidapi.com/search",
            headers={
                "X-RapidAPI-Key": api_key,
                "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
            },
            params={
                "query": search_query,
                "page": "1",
                "num_pages": "1",
                "date_posted": "month",
            },
            timeout=15,
        )
        resp.raise_for_status()
        data = resp.json()
        results = data.get("data", [])

        jobs = []
        for job in results[:10]:
            jobs.append({
                "title": job.get("job_title") or "Unknown Title",
                "company": job.get("employer_name") or "Unknown Company",
                "location": job.get("job_city") or job.get("job_country") or location or "Remote",
                "remote_type": "remote" if job.get("job_is_remote") else "onsite",
                "source": job.get("job_publisher") or source,
                "url": job.get("job_apply_link") or job.get("job_google_link") or "",
                "description": (job.get("job_description") or "")[:2000],
                "salary_range": _format_salary(job),
                "posted_date": (job.get("job_posted_at_datetime_utc") or "")[:10],
                "required_skills": job.get("job_required_skills") or [],
            })
        return jobs if jobs else _mock_jobs(query, location, source, reason="JSearch returned 0 results")

    except requests.exceptions.RequestException as exc:
        return _mock_jobs(query, location, source, reason=f"JSearch API error: {exc}")


def _format_salary(job: dict) -> str:
    lo, hi = job.get("job_min_salary"), job.get("job_max_salary")
    currency = job.get("job_salary_currency") or "USD"
    if lo and hi:
        try:
            return f"{currency} {int(float(lo)):,} - {int(float(hi)):,}"
        except (ValueError, TypeError):
            return "Not disclosed"
    return "Not disclosed"


def _mock_jobs(query: str, location: str, source: str, reason: str) -> list:
    """Fallback mock data, clearly labeled as fake so it's never mistaken
    for a real listing. Used only when no API key is configured or the
    real API call fails.

    NOTE: url is intentionally non-empty (job_scout.py filters out jobs
    with no url at all) so this demo job still surfaces in the UI with
    its "[DEMO DATA - ...]" label, rather than silently vanishing and
    leaving the user with zero jobs and no explanation of why.
    """
    return [
        {
            "title": f"[DEMO DATA - {reason}] {query} Engineer",
            "company": "Demo Company (not real)",
            "location": location or "Remote",
            "remote_type": "remote" if not location else "hybrid",
            "source": source,
            "url": "https://example.com/demo-job-set-jsearch-api-key",
            "description": f"This is placeholder data because: {reason}. "
                            f"Set JSEARCH_API_KEY in backend/.env to fetch real listings.",
            "salary_range": "N/A (demo data)",
            "posted_date": "",
            "required_skills": ["Python", "FastAPI", "LangGraph", "SQL", "Docker"],
        },
    ]


def send_notification(channel: str, title: str, body: str, config: Dict[str, Any]) -> bool:
    """Send a notification via email/Telegram/Discord.

    MCP equivalent: `notifications.send` tool call.
    """
    try:
        if channel == "telegram" and config.get("telegram_bot_token"):
            url = f"https://api.telegram.org/bot{config['telegram_bot_token']}/sendMessage"
            requests.post(url, json={
                "chat_id": config.get("telegram_chat_id"),
                "text": f"{title}\n\n{body}",
            }, timeout=10)
            return True

        if channel == "discord" and config.get("discord_webhook_url"):
            requests.post(config["discord_webhook_url"], json={
                "content": f"**{title}**\n{body}",
            }, timeout=10)
            return True

        if channel == "email" and config.get("smtp_user"):
            # Real implementation would use smtplib here.
            return True

        return False
    except Exception:
        return False
