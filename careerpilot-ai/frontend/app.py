"""
CareerPilot AI - Streamlit Frontend

A multi-page dashboard for:
  - Setting up / viewing the user profile
  - Running the autonomous agent pipeline
  - Reviewing & approving applications (human-in-the-loop)
  - Tracking application status and analytics

Run with: streamlit run frontend/app.py
Requires the FastAPI backend running at API_BASE_URL.
"""
import streamlit as st
import requests

API_BASE_URL = "http://localhost:8000"

st.set_page_config(page_title="CareerPilot AI", page_icon="🚀", layout="wide")

st.title("🚀 CareerPilot AI")
st.caption("Autonomous Multi-Agent Career Operating System")

# Session state for user_id and last run
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "thread_id" not in st.session_state:
    st.session_state.thread_id = None

tab_profile, tab_run, tab_approvals, tab_dashboard = st.tabs(
    ["👤 Profile", "🤖 Run Agents", "✅ Approvals", "📊 Dashboard"]
)

# ---------------------------------------------------------------------
# Profile tab
# ---------------------------------------------------------------------
with tab_profile:
    st.header("Profile Setup")

    with st.form("profile_form"):
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input("Name")
            email = st.text_input("Email")
            github_url = st.text_input("GitHub URL")
            linkedin_url = st.text_input("LinkedIn URL")
        with col2:
            portfolio_url = st.text_input("Portfolio URL")
            leetcode_url = st.text_input("LeetCode URL")
            kaggle_url = st.text_input("Kaggle URL")
            remote_pref = st.selectbox("Remote preference", ["remote", "hybrid", "onsite"])

        target_roles = st.text_input("Target roles (comma-separated)", "AI Engineer, Backend Engineer")
        preferred_locations = st.text_input("Preferred locations (comma-separated)", "Bangalore, Remote")
        min_salary = st.number_input("Minimum salary expectation", min_value=0, value=0, step=10000)
        resume_text = st.text_area("Resume text (paste content)", height=200)

        submitted = st.form_submit_button("Create / Update Profile")

    if submitted:
        payload = {
            "name": name, "email": email,
            "resume_text": resume_text,
            "github_url": github_url, "linkedin_url": linkedin_url,
            "portfolio_url": portfolio_url, "leetcode_url": leetcode_url,
            "kaggle_url": kaggle_url,
            "preferred_locations": [l.strip() for l in preferred_locations.split(",") if l.strip()],
            "remote_preference": remote_pref,
            "min_salary_expectation": int(min_salary),
            "target_roles": [r.strip() for r in target_roles.split(",") if r.strip()],
        }
        try:
            resp = requests.post(f"{API_BASE_URL}/profiles", json=payload, timeout=30)
            if resp.status_code == 200:
                profile = resp.json()
                st.session_state.user_id = profile["id"]
                st.success(f"Profile created with ID {profile['id']}")
            else:
                st.error(resp.json().get("detail", "Error creating profile"))
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend. Is the FastAPI server running on :8000?")

    st.divider()
    user_id_input = st.number_input("Or load existing profile by ID", min_value=1, step=1, value=1)
    if st.button("Load Profile"):
        try:
            resp = requests.get(f"{API_BASE_URL}/profiles/{user_id_input}", timeout=10)
            if resp.status_code == 200:
                st.session_state.user_id = int(user_id_input)
                st.json(resp.json())
            else:
                st.error("Profile not found")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend.")

# ---------------------------------------------------------------------
# Run Agents tab
# ---------------------------------------------------------------------
with tab_run:
    st.header("Run Autonomous Agent Pipeline")

    if not st.session_state.user_id:
        st.info("Set up or load a profile first in the Profile tab.")
    else:
        st.write(f"Active profile ID: **{st.session_state.user_id}**")
        task = st.text_area(
            "What should CareerPilot do?",
            value="Find me relevant AI Engineer jobs, score them, and prepare an "
                  "application package for the best match.",
            height=100,
        )

        if st.button("▶️ Run Pipeline", type="primary"):
            with st.spinner("Agents are working... (Planning → Scout → Rank → Skill Gap → "
                             "Resume → Cover Letter → Application Prep)"):
                try:
                    resp = requests.post(
                        f"{API_BASE_URL}/run",
                        json={"user_id": st.session_state.user_id, "task": task},
                        timeout=300,
                    )
                    if resp.status_code == 200:
                        result = resp.json()
                        st.session_state.thread_id = result["thread_id"]
                        st.success("Pipeline run complete.")

                        state = result["state"]
                        st.subheader("Execution Log")
                        for log in state.get("logs", []):
                            st.text(log)

                        if state.get("current_job"):
                            st.subheader("Top Matched Job")
                            top_job = state["current_job"]
                            if "[DEMO DATA" in (top_job.get("title") or ""):
                                st.error(
                                    "⚠️ **This is DEMO DATA, not a real job listing.** "
                                    "Set `JSEARCH_API_KEY` in `backend/.env` to fetch real jobs "
                                    "from LinkedIn, Indeed, Glassdoor, etc."
                                )
                            st.json(top_job)

                        if state.get("requires_approval"):
                            st.warning(
                                "⚠️ An application package is ready and awaiting your "
                                "approval. Go to the **Approvals** tab to review it."
                            )
                            st.json(state.get("approval_payload", {}))
                    else:
                        st.error(resp.text)
                except requests.exceptions.ConnectionError:
                    st.error("Cannot connect to backend.")

