from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, ListFlowable, ListItem, HRFlowable
)

styles = getSampleStyleSheet()

title_style = ParagraphStyle(
    "TitleCustom", parent=styles["Title"], fontSize=22, spaceAfter=6,
    textColor=colors.HexColor("#1a1a2e")
)
subtitle_style = ParagraphStyle(
    "SubtitleCustom", parent=styles["Normal"], fontSize=12,
    textColor=colors.HexColor("#555555"), spaceAfter=14
)
section_style = ParagraphStyle(
    "SectionHeader", parent=styles["Heading1"], fontSize=15,
    textColor=colors.white, backColor=colors.HexColor("#16213e"),
    spaceBefore=14, spaceAfter=8, leftIndent=6, borderPadding=6,
)
agent_name_style = ParagraphStyle(
    "AgentName", parent=styles["Heading2"], fontSize=12.5,
    textColor=colors.HexColor("#0f3460"), spaceBefore=10, spaceAfter=2,
)
body_style = ParagraphStyle(
    "BodyCustom", parent=styles["Normal"], fontSize=9.5, leading=13.5,
    textColor=colors.HexColor("#222222"),
)
label_style = ParagraphStyle(
    "LabelCustom", parent=styles["Normal"], fontSize=9, leading=13,
    textColor=colors.HexColor("#0f3460"), spaceBefore=2,
)
tool_tag_style = ParagraphStyle(
    "ToolTag", parent=styles["Normal"], fontSize=8.5, leading=12,
    textColor=colors.HexColor("#e94560"), fontName="Helvetica-Oblique",
)

doc = SimpleDocTemplate(
    "/home/claude/careerpilot-ai/CareerPilot_AI_Agents_and_Tools.pdf",
    pagesize=letter,
    leftMargin=0.7 * inch, rightMargin=0.7 * inch,
    topMargin=0.7 * inch, bottomMargin=0.7 * inch,
)

story = []

# ---------------- COVER ----------------
story.append(Paragraph("CareerPilot AI", title_style))
story.append(Paragraph("Autonomous Multi-Agent Career Operating System", subtitle_style))
story.append(Paragraph(
    "Agent Roster &amp; Technology Stack Reference", subtitle_style
))
story.append(HRFlowable(width="100%", color=colors.HexColor("#16213e"), thickness=1.2))
story.append(Spacer(1, 12))

story.append(Paragraph(
    "This document summarizes the 15 specialist agents plus the 2 orchestration "
    "agents (Supervisor and Planning) implemented in CareerPilot AI, along with "
    "the responsibilities of each agent and the underlying tools, frameworks, "
    "and integrations used across the project.",
    body_style
))
story.append(Spacer(1, 14))

# ---------------- SUMMARY TABLE ----------------
story.append(Paragraph("Agent Count Summary", section_style))
summary_data = [
    ["Category", "Count", "Examples"],
    ["Orchestration Agents", "2", "Supervisor, Planning"],
    ["Profile & Career Asset Agents", "4", "Profile Intelligence, GitHub Enhancement,\nPortfolio Enhancement, Resume Optimization"],
    ["Job Discovery & Evaluation Agents", "3", "Job Scout, Job Ranking, Skill Gap"],
    ["Application Pipeline Agents", "3", "Cover Letter, Application, Tracking"],
    ["Growth & Support Agents", "5", "Networking, Interview Prep, Notification,\nLearning, Salary Intelligence"],
    ["TOTAL AGENTS", "17", "2 orchestration + 15 specialist"],
]
summary_table = Table(summary_data, colWidths=[2.3 * inch, 0.8 * inch, 3.4 * inch])
summary_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
    ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#e8eaf6")),
    ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, colors.HexColor("#f5f6fa")]),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
]))
story.append(summary_table)
story.append(Spacer(1, 14))

