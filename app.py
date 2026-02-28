"""Streamlit web UI for the content/marketing crew."""

import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.crew import run_content_crew

HTML_CONTENT_TYPES = {"landing page", "html page", "webpage", "website"}


def is_html_output(content_type: str, result: str) -> bool:
    """Check if the crew output is HTML."""
    return (
        content_type in HTML_CONTENT_TYPES
        or "<!doctype html>" in result[:300].lower()
        or "<html" in result[:300].lower()
    )


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences if the model wrapped the output."""
    t = text.strip()
    if t.startswith("```html"):
        t = t[7:].strip()
    elif t.startswith("```"):
        t = t[3:].strip()
    if t.endswith("```"):
        t = t[:-3].strip()
    return t


def save_output_file(result: str, content_type: str, task_id: int) -> Path:
    """Save crew output to a file in output/."""
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    if is_html_output(content_type, result):
        result = strip_code_fences(result)
        filepath = output_dir / f"crew-output-{task_id}.html"
    else:
        filepath = output_dir / f"crew-output-{task_id}.md"
    filepath.write_text(result, encoding="utf-8")
    return filepath


DB_PATH = Path("output/history.db")


def init_db():
    """Create the history database if it doesn't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            description TEXT NOT NULL,
            content_type TEXT NOT NULL,
            platform TEXT NOT NULL,
            include_seo INTEGER NOT NULL,
            include_social INTEGER NOT NULL,
            result TEXT,
            status TEXT NOT NULL DEFAULT 'running',
            duration_seconds REAL
        )
        """
    )
    conn.commit()
    conn.close()


def save_task(description, content_type, platform, include_seo, include_social):
    """Save a new task to the database. Returns the task ID."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.execute(
        "INSERT INTO tasks (created_at, description, content_type, platform, "
        "include_seo, include_social) VALUES (?, ?, ?, ?, ?, ?)",
        (
            datetime.now(timezone.utc).isoformat(),
            description,
            content_type,
            platform,
            int(include_seo),
            int(include_social),
        ),
    )
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id


def update_task(task_id, result, status, duration):
    """Update a task with its result."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "UPDATE tasks SET result = ?, status = ?, duration_seconds = ? WHERE id = ?",
        (result, status, duration, task_id),
    )
    conn.commit()
    conn.close()


def get_history():
    """Get all past tasks."""
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM tasks ORDER BY created_at DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_task_by_id(task_id):
    """Get a specific task by ID."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


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
