"""Crew orchestration — assembles agents and tasks into a sequential crew."""

import logging

from crewai import Crew, Process

from src.agents import (
    create_researcher,
    create_seo_strategist,
    create_social_monitor,
    create_writer,
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
    """Run the content crew on a given task.

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
    # Create agents
    researcher = create_researcher()
    writer = create_writer()

    agents = [researcher, writer]
    tasks = []

    # Research task always runs first
    research_task = create_research_task(topic=task_description, agent=researcher)
    tasks.append(research_task)

    # SEO task (optional) — runs after research, before writing
    if include_seo:
        seo = create_seo_strategist()
        agents.append(seo)
        seo_task = create_seo_task(topic=task_description, agent=seo)
        tasks.append(seo_task)

    # Social monitoring (optional)
    if include_social:
        monitor = create_social_monitor()
        agents.append(monitor)
        social_task = create_social_monitoring_task(
            topic=task_description, agent=monitor
        )
        tasks.append(social_task)

    # Writing task runs last — gets context from all previous tasks
    writing_task = create_writing_task(
        topic=task_description,
        content_type=content_type,
        agent=writer,
        platform=platform,
        audience=audience,
        tone=tone,
    )
    tasks.append(writing_task)

    # Sequential process: Research → SEO → Write
    # (Claude 4.6 doesn't support assistant prefill required by hierarchical mode)
    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.sequential,
        verbose=True,
    )

    logger.info("Starting crew with %d agents and %d tasks", len(agents), len(tasks))
    result = crew.kickoff()
    logger.info("Crew finished successfully")
    return str(result)