# ---------------- TECH STACK ----------------
story.append(Paragraph("Core Technology Stack", section_style))
tech_data = [
    ["Layer", "Technology"],
    ["Agent Orchestration", "LangGraph (StateGraph, conditional edges, MemorySaver checkpointer)"],
    ["LLM Framework", "LangChain"],
    ["LLM Providers", "Google Gemini (default: gemini-1.5-pro) / OpenAI (gpt-4o-mini) - switchable via LLM_PROVIDER"],
    ["Backend API", "FastAPI (REST endpoints, Pydantic schemas)"],
    ["Frontend", "Streamlit (4-tab dashboard)"],
    ["Database", "SQLite (default) / PostgreSQL via SQLAlchemy ORM"],
    ["Vector Store (RAG)", "ChromaDB - per-user persistent collections"],
    ["Embeddings", "Google Generative AI Embeddings / OpenAI Embeddings"],
    ["Tool Integration", "Model Context Protocol (MCP) - tool-shaped client helpers + server design"],
    ["Observability", "LangSmith tracing (LANGCHAIN_TRACING_V2)"],
    ["Containerization", "Docker + docker-compose (separate backend/frontend services)"],
    ["File Parsing", "pypdf (resume PDF text extraction)"],
    ["Notifications", "Email (SMTP) / Telegram Bot API / Discord Webhooks"],
    ["External Data", "GitHub REST API (repo analysis)"],
    ["Scheduling (planned)", "APScheduler (daily/weekly notification jobs)"],
]
tech_table = Table(tech_data, colWidths=[1.8 * inch, 4.7 * inch])
tech_table.setStyle(TableStyle([
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16213e")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
    ("FONTNAME", (0, 1), (0, -1), "Helvetica-Bold"),
    ("FONTSIZE", (0, 0), (-1, -1), 8.5),
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cccccc")),
    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f6fa")]),
    ("TOPPADDING", (0, 0), (-1, -1), 4.5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4.5),
]))
story.append(tech_table)

story.append(PageBreak())

# ---------------- AGENT DETAILS ----------------
story.append(Paragraph("Orchestration Agents", section_style))

orchestration_agents = [
    {
        "name": "1. Supervisor Agent",
        "desc": "Top-level router in the LangGraph workflow. Reads the current "
                "state (task, plan, completed steps, whether a job is selected, "
                "whether skill gap / resume / cover letter are ready, approval "
                "status) and decides which specialist agent runs next via an "
                "LLM call. Halts the graph (routes to FINISH) when an application "
                "is awaiting human approval.",
        "tools": "LLM (Gemini/OpenAI) for routing decisions; reads CareerPilotState",
    },
    {
        "name": "2. Planning Agent",
        "desc": "Decomposes the user's natural-language request into an ordered "
                "JSON list of agent names to execute (e.g. job_scout -> "
                "job_ranking -> skill_gap -> resume_optimization -> "
                "cover_letter -> application). Runs once at the start of every "
                "workflow invocation; the Supervisor uses this plan as guidance.",
        "tools": "LLM (Gemini/OpenAI) for plan generation; JSON output parsing",
    },
]

for agent in orchestration_agents:
    story.append(Paragraph(agent["name"], agent_name_style))
    story.append(Paragraph(agent["desc"], body_style))
    story.append(Paragraph(f"Tools used: {agent['tools']}", tool_tag_style))

story.append(Spacer(1, 8))
story.append(Paragraph("Specialist Agents", section_style))

