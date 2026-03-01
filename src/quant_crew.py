"""Crew orchestration for the quant research pipeline with isolated steps."""

import logging

from crewfarm import IsolatedRunner, StateTracker
from crewfarm.verification import check_non_empty
from crewfarm.verifier_agent import create_domain_verifier

from src.agents import haiku
from src.quant_agents import (
    create_data_analyst,
    create_financial_writer,
    create_quant_researcher,
)
from src.quant_tasks import (
    create_quant_analysis_task,
    create_quant_content_task,
    create_quant_research_task,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_quant_crew(
    task_description: str,
    tickers: list[str] | None = None,
    content_type: str = "LinkedIn post",
    platform: str = "linkedin",
) -> str:
    """Run the quant research crew using isolated steps.

    Each step runs as its own mini-crew (fresh context window), with
    verification gates and SQLite state tracking.

    Args:
        task_description: What to research and write about.
        tickers: Stock ticker symbols to analyze (e.g. ["NVDA", "AAPL"]).
        content_type: Type of content to produce.
        platform: Target platform (linkedin, twitter, blog).

    Returns:
        Final publish-ready content from the crew.
    """
    # --- AGENTS (unchanged) ---
    researcher = create_quant_researcher()
    analyst = create_data_analyst()
    writer = create_financial_writer()

    # --- VERIFIER (domain-specific, cheap model) ---
    quant_verifier = create_domain_verifier(
        domain="financial data analysis",
        checks=[
            "All referenced financial metrics include specific numbers",
            "STATUS field is present and set to 'done'",
            "Output is substantive, not placeholder text",
            "Claims reference concrete data points, not vague statements",
        ],
        llm=haiku,
    )

    # --- TASKS ---
    research_task = create_quant_research_task(
        description=task_description,
        tickers=tickers,
        agent=researcher,
    )
    analysis_task = create_quant_analysis_task(
        description=task_description,
        agent=analyst,
    )
    content_task = create_quant_content_task(
        description=task_description,
        content_type=content_type,
        platform=platform,
        agent=writer,
    )

    # --- EXECUTION ---
    tracker = StateTracker("crewfarm_db.sqlite")
    runner = IsolatedRunner(state_tracker=tracker, max_retries=2, verbose=True)

    tickers_str = ", ".join(tickers) if tickers else "none"
    run_id = runner.start_run(
        workflow_name="quant-crew",
        task_description=f"{task_description} (tickers: {tickers_str})",
    )

    logger.info(
        "Starting quant crew run %s — tickers=%s, platform=%s",
        run_id,
        tickers_str,
        platform,
    )

    try:
        # Step 1: Research — gather raw financial data and news
        runner.run_step(
            step_id="research",
            agent=researcher,
            task=research_task,
            expects="STATUS: done",
            required_keys=["metrics", "summary"],
            custom_checks=[check_non_empty("metrics", "summary")],
            verifier_agent=quant_verifier,
        )

        # Step 2: Analysis — interpret data, calculate trends
        runner.run_step(
            step_id="analyze",
            agent=analyst,
            task=analysis_task,
            expects="STATUS: done",
            required_keys=["top_insights", "outlook"],
            custom_checks=[check_non_empty("top_insights", "outlook")],
            verifier_agent=quant_verifier,
        )

        # Step 3: Content — produce publish-ready piece
        content_output = runner.run_step(
            step_id="content",
            agent=writer,
            task=content_task,
            expects="STATUS: done",
            required_keys=["content"],
            custom_checks=[check_non_empty("content")],
        )

        tracker.complete_run(run_id, status="done")
        tracker.print_status(run_id)
        logger.info("Quant crew finished successfully — run %s", run_id)

        return content_output.get("content", "")

    except RuntimeError as e:
        tracker.complete_run(run_id, status="failed")
        tracker.print_status(run_id)
        logger.error("Quant crew failed — run %s: %s", run_id, e)
        raise

    finally:
        tracker.close()
