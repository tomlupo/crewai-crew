"""Shared database and file helpers for the content crew."""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("output/history.db")

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
            duration_seconds REAL,
            crew_type TEXT NOT NULL DEFAULT 'content'
        )
        """
    )
    # Migration for existing databases missing the crew_type column
    try:
        conn.execute(
            "ALTER TABLE tasks ADD COLUMN crew_type TEXT NOT NULL DEFAULT 'content'"
        )
    except sqlite3.OperationalError:
        pass  # Column already exists
    conn.commit()
    conn.close()


def save_task(
    description,
    content_type,
    platform,
    include_seo,
    include_social,
    crew_type="content",
):
    """Save a new task to the database. Returns the task ID."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.execute(
        "INSERT INTO tasks (created_at, description, content_type, platform, "
        "include_seo, include_social, crew_type) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (
            datetime.now(timezone.utc).isoformat(),
            description,
            content_type,
            platform,
            int(include_seo),
            int(include_social),
            crew_type,
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