specialist_agents = [
    {
        "name": "3. Profile Intelligence Agent",
        "desc": "Collects and analyzes resume text and external profile data "
                "(GitHub, LinkedIn, portfolio, LeetCode, Kaggle). Uses the LLM "
                "to extract structured data: skills, experience, projects, "
                "education, certifications, and achievements. Persists this "
                "to the UserProfile table and indexes resume/project text into "
                "the per-user ChromaDB collection for later RAG retrieval.",
        "tools": "LLM extraction (Gemini/OpenAI); GitHub REST API (via MCP-shaped "
                 "fetch_github_profile); ChromaDB vector store; pypdf for resume parsing; "
                 "SQLAlchemy persistence",
    },
    {
        "name": "4. Job Scout Agent",
        "desc": "Generates optimized job-search queries from the user's skills, "
                "target roles, and location preferences using the LLM, then "
                "searches configured job boards (LinkedIn, Indeed, Wellfound, "
                "Naukri, Internshala, Glassdoor, company career pages). "
                "Deduplicates and persists newly discovered jobs to the database.",
        "tools": "LLM for query generation; MCP-shaped job board search tool "
                 "(search_jobs_external - mock data, swappable for real job board "
                 "API/MCP server); SQLAlchemy persistence",
    },
    {
        "name": "5. Job Ranking Agent",
        "desc": "Scores every discovered job 0-100 using a weighted formula "
                "covering skill match (40%), experience match (15%), location "
                "match (15%), remote preference match (10%), salary match "
                "(10%), and company quality (10%). Sorts jobs by score and "
                "selects the top match as the 'current_job' for the per-job "
                "pipeline (skill gap -> resume -> cover letter -> application).",
        "tools": "Custom rule-based scoring engine (Python heuristics, regex for "
                 "salary parsing); SQLAlchemy persistence",
    },
    {
        "name": "6. Skill Gap Agent",
        "desc": "Compares the current job's required skills/description against "
                "the candidate's profile. Identifies missing skills, missing "
                "certifications, and missing technologies, and generates "
                "prioritized learning recommendations (course/doc/project/cert, "
                "with high/medium/low priority).",
        "tools": "LLM for gap analysis and JSON-structured recommendations; "
                 "SQLAlchemy persistence (SkillGap table)",
    },
    {
        "name": "7. Resume Optimization Agent",
        "desc": "Tailors the candidate's resume for the current job: retrieves "
                "relevant project/experience chunks from the RAG vector store "
                "(query = job title + required skills), then asks the LLM to "
                "rewrite/reorganize resume content emphasizing matching skills "
                "and incorporating job-relevant keywords for ATS scanning. "
                "Estimates an ATS keyword-coverage score.",
        "tools": "LLM for resume rewriting; ChromaDB RAG retrieval (PersonalDocStore); "
                 "regex-based ATS score estimation",
    },
    {
        "name": "8. Cover Letter Agent",
        "desc": "Generates a tailored cover letter (under 350 words) referencing "
                "1-2 relevant projects/experiences, plus three short outreach "
                "message templates: recruiter outreach, referral request, and "
                "general networking message - all personalized to the target "
                "job and company.",
        "tools": "LLM (two prompts: cover letter generation + outreach message generation)",
    },
    {
        "name": "9. GitHub Enhancement Agent",
        "desc": "Analyzes the user's public GitHub repositories and suggests "
                "improvements: better READMEs, missing documentation, whether "
                "an architecture diagram would help, missing tests, "
                "Dockerization opportunities, and CI/CD pipeline suggestions.",
        "tools": "GitHub REST API (via MCP-shaped fetch_github_profile); LLM for "
                 "improvement suggestions",
    },
    {
        "name": "10. Portfolio Enhancement Agent",
        "desc": "Analyzes the candidate's portfolio/projects relative to their "
                "skills and target roles. Suggests new project ideas, better "
                "project descriptions (impact/metrics focus), SEO improvements, "
                "technical blog topics, and personal branding suggestions "
                "(tagline, about-section angle).",
        "tools": "LLM for portfolio analysis and content suggestions",
    },
    {
        "name": "11. Networking Agent",
        "desc": "For the current job/company, generates a LinkedIn search "
                "strategy (job titles/keywords to find recruiters, hiring "
                "managers, and alumni) plus personalized outreach message "
                "templates for a recruiter, a hiring manager/team lead, and an "
                "alumni connection. Keeps the human in control of actual outreach.",
        "tools": "LLM for strategy and message-template generation",
    },
    {
        "name": "12. Application Agent",
        "desc": "Prepares the final application package (tailored resume + "
                "cover letter + outreach message + recommended application "
                "method: easy_apply / company_portal / email) and persists it "
                "as a pending Application record. CRITICAL: never submits an "
                "application automatically - always sets requires_approval=True "
                "and approval_status='pending', pausing the LangGraph workflow "
                "at a human-in-the-loop checkpoint until the user explicitly "
                "approves or rejects via the API.",
        "tools": "SQLAlchemy persistence (Application, Job tables); LangGraph "
                 "human-in-the-loop pause/resume (MemorySaver checkpointer); "
                 "rule-based application-method recommendation",
    },
    {
        "name": "13. Interview Preparation Agent",
        "desc": "For shortlisted jobs, generates company research summaries, "
                "6-8 likely technical interview questions, 5 behavioral/STAR "
                "questions, a prioritized DSA topic roadmap, and a mock "
                "interview opening script - all tailored to the job description "
                "and the candidate's existing skill gaps.",
        "tools": "LLM for structured JSON prep-material generation; SQLAlchemy "
                 "persistence (InterviewPrep table)",
    },
    {
        "name": "14. Tracking Agent",
        "desc": "Updates and reports on application status across the full "
                "lifecycle (discovered -> scored -> resume_ready -> "
                "awaiting_approval -> approved -> applied -> assessment -> "
                "interview -> offer/rejected). Computes dashboard analytics: "
                "total jobs, status breakdown, applied count, interview count, "
                "and application-to-interview conversion rate.",
        "tools": "SQLAlchemy persistence (Job, TrackingEvent tables); Python "
                 "Counter for analytics aggregation",
    },
    {
        "name": "15. Notification Agent",
        "desc": "Prepares and sends daily summaries covering new jobs "
                "discovered, applications awaiting approval, and active "
                "interview processes. Supports multiple channels and logs "
                "every notification attempt.",
        "tools": "MCP-shaped send_notification helper; Telegram Bot API; Discord "
                 "Webhooks; SMTP (email - stub); SQLAlchemy persistence "
                 "(Notification table)",
    },
    {
        "name": "16. Learning Agent",
        "desc": "Implements the reflection / self-improvement loop. Analyzes all "
                "rejected jobs and their associated skill gaps, identifies the "
                "top recurring missing skills/technologies across rejections, "
                "and produces a revised prioritized learning plan plus job-search "
                "strategy adjustments (e.g. target different seniority levels, "
                "locations, or role types).",
        "tools": "LLM for reflective analysis; Python Counter for frequency "
                 "ranking of recurring skill gaps; SQLAlchemy queries (Job, SkillGap)",
    },
    {
        "name": "17. Salary Intelligence Agent",
        "desc": "Provides an estimated market salary range for the current "
                "job's role/location/experience level, compares it against the "
                "job's posted salary range, and generates 3-4 specific salary "
                "negotiation talking points tailored to the candidate's "
                "strengths (skills and achievements).",
        "tools": "LLM for market salary estimation and negotiation guidance "
                 "(framed as general estimates, not live market data)",
    },
]

for agent in specialist_agents:
    story.append(Paragraph(agent["name"], agent_name_style))
    story.append(Paragraph(agent["desc"], body_style))
    story.append(Paragraph(f"Tools used: {agent['tools']}", tool_tag_style))

story.append(Spacer(1, 12))
story.append(HRFlowable(width="100%", color=colors.HexColor("#cccccc"), thickness=0.7))
story.append(Spacer(1, 6))
story.append(Paragraph(
    "Note: All agents inherit from a common BaseAgent class (backend/agents/base.py) "
    "which provides LLM access, a standardized run(state) -> partial_state_update "
    "interface for LangGraph nodes, and automatic execution logging to the "
    "AgentRun table (used for observability and by the Learning Agent).",
    ParagraphStyle("Footnote", parent=styles["Normal"], fontSize=8, leading=11,
                    textColor=colors.HexColor("#777777"))
))

doc.build(story)
print("PDF generated successfully.")