# ---------------------------------------------------------------------
# Approvals tab
# ---------------------------------------------------------------------
with tab_approvals:
    st.header("Human-in-the-Loop Approvals")
    st.caption("CareerPilot never submits applications automatically. "
               "Review and approve each package before applying yourself.")

    app_id = st.number_input("Application ID", min_value=1, step=1)

    if st.button("Load Application"):
        try:
            resp = requests.get(f"{API_BASE_URL}/applications/{int(app_id)}", timeout=10)
            if resp.status_code == 200:
                app_data = resp.json()
                st.session_state["loaded_app"] = app_data
            else:
                st.error("Application not found")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend.")

    if "loaded_app" in st.session_state:
        app_data = st.session_state["loaded_app"]

        if app_data.get("is_demo_data"):
            st.error(
                "⚠️ **This is DEMO DATA, not a real job.** "
                "Set `JSEARCH_API_KEY` in `backend/.env` to fetch real listings. "
                "Do not act on this application package."
            )

        st.subheader(f"{app_data.get('job_title', 'Unknown role')} @ {app_data.get('company', 'Unknown company')}")
        col_a, col_b, col_c = st.columns(3)
        col_a.metric("Match Score", f"{app_data.get('match_score', 0)}/100")
        col_b.metric("ATS Score", f"{app_data['ats_score']}/100")
        col_c.write(f"**Status:** {app_data['approval_status']}")

        st.write(f"**Recommended application method:** {app_data['application_method']}")
        if app_data.get("job_url"):
            st.markdown(f"**Apply link:** [{app_data['job_url']}]({app_data['job_url']})")
        else:
            st.warning("No apply link available for this job.")

        with st.expander("Tailored Resume", expanded=False):
            st.markdown(app_data["tailored_resume"])
        with st.expander("Cover Letter", expanded=False):
            st.markdown(app_data["cover_letter"])
        with st.expander("Outreach Messages", expanded=False):
            st.markdown(app_data["outreach_message"])

        col1, col2 = st.columns(2)
        with col1:
            if st.button("✅ Approve", type="primary"):
                resp = requests.post(
                    f"{API_BASE_URL}/applications/{app_data['id']}/decision",
                    json={"approve": True}, timeout=10,
                )
                st.success(resp.json().get("message"))
        with col2:
            if st.button("❌ Reject"):
                resp = requests.post(
                    f"{API_BASE_URL}/applications/{app_data['id']}/decision",
                    json={"approve": False}, timeout=10,
                )
                st.info(resp.json().get("message"))

# ---------------------------------------------------------------------
# Dashboard tab
# ---------------------------------------------------------------------
with tab_dashboard:
    st.header("Application Tracking Dashboard")

    if not st.session_state.user_id:
        st.info("Set up or load a profile first.")
    else:
        try:
            resp = requests.get(f"{API_BASE_URL}/users/{st.session_state.user_id}/dashboard", timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                col1, col2, col3 = st.columns(3)
                col1.metric("Total Jobs Tracked", data["total_jobs"])
                col2.metric("Statuses", len(data["status_breakdown"]))
                if data["top_matches"]:
                    col3.metric("Top Match Score", f"{data['top_matches'][0]['match_score']}/100")

                st.subheader("Status Breakdown")
                st.bar_chart(data["status_breakdown"])

                st.subheader("Top Matches")
                st.table(data["top_matches"])
            else:
                st.error("Could not load dashboard")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend.")

        st.divider()
        st.subheader("All Jobs")
        try:
            resp = requests.get(f"{API_BASE_URL}/users/{st.session_state.user_id}/jobs", timeout=10)
            if resp.status_code == 200:
                jobs = resp.json()
                for job in jobs:
                    is_demo = "[DEMO DATA" in (job.get("title") or "")
                    label_prefix = "🟡 DEMO " if is_demo else ""
                    with st.expander(f"{label_prefix}{job['title']} @ {job['company']} - {job['match_score']}/100 "
                                      f"[{job['status']}]"):
                        if is_demo:
                            st.error("⚠️ This is demo data, not a real job. Set JSEARCH_API_KEY for real listings.")
                        st.json(job)
                        new_status = st.selectbox(
                            "Update status", [
                                "discovered", "scored", "resume_ready", "awaiting_approval",
                                "approved", "applied", "assessment", "interview", "offer", "rejected",
                            ],
                            index=0, key=f"status_{job['id']}",
                        )
                        if st.button("Update", key=f"update_{job['id']}"):
                            r = requests.patch(
                                f"{API_BASE_URL}/jobs/{job['id']}/status",
                                json={"status": new_status, "note": "Updated from dashboard"},
                                timeout=10,
                            )
                            st.success(f"Status updated to {r.json()['status']}")
        except requests.exceptions.ConnectionError:
            st.error("Cannot connect to backend.")
