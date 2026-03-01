"""Crew orchestration — assembles agents and tasks into isolated steps with verification."""

import logging

from crewfarm import IsolatedRunner, StateTracker
from crewfarm.verification import check_non_empty
from crewfarm.verifier_agent import create_verifier

from src.agents import (
    create_researcher,
    create_seo_strategist,
    create_social_monitor,
    create_writer,
    haiku,
)
from src.tasks import (
    create_research_task,
    create_seo_task,
    create_social_monitoring_task,
    create_writing_task,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_content_crew(
    task_description: str,
    content_type: str = "blog post",
    platform: str = "blog",
    audience: str = "tech professionals",
    tone: str = "informative and engaging",
    include_seo: bool = True,
    include_social: bool = False,
) -> str:
    """Run the content crew on a given task using isolated steps.

    Each step runs as its own mini-crew (fresh context window), with
    verification gates and SQLite state tracking.

    Args:
        task_description: Natural language description of what to create.
        content_type: Type of content (blog post, thread, newsletter, etc).
        platform: Target platform (blog, twitter, linkedin, newsletter).
        audience: Target audience description.
        tone: Desired tone of the content.
        include_seo: Whether to include SEO optimization.
        include_social: Whether to include social monitoring.

    Returns:
        Final synthesized output from the crew.
    """
    # --- AGENTS (unchanged) ---
    researcher = create_researcher()
    writer = create_writer()

    # --- VERIFIER (cheap model checks work) ---
    content_verifier = create_verifier(
        llm=haiku,
        domain_context=(
            "You are verifying content creation output. Check that:\n"
            "- All required KEY: value fields are present\n"
            "- Content is substantive and not placeholder text\n"
            "- STATUS field is 'done'"
        ),
    )

    # --- TASKS ---
    research_task = create_research_task(topic=task_description, agent=researcher)

    # --- EXECUTION ---
    tracker = StateTracker("crewfarm_db.sqlite")
    runner = IsolatedRunner(state_tracker=tracker, max_retries=2, verbose=True)

    run_id = runner.start_run(
        workflow_name="content-crew",
        task_description=task_description,
    )

    logger.info("Starting content crew run %s", run_id)

    try:
        # Step 1: Research
        runner.run_step(
            step_id="research",
            agent=researcher,
            task=research_task,
            expects="STATUS: done",
            required_keys=["summary", "key_findings"],
            custom_checks=[check_non_empty("summary", "key_findings")],
            verifier_agent=content_verifier,
        )

        # Step 2: SEO (optional)
        if include_seo:
            seo = create_seo_strategist()
            seo_task = create_seo_task(topic=task_description, agent=seo)
            runner.run_step(
                step_id="seo",
                agent=seo,
                task=seo_task,
                expects="STATUS: done",
                required_keys=["primary_keyword", "recommendations"],
                custom_checks=[check_non_empty("primary_keyword")],
            )

        # Step 3: Social monitoring (optional)
        if include_social:
            monitor = create_social_monitor()
            social_task = create_social_monitoring_task(
                topic=task_description, agent=monitor
            )
            runner.run_step(
                step_id="social",
                agent=monitor,
                task=social_task,
                expects="STATUS: done",
                required_keys=["alert_level"],
            )

        # Step 4: Writing (final step)
        writing_task = create_writing_task(
            topic=task_description,
            content_type=content_type,
            agent=writer,
            platform=platform,
            audience=audience,
            tone=tone,
        )
        write_output = runner.run_step(
            step_id="write",
            agent=writer,
            task=writing_task,
            expects="STATUS: done",
            required_keys=["content"],
            custom_checks=[check_non_empty("content")],
        )

        tracker.complete_run(run_id, status="done")
        tracker.print_status(run_id)
        logger.info("Content crew finished successfully — run %s", run_id)

        return write_output.get("content", "")

    except RuntimeError as e:
        tracker.complete_run(run_id, status="failed")
        tracker.print_status(run_id)
        logger.error("Content crew failed — run %s: %s", run_id, e)
        raise

    finally:
        tracker.close()
