# CareerPilot AI — Autonomous Multi-Agent Career Operating System

An agentic AI platform that discovers, scores, prepares, and tracks job
applications on your behalf — with a **human-in-the-loop checkpoint before
any application is ever submitted.**

---

## 1. Architecture Overview

```
+-------------+     +------------------+     +-------------------------+
|  Streamlit  |---->|   FastAPI Backend |---->|   LangGraph Multi-Agent  |
|  Frontend   |<----|  (REST API layer) |<----|   Workflow (Supervisor)  |
+-------------+     +------------------+     +-------------------------+
                              |                          |
                     +--------+--------+        +--------+--------+
                     |  SQLite/Postgres |        |   ChromaDB (RAG) |
                     |  (structured DB) |        |  per-user vector |
                     +-----------------+         |     store       |
                                                  +-----------------+
                              |
                     +--------+--------+
                     |  MCP Tool Layer  |
                     | (GitHub, Job     |
                     |  Boards, Notify) |
                     +-----------------+
```

**LLM**: Gemini (default) or OpenAI, switchable via `LLM_PROVIDER` env var.
**Observability**: LangSmith tracing (enable via `LANGCHAIN_TRACING_V2=true`).

---

## 2. Folder Structure

```
careerpilot-ai/
├── backend/
│   ├── agents/                  # One file per agent (15 agents + supervisor/planning)
│   │   ├── base.py               # BaseAgent: logging, LLM access, run() interface
│   │   ├── supervisor.py         # Routes between agents
│   │   ├── planning.py           # Decomposes user task into agent plan
│   │   ├── profile_intelligence.py
│   │   ├── job_scout.py
│   │   ├── job_ranking.py
│   │   ├── skill_gap.py
│   │   ├── resume_optimization.py
│   │   ├── cover_letter.py
│   │   ├── application.py        # Human-in-the-loop checkpoint
│   │   ├── interview_prep.py
│   │   ├── tracking.py
│   │   ├── github_enhancement.py
│   │   ├── portfolio_enhancement.py
│   │   ├── networking.py
│   │   ├── notification.py
│   │   ├── learning.py           # Reflection / self-improvement loop
│   │   └── salary_intelligence.py
│   ├── core/
│   │   ├── config.py             # Settings (env vars)
│   │   ├── llm.py                # LLM/embeddings factory (Gemini/OpenAI)
│   │   ├── state.py              # Shared LangGraph state schema
│   │   └── graph.py              # LangGraph workflow definition
│   ├── db/
│   │   ├── models.py             # SQLAlchemy ORM models (full schema)
│   │   └── session.py            # DB session management
│   ├── rag/
│   │   └── store.py               # ChromaDB per-user vector store wrapper
│   ├── mcp_servers/
│   │   ├── client_helpers.py     # MCP-tool-shaped functions (swappable)
│   │   └── jobboard_server_design.py  # MCP server design doc/stub
│   ├── utils/
│   │   └── resume_parser.py      # PDF/text extraction
│   ├── api/
│   │   ├── main.py                # FastAPI app & routes
│   │   └── schemas.py             # Pydantic request/response models
│   └── requirements.txt
├── frontend/
│   └── app.py                     # Streamlit dashboard (4 tabs)
├── docker/
│   ├── Dockerfile.backend
│   ├── Dockerfile.frontend
│   └── docker-compose.yml
└── tests/
```

---

## 3. Database Schema

| Table | Purpose |
|---|---|
| `user_profiles` | Profile data: skills, experience, projects, education, certs, achievements, preferences |
| `jobs` | Discovered jobs with match scores, score breakdowns, and pipeline status |
| `skill_gaps` | Per-job missing skills/certs/tech + learning recommendations |
| `applications` | Tailored resume, cover letter, outreach message, ATS score, approval status |
| `interview_prep` | Company research, technical/behavioral questions, DSA roadmap |
| `tracking_events` | Audit trail of status changes per job |
| `agent_runs` | Execution log of every agent run (for observability + Learning Agent) |
| `notifications` | Sent notification history |

Job status lifecycle:
```
discovered -> scored -> resume_ready -> awaiting_approval -> approved
  -> applied -> assessment -> interview -> offer / rejected
```

---

## 4. LangGraph Workflow

```
        +-----------+
START ->| planning  |  (decomposes task into agent plan)
        +-----+-----+
              |
              v
        +-----------+
   +--->|supervisor |<------------------------+
   |    +-----+-----+                         |
   |          | routes to one agent           |
   |          v                               |
   |  profile_intelligence / job_scout /      |
   |  job_ranking / skill_gap /               |
   |  resume_optimization / cover_letter /    |
   |  application / interview_prep / tracking |
   |          |                               |
   |          +-------------------------------+
   |
   +-- next_agent == "FINISH" --> END
```

