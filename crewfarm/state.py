"""
SQLite state tracking for CrewAI workflows.

Antfarm pattern: SQLite database at ~/.openclaw/antfarm/antfarm.db tracks
every run, step, and story. We replicate this for CrewAI.

Tables:
  - runs: workflow-level tracking (id, name, status, timestamps)
  - steps: step-level tracking (id, run_id, agent, input, output, status, timing)
"""

import sqlite3
import uuid
import json
from datetime import datetime, timezone
from pathlib import Path


class StateTracker:
    """
    SQLite-backed state tracker for CrewAI workflow runs.

    Usage:
        tracker = StateTracker("crewfarm_db.sqlite")
        run_id = tracker.create_run("fund-analysis", "Screen Polish equity funds")
        tracker.log_step(run_id, "screen", "Fund Screener", ...)
        tracker.complete_run(run_id)
    """

    def __init__(self, db_path: str = "crewfarm_db.sqlite"):
        self.db_path = Path(db_path)
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row
        self._init_tables()

    def _init_tables(self):
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS runs (
                id TEXT PRIMARY KEY,
                workflow_name TEXT NOT NULL,
                task_description TEXT,
                status TEXT NOT NULL DEFAULT 'running',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                metadata TEXT
            );

            CREATE TABLE IF NOT EXISTS steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_id TEXT NOT NULL REFERENCES runs(id),
                step_id TEXT NOT NULL,
                agent_name TEXT NOT NULL,
                input_text TEXT,
                output_text TEXT,
                parsed_output TEXT,
                status TEXT NOT NULL,
                duration_seconds REAL,
                attempt INTEGER DEFAULT 1,
                error TEXT,
                created_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_steps_run_id ON steps(run_id);
            CREATE INDEX IF NOT EXISTS idx_steps_status ON steps(status);
            CREATE INDEX IF NOT EXISTS idx_runs_status ON runs(status);
        """)
        self.conn.commit()

    def create_run(self, workflow_name: str, task_description: str = "") -> str:
        """Create a new workflow run. Returns run_id."""
        run_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO runs (id, workflow_name, task_description, status, created_at) "
            "VALUES (?, ?, ?, 'running', ?)",
            (run_id, workflow_name, task_description, now),
        )
        self.conn.commit()
        return run_id

    def log_step(
        self,
        run_id: str,
        step_id: str,
        agent_name: str,
        input_text: str,
        output_text: str,
        status: str,
        duration: float = 0,
        attempt: int = 1,
        error: str | None = None,
    ):
        """Log a step execution to the database."""
        from crewfarm.verification import extract_key_values

        parsed = extract_key_values(output_text) if output_text else {}
        now = datetime.now(timezone.utc).isoformat()

        self.conn.execute(
            "INSERT INTO steps "
            "(run_id, step_id, agent_name, input_text, output_text, parsed_output, "
            "status, duration_seconds, attempt, error, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run_id,
                step_id,
                agent_name,
                input_text,
                output_text,
                json.dumps(parsed),
                status,
                duration,
                attempt,
                error,
                now,
            ),
        )
        self.conn.commit()

    def complete_run(self, run_id: str, status: str = "done"):
        """Mark a run as completed."""
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE runs SET status = ?, completed_at = ? WHERE id = ?",
            (status, now, run_id),
        )
        self.conn.commit()

    def get_run(self, run_id: str) -> dict | None:
        """Get run details."""
        row = self.conn.execute("SELECT * FROM runs WHERE id = ?", (run_id,)).fetchone()
        return dict(row) if row else None

    def get_steps(self, run_id: str) -> list[dict]:
        """Get all steps for a run, ordered by creation time."""
        rows = self.conn.execute(
            "SELECT * FROM steps WHERE run_id = ? ORDER BY created_at",
            (run_id,),
        ).fetchall()
        return [dict(r) for r in rows]

    def get_last_successful_output(self, run_id: str, step_id: str) -> dict | None:
        """Get the last successful output for a step in a run."""
        row = self.conn.execute(
            "SELECT parsed_output FROM steps "
            "WHERE run_id = ? AND step_id = ? AND status = 'done' "
            "ORDER BY created_at DESC LIMIT 1",
            (run_id, step_id),
        ).fetchone()
        if row and row["parsed_output"]:
            return json.loads(row["parsed_output"])
        return None

    def get_run_summary(self, run_id: str) -> dict:
        """
        Get a summary of a run: total steps, passed, failed, total duration.
        Equivalent to `antfarm workflow status <run-id>`.
        """
        steps = self.get_steps(run_id)
        run = self.get_run(run_id)

        summary = {
            "run_id": run_id,
            "workflow": run["workflow_name"] if run else "unknown",
            "status": run["status"] if run else "unknown",
            "total_steps": len(set(s["step_id"] for s in steps)),
            "total_attempts": len(steps),
            "passed": len([s for s in steps if s["status"] == "done"]),
            "failed": len([s for s in steps if s["status"] == "failed"]),
            "errors": len([s for s in steps if s["status"] == "error"]),
            "escalated": len([s for s in steps if s["status"] == "escalated"]),
            "total_duration": sum(s["duration_seconds"] or 0 for s in steps),
        }

        # Per-step breakdown
        step_ids = list(dict.fromkeys(s["step_id"] for s in steps))
        summary["steps"] = []
        for sid in step_ids:
            step_entries = [s for s in steps if s["step_id"] == sid]
            last = step_entries[-1]
            summary["steps"].append(
                {
                    "step_id": sid,
                    "agent": last["agent_name"],
                    "status": last["status"],
                    "attempts": len(step_entries),
                    "duration": sum(s["duration_seconds"] or 0 for s in step_entries),
                }
            )

        return summary

    def print_status(self, run_id: str):
        """
        Print run status in Antfarm style.

        Mimics:
            antfarm workflow status "Screen Polish funds"
            Run: a1fdf573
            Steps:
              [done ] screen (Fund Screener)
              [done ] verify (Verifier)
              [running] analyze (Attribution Analyst)
        """
        summary = self.get_run_summary(run_id)

        print(f"\nRun: {summary['run_id']}")
        print(f"Workflow: {summary['workflow']}")
        print(f"Status: {summary['status']}")
        print("Steps:")
        for step in summary["steps"]:
            status_icon = {
                "done": "done ",
                "failed": "FAIL ",
                "error": "ERROR",
                "escalated": "ESCAL",
                "running": "run  ",
            }.get(step["status"], step["status"][:5])
            attempts_str = (
                f" ({step['attempts']} attempts)" if step["attempts"] > 1 else ""
            )
            print(
                f"  [{status_icon}] {step['step_id']} ({step['agent']}){attempts_str}"
            )
        print(f"\nTotal time: {summary['total_duration']:.1f}s")

    def close(self):
        self.conn.close()
