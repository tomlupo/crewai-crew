"""
Isolated execution engine for CrewAI tasks.

Antfarm pattern: each agent gets a fresh session with clean context.
We replicate this by running each task as a separate Crew.kickoff()
and passing only parsed KEY: value pairs between steps.
"""

import time
import traceback
from typing import Any
from crewai import Agent, Task, Crew, Process

from crewfarm.verification import verify_output, extract_key_values
from crewfarm.state import StateTracker


class IsolatedRunner:
    """
    Runs CrewAI tasks in isolation with verification gates.

    Antfarm equivalent: the workflow step executor that runs each agent
    in a fresh session, checks `expects:` conditions, and retries on failure.
    """

    def __init__(
        self,
        state_tracker: StateTracker | None = None,
        max_retries: int = 2,
        verbose: bool = True,
    ):
        self.state = state_tracker or StateTracker()
        self.max_retries = max_retries
        self.verbose = verbose
        self._context: dict[str, Any] = {}  # accumulated KEY: value pairs
        self._run_id: str | None = None

    def start_run(self, workflow_name: str, task_description: str) -> str:
        """Start a new workflow run. Returns run_id."""
        self._run_id = self.state.create_run(workflow_name, task_description)
        self._context = {}
        return self._run_id

    def run_step(
        self,
        step_id: str,
        agent: Agent,
        task: Task,
        expects: str | None = None,
        required_keys: list[str] | None = None,
        custom_checks: list[callable] | None = None,
        max_retries: int | None = None,
        verifier_agent: Agent | None = None,
    ) -> dict[str, Any]:
        """
        Run a single task in isolation with verification.

        This is the core Antfarm pattern:
        1. Inject accumulated context into the task description
        2. Run as isolated mini-crew (fresh context)
        3. Parse KEY: value output
        4. Verify against `expects` condition
        5. If verification fails, retry with feedback
        6. Log everything to SQLite

        Args:
            step_id: Unique identifier for this step
            agent: The CrewAI agent to execute this step
            task: The CrewAI task definition
            expects: String that must appear in output (Antfarm's expects: field)
            required_keys: List of KEY names that must be present in parsed output
            custom_checks: List of callables that take (output, parsed_keys) and
                            return (bool, error_msg)
            max_retries: Override default retry count for this step
            verifier_agent: Optional separate agent to verify output

        Returns:
            Dict of parsed KEY: value pairs from the output
        """
        retries = max_retries if max_retries is not None else self.max_retries
        last_error = None

        for attempt in range(retries + 1):
            start_time = time.time()

            try:
                # --- INJECT CONTEXT ---
                # Antfarm uses {{variable}} templates. We append context to description.
                enriched_description = self._enrich_description(task.description)

                if last_error and attempt > 0:
                    enriched_description += (
                        f"\n\n---\nPREVIOUS ATTEMPT FAILED (attempt {attempt}/{retries}).\n"
                        f"Error: {last_error}\n"
                        f"Fix the issue and try again.\n---"
                    )

                # --- CREATE ISOLATED TASK ---
                # Fresh task object so we don't mutate the original
                isolated_task = Task(
                    description=enriched_description,
                    expected_output=task.expected_output,
                    agent=agent,
                )

                # --- RUN IN ISOLATION ---
                # This is the key Antfarm pattern: fresh crew = fresh context
                mini_crew = Crew(
                    agents=[agent],
                    tasks=[isolated_task],
                    process=Process.sequential,
                    verbose=self.verbose,
                )
                result = mini_crew.kickoff()
                raw_output = str(result)
                duration = time.time() - start_time

                # --- VERIFY OUTPUT ---
                passed, error_msg = verify_output(
                    raw_output,
                    expects=expects,
                    required_keys=required_keys,
                    custom_checks=custom_checks,
                )

                # --- OPTIONAL VERIFIER AGENT ---
                if passed and verifier_agent:
                    passed, error_msg = self._run_verifier(
                        verifier_agent, step_id, enriched_description, raw_output
                    )

                if passed:
                    # --- PARSE AND ACCUMULATE ---
                    key_values = extract_key_values(raw_output)
                    self._context.update(key_values)

                    # --- LOG SUCCESS ---
                    self.state.log_step(
                        run_id=self._run_id,
                        step_id=step_id,
                        agent_name=agent.role,
                        input_text=enriched_description,
                        output_text=raw_output,
                        status="done",
                        duration=duration,
                        attempt=attempt + 1,
                    )

                    if self.verbose:
                        print(f"  ✓ Step '{step_id}' completed (attempt {attempt + 1})")

                    return key_values

                else:
                    last_error = error_msg
                    self.state.log_step(
                        run_id=self._run_id,
                        step_id=step_id,
                        agent_name=agent.role,
                        input_text=enriched_description,
                        output_text=raw_output,
                        status="failed",
                        duration=duration,
                        attempt=attempt + 1,
                        error=error_msg,
                    )

                    if self.verbose:
                        print(
                            f"  ✗ Step '{step_id}' failed (attempt {attempt + 1}): {error_msg}"
                        )

            except Exception as e:
                duration = time.time() - start_time
                last_error = str(e)
                self.state.log_step(
                    run_id=self._run_id,
                    step_id=step_id,
                    agent_name=agent.role,
                    input_text=task.description,
                    output_text=traceback.format_exc(),
                    status="error",
                    duration=duration,
                    attempt=attempt + 1,
                    error=str(e),
                )

                if self.verbose:
                    print(f"  ✗ Step '{step_id}' error (attempt {attempt + 1}): {e}")

        # --- ALL RETRIES EXHAUSTED ---
        self.state.log_step(
            run_id=self._run_id,
            step_id=step_id,
            agent_name=agent.role,
            input_text=task.description,
            output_text="",
            status="escalated",
            duration=0,
            attempt=retries + 1,
            error=f"All {retries + 1} attempts failed. Last error: {last_error}",
        )

        raise RuntimeError(
            f"Step '{step_id}' failed after {retries + 1} attempts. "
            f"Last error: {last_error}"
        )

    def get_context(self) -> dict[str, Any]:
        """Return accumulated context from all completed steps."""
        return dict(self._context)

    def _enrich_description(self, description: str) -> str:
        """
        Inject accumulated context into task description.

        Antfarm uses {{variable}} placeholders in step input templates.
        We append all accumulated KEY: value pairs as a context block.
        """
        if not self._context:
            return description

        context_block = "\n\n---\nCONTEXT FROM PREVIOUS STEPS:\n"
        for key, value in self._context.items():
            # Truncate very long values to avoid context window bloat
            val_str = str(value)
            if len(val_str) > 2000:
                val_str = val_str[:2000] + "\n... [truncated]"
            context_block += f"{key}: {val_str}\n"
        context_block += "---\n"

        return description + context_block

    def _run_verifier(
        self,
        verifier: Agent,
        step_id: str,
        original_input: str,
        output: str,
    ) -> tuple[bool, str | None]:
        """
        Run a separate verifier agent to check output quality.

        Antfarm pattern: "The developer doesn't mark their own homework."
        """
        verify_task = Task(
            description=(
                f"Verify the output of step '{step_id}'.\n\n"
                f"ORIGINAL TASK:\n{original_input}\n\n"
                f"OUTPUT TO VERIFY:\n{output}\n\n"
                "Check for:\n"
                "- Completeness: Does the output address all requirements?\n"
                "- Accuracy: Are facts, numbers, and logic correct?\n"
                "- Format: Does it include required KEY: value pairs?\n\n"
                "Reply with:\n"
                "STATUS: approved  (if output is acceptable)\n"
                "STATUS: rejected  (if output needs rework)\n"
                "REASON: <explanation>"
            ),
            expected_output="STATUS: approved or STATUS: rejected with REASON",
            agent=verifier,
        )

        verify_crew = Crew(
            agents=[verifier],
            tasks=[verify_task],
            process=Process.sequential,
            verbose=self.verbose,
        )
        verify_result = str(verify_crew.kickoff())

        if "STATUS: approved" in verify_result:
            return True, None
        else:
            reason = "Verifier rejected output"
            for line in verify_result.split("\n"):
                if line.strip().upper().startswith("REASON:"):
                    reason = line.split(":", 1)[1].strip()
                    break
            return False, reason