* **Supervisor** (LLM-routed): decides the next agent based on current state.
* **Human-in-the-loop**: the `application` agent sets
  `requires_approval=True, approval_status="pending"`. The supervisor sees
  this and routes to `END`, **pausing** the graph (via `MemorySaver`
  checkpointer). The user approves/rejects via
  `POST /applications/{id}/decision`, and the graph can be resumed via
  `POST /run/{thread_id}/resume`.
* **Never auto-applies**: `ApplicationAgent` only *prepares* the package.

---

## 5. MCP Integration Design

`backend/mcp_servers/client_helpers.py` defines tool-shaped functions
(`fetch_github_profile`, `search_jobs_external`, `send_notification`) with
the exact signatures an MCP server would expose. `jobboard_server_design.py`
documents the intended standalone MCP server (using the `mcp` Python SDK)
for job board search. Swapping mock implementations for real MCP client
calls requires **no agent code changes** — only replacing the function
bodies.

---

## 6. RAG Architecture

* Each user gets a dedicated ChromaDB collection (`user_{id}_docs`).
* `ProfileIntelligenceAgent` indexes resume text + project descriptions on
  profile creation/update.
* `ResumeOptimizationAgent` retrieves top-k relevant chunks (via the job's
  title + required skills as the query) to ground tailored resume content.
* Embeddings come from the same provider as the LLM (Gemini or OpenAI).

---

## 7. Memory Architecture

* **Short-term**: `CareerPilotState` (TypedDict) passed through the graph
  for one run — current job, scores, generated artifacts.
* **Long-term**: PostgreSQL/SQLite (`UserProfile`, `Job`, `Application`,
  etc.) persists across runs.
* **Semantic memory**: ChromaDB vector store for RAG over personal docs.
* **Checkpointed graph state**: LangGraph `MemorySaver` enables pause/resume
  for human-in-the-loop (swap for `PostgresSaver` in production).

---

## 8. API Design (key endpoints)

| Method | Path | Purpose |
|---|---|---|
| POST | `/profiles` | Create user profile |
| GET | `/profiles/{id}` | Fetch profile |
| POST | `/profiles/{id}/resume` | Upload resume (PDF/text) |
| POST | `/run` | Start agentic workflow run |
| POST | `/run/{thread_id}/resume` | Resume a paused workflow |
| POST | `/applications/{id}/decision` | Approve/reject application package |
| GET | `/users/{id}/jobs` | List tracked jobs |
| GET | `/users/{id}/dashboard` | Tracking analytics |
| PATCH | `/jobs/{id}/status` | Manually update job status |
| GET | `/applications/{id}` | Fetch full application package |

---

## 9. Setup & Run

### Local (without Docker)

```bash
cd careerpilot-ai/backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GOOGLE_API_KEY or OPENAI_API_KEY

# Terminal 1: backend (from project root)
uvicorn backend.api.main:app --reload --port 8000

# Terminal 2: frontend (from project root)
streamlit run frontend/app.py
```

### Docker

```bash
cd careerpilot-ai/docker
docker compose up --build
```
Backend: http://localhost:8000 · Frontend: http://localhost:8501

---

## 10. Security & Production Notes

* Never commit `.env` — use secrets managers in production.
* `application` agent enforces human approval; do not bypass this gate.
* Replace `MemorySaver` with a persistent checkpointer (Postgres) for
  production-grade pause/resume across restarts.
* Add authentication (JWT/OAuth) to all API routes before exposing publicly.
* Rate-limit and sandbox MCP tool calls that hit external services.
* Sanitize/validate uploaded resume files (size limits, type checks).

---

## 11. Implementation Roadmap

1. DONE - Core schema, config, LLM factory, base agent
2. DONE - Supervisor + Planning agents (LangGraph orchestration)
3. DONE - Profile Intelligence + RAG indexing
4. DONE - Job Scout (MCP-shaped) + Job Ranking (scoring engine)
5. DONE - Skill Gap, Resume Optimization, Cover Letter agents
6. DONE - Application agent with human-in-the-loop checkpoint
7. DONE - Interview Prep, Tracking, GitHub/Portfolio Enhancement, Networking,
   Notification, Learning, Salary Intelligence agents
8. DONE - FastAPI REST layer + Streamlit dashboard
9. DONE - Docker + docker-compose
10. NEXT - Real job-board MCP server (replace mocks), persistent
    checkpointer, auth, scheduled notification jobs (APScheduler),
    CI/CD pipeline, automated tests
