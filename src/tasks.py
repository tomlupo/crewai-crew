"""Task factories for common content/marketing workflows."""

from crewai import Agent, Task


def create_research_task(topic: str, agent: Agent) -> Task:
    """Create a research task for the given topic."""
    return Task(
        description=(
            f"Research the following topic thoroughly: {topic}\n\n"
            "Find current, accurate information from multiple web sources. "
            "Focus on: key facts, recent developments, notable players, "
            "and data points.\n\n"
            "REQUIRED OUTPUT FORMAT:\n"
            "STATUS: done\n"
            "SUMMARY: <2-3 sentence overview of findings>\n"
            "KEY_FINDINGS: <bullet points with specifics>\n"
            "DATA: <data points, comparisons, or table>\n"
            "SOURCES: <URLs for every claim>"
        ),
        expected_output=(
            "A structured research brief with STATUS: done and KEY: value output "
            "including SUMMARY, KEY_FINDINGS, DATA, and SOURCES."
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
            "- DO NOT output markdown. Output raw HTML only.\n\n"
            "REQUIRED OUTPUT FORMAT:\n"
            "STATUS: done\n"
            "CONTENT: <the complete HTML document from <!DOCTYPE html> to </html>>"
        )
        expected_output = (
            "A complete, self-contained HTML file with STATUS: done and "
            "CONTENT: containing the full HTML document."
        )
    else:
        description = (
            f"Write a {content_type} about: {topic}\n\n"
            "Use the research findings provided by the researcher as your "
            "source material.\n"
            f"Target platform: {platform}\n"
            f"Target audience: {audience}\n"
            f"Tone: {tone}\n\n"
            "REQUIRED OUTPUT FORMAT:\n"
            "STATUS: done\n"
            "CONTENT: <the full publish-ready content>"
        )
        expected_output = (
            f"Publish-ready {content_type} with STATUS: done and "
            f"CONTENT: containing the complete piece formatted for {platform}."
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
            "optimizations.\n\n"
            "REQUIRED OUTPUT FORMAT:\n"
            "STATUS: done\n"
            "PRIMARY_KEYWORD: <main target keyword>\n"
            "SECONDARY_KEYWORDS: <3-5 secondary keywords, comma-separated>\n"
            "SEARCH_INTENT: <analysis of user search intent>\n"
            "META_TITLE: <suggested meta title, under 60 chars>\n"
            "META_DESCRIPTION: <suggested meta description, under 160 chars>\n"
            "RECOMMENDATIONS: <content optimization recommendations>"
        ),
        expected_output=(
            "SEO optimization brief with STATUS: done and KEY: value output "
            "including PRIMARY_KEYWORD, META_TITLE, META_DESCRIPTION, and RECOMMENDATIONS."
        ),
        agent=agent,
    )


def create_social_monitoring_task(topic: str, agent: Agent) -> Task:
    """Create a social monitoring task."""
    return Task(
        description=(
            f"Monitor and report on social/news activity related to: {topic}\n\n"
            "Search for recent mentions, competitor activity, and emerging trends.\n\n"
            "REQUIRED OUTPUT FORMAT:\n"
            "STATUS: done\n"
            "ALERT_LEVEL: <urgent/notable/routine>\n"
            "MENTIONS: <key mentions and their sentiment>\n"
            "COMPETITOR_ACTIVITY: <competitor activity summary>\n"
            "TRENDS: <emerging trends>\n"
            "ACTIONS: <recommended actions>"
        ),
        expected_output=(
            "Social intelligence report with STATUS: done and KEY: value output "
            "including ALERT_LEVEL, MENTIONS, TRENDS, and ACTIONS."
        ),
        agent=agent,
    )
