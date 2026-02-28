"""Task factories for common content/marketing workflows."""

from crewai import Agent, Task


def create_research_task(topic: str, agent: Agent) -> Task:
    """Create a research task for the given topic."""
    return Task(
        description=(
            f"Research the following topic thoroughly: {topic}\n\n"
            "Find current, accurate information from multiple web sources. "
            "Focus on: key facts, recent developments, notable players, "
            "and data points."
        ),
        expected_output=(
            "A structured research brief with:\n"
            "- Summary (2-3 sentences)\n"
            "- Key Findings (bullet points with specifics)\n"
            "- Data/Comparisons (table if applicable)\n"
            "- Sources (URLs for every claim)"
        ),
        agent=agent,
    )


def create_writing_task(
    topic: str,
    content_type: str,
    agent: Agent,
    platform: str = "blog",
    audience: str = "tech professionals",
    tone: str = "informative and engaging",
) -> Task:
    """Create a content writing task."""
    return Task(
        description=(
            f"Write a {content_type} about: {topic}\n\n"
            "Use the research findings provided by the researcher as your "
            "source material.\n"
            f"Target platform: {platform}\n"
            f"Target audience: {audience}\n"
            f"Tone: {tone}"
        ),
        expected_output=(
            f"Publish-ready {content_type} with:\n"
            "- Compelling headline\n"
            "- Well-structured body\n"
            "- Clear call-to-action if appropriate\n"
            f"- Formatted for {platform}"
        ),
        agent=agent,
    )


def create_seo_task(topic: str, agent: Agent) -> Task:
    """Create an SEO optimization task."""
    return Task(
        description=(
            f"Analyze and provide SEO optimization for content about: {topic}\n\n"
            "Research target keywords, analyze search intent, and suggest "
            "optimizations."
        ),
        expected_output=(
            "SEO optimization brief with:\n"
            "- Primary keyword and 3-5 secondary keywords\n"
            "- Search intent analysis\n"
            "- Suggested meta title (under 60 chars)\n"
            "- Suggested meta description (under 160 chars)\n"
            "- Content optimization recommendations"
        ),
        agent=agent,
    )


def create_social_monitoring_task(topic: str, agent: Agent) -> Task:
    """Create a social monitoring task."""
    return Task(
        description=(
            f"Monitor and report on social/news activity related to: {topic}\n\n"
            "Search for recent mentions, competitor activity, and emerging trends."
        ),
        expected_output=(
            "Social intelligence report with:\n"
            "- Alert level (urgent/notable/routine)\n"
            "- Key mentions and their sentiment\n"
            "- Competitor activity summary\n"
            "- Emerging trends\n"
            "- Recommended actions"
        ),
        agent=agent,
    )
