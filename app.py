"""Streamlit web UI for the content/marketing crew."""

import time

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.crew import run_content_crew
from src.db import (
    is_html_output,
    strip_code_fences,
    save_output_file,
    init_db,
    save_task,
    update_task,
    get_history,
    get_task_by_id,
)

# --- Streamlit App ---

st.set_page_config(page_title="Content Crew", page_icon="📝", layout="wide")
st.title("📝 Content Crew")
st.caption("Multi-agent content creation powered by CrewAI + Claude")

init_db()

# Sidebar — History
with st.sidebar:
    st.header("History")
    history = get_history()
    if not history:
        st.info("No tasks yet. Submit one to get started.")
    for task in history:
        status_icon = (
            "✅"
            if task["status"] == "complete"
            else ("❌" if task["status"] == "error" else "⏳")
        )
        if st.button(
            f"{status_icon} {task['description'][:50]}...",
            key=f"hist_{task['id']}",
        ):
            st.session_state["view_task_id"] = task["id"]

# Main area
if "view_task_id" in st.session_state:
    # Viewing a past task
    task = get_task_by_id(st.session_state["view_task_id"])
    if task:
        st.subheader(task["description"])
        col1, col2, col3 = st.columns(3)
        col1.metric("Type", task["content_type"])
        col2.metric("Platform", task["platform"])
        col3.metric(
            "Duration",
            f"{task['duration_seconds']:.0f}s" if task["duration_seconds"] else "—",
        )
        st.markdown("---")
        if task["result"] and is_html_output(task["content_type"], task["result"]):
            clean = strip_code_fences(task["result"])
            st.components.v1.html(clean, height=800, scrolling=True)
            st.download_button(
                "📥 Download HTML",
                data=clean,
                file_name=f"crew-output-{task['id']}.html",
                mime="text/html",
            )
        else:
            st.markdown(task["result"] or "*No result yet*")
    if st.button("← Back to new task"):
        del st.session_state["view_task_id"]
        st.rerun()
else:
    # New task form
    with st.form("task_form"):
        description = st.text_area(
            "What do you need?",
            placeholder="Research AI coding tools and write a blog post about them",
            height=100,
        )

        col1, col2 = st.columns(2)
        with col1:
            content_type = st.selectbox(
                "Content type",
                [
                    "blog post",
                    "landing page",
                    "Twitter/X thread",
                    "LinkedIn post",
                    "newsletter",
                    "report",
                ],
            )
            platform = st.selectbox(
                "Platform",
                ["blog", "website", "twitter", "linkedin", "newsletter", "internal"],
            )
        with col2:
            include_seo = st.checkbox("Include SEO optimization", value=True)
            include_social = st.checkbox("Include social monitoring", value=False)

        submitted = st.form_submit_button("🚀 Run Crew", type="primary")

    if submitted and description:
        task_id = save_task(
            description, content_type, platform, include_seo, include_social
        )

        with st.status("Crew is working...", expanded=True) as status:
            st.write("Editor-in-Chief is analyzing the task...")
            start_time = time.time()

            try:
                result = run_content_crew(
                    task_description=description,
                    content_type=content_type,
                    platform=platform,
                    include_seo=include_seo,
                    include_social=include_social,
                )
                duration = time.time() - start_time
                update_task(task_id, result, "complete", duration)
                status.update(label="Crew finished!", state="complete")
            except Exception as e:
                duration = time.time() - start_time
                update_task(task_id, str(e), "error", duration)
                status.update(label="Crew encountered an error", state="error")
                st.error(f"Error: {e}")
                result = None

        if result:
            st.markdown("---")
            st.subheader("Result")

            filepath = save_output_file(result, content_type, task_id)
            html_output = is_html_output(content_type, result)

            if html_output:
                clean_html = strip_code_fences(result)
                st.components.v1.html(clean_html, height=800, scrolling=True)
                st.download_button(
                    "📥 Download HTML",
                    data=clean_html,
                    file_name=filepath.name,
                    mime="text/html",
                )
            else:
                st.markdown(result)
                st.download_button(
                    "📥 Download Markdown",
                    data=result,
                    file_name=filepath.name,
                    mime="text/markdown",
                )

            st.success(f"Saved to {filepath}")
