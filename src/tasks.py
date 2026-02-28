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
    is_html = content_type in ("landing page", "html page", "webpage", "website")
    if is_html:
        description = (
            f"Build a {content_type} about: {topic}\n\n"
            "Use the research findings and SEO recommendations from prior tasks.\n"
            f"Target audience: {audience}\n"
            f"Tone: {tone}\n\n"
            "OUTPUT REQUIREMENTS:\n"
            "- Output a COMPLETE, single-file HTML document (<!DOCTYPE html> to </html>)\n"
            "- Include all CSS inline in a <style> tag — no external stylesheets\n"
            "- Modern, responsive design with mobile-first approach\n"
            "- Professional color palette, clean typography (use Google Fonts via CDN)\n"
            "- Hero section with headline and CTA button\n"
            "- Benefits/features section with icons or cards\n"
            "- Social proof / stats section\n"
            "- Final CTA section\n"
            "- Smooth scroll, subtle animations (CSS only)\n"
            "- DO NOT output markdown. Output raw HTML only."
        )
        expected_output = (
            "A complete, self-contained HTML file with:\n"
            "- <!DOCTYPE html> declaration\n"
            "- Embedded CSS in <style> tags\n"
            "- Responsive layout that works on mobile and desktop\n"
            "- Hero, benefits, stats, and CTA sections\n"
            "- Professional visual design\n"
            "- NO markdown wrapping — raw HTML only"
        )
    else:
        description = (
            f"Write a {content_type} about: {topic}\n\n"
            "Use the research findings provided by the researcher as your "
            "source material.\n"
            f"Target platform: {platform}\n"
            f"Target audience: {audience}\n"
            f"Tone: {tone}"
        )
        expected_output = (
            f"Publish-ready {content_type} with:\n"
            "- Compelling headline\n"
            "- Well-structured body\n"
            "- Clear call-to-action if appropriate\n"
            f"- Formatted for {platform}"
        )
    return Task(
        description=description,
        expected_output=expected_output,
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
