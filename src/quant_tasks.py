"""Task factories for the quant research crew."""

from crewai import Agent, Task


def create_quant_research_task(
    description: str,
    tickers: list[str] | None,
    agent: Agent,
) -> Task:
    """Create a quantitative research task."""
    ticker_instruction = ""
    if tickers:
        ticker_list = ", ".join(tickers)
        ticker_instruction = (
            f"\n\nUse the YFinance Stock Data tool to fetch data for each ticker: {ticker_list}. "
            "For each ticker, get the 3-month price performance and key metrics. "
            "If the task involves deep analysis, also fetch with include_financials=True."
        )

    return Task(
        description=(
            f"Research the following: {description}"
            f"{ticker_instruction}\n\n"
            "After fetching financial data, search the web for recent news, "
            "earnings reports, analyst opinions, and catalysts for these companies.\n\n"
            "REQUIRED OUTPUT FORMAT:\n"
            "STATUS: done\n"
            "METRICS: <key financial metrics for each ticker — price, P/E, EPS, revenue, margins>\n"
            "PERFORMANCE: <price performance over recent period>\n"
            "NEWS: <recent news and catalysts with sources>\n"
            "ANALYST_RATINGS: <notable analyst ratings or price targets>\n"
            "SUMMARY: <2-3 sentence overview>"
        ),
        expected_output=(
            "A structured research package with STATUS: done and KEY: value output "
            "including METRICS, PERFORMANCE, NEWS, and ANALYST_RATINGS."
        ),
        agent=agent,
    )


def create_quant_analysis_task(description: str, agent: Agent) -> Task:
    """Create a data analysis/interpretation task."""
    return Task(
        description=(
            f"Analyze the financial data gathered for: {description}\n\n"
            "Your job is to interpret the raw data and produce actionable insights:\n"
            "1. Calculate year-over-year and quarter-over-quarter growth rates\n"
            "2. Compare valuation metrics to sector/industry averages\n"
            "3. Identify margin trends (improving, stable, declining)\n"
            "4. Assess price performance relative to benchmarks\n"
            "5. Identify the top 3 most significant trends or insights\n\n"
            "IMPORTANT: Every claim must reference a specific data point. "
            "Do not make vague statements like 'revenue is growing' — say "
            "'revenue grew 122% YoY to $35.1B in Q3 FY2025'.\n\n"
            "REQUIRED OUTPUT FORMAT:\n"
            "STATUS: done\n"
            "GROWTH_METRICS: <revenue, earnings, margins with exact numbers>\n"
            "VALUATION: <assessment vs. sector and historical>\n"
            "TOP_INSIGHTS: <top 3 key insights, each backed by specific data>\n"
            "RISKS: <risk factors or concerns>\n"
            "OUTLOOK: <overall outlook summary>"
        ),
        expected_output=(
            "A financial analysis brief with STATUS: done and KEY: value output "
            "including GROWTH_METRICS, VALUATION, TOP_INSIGHTS, RISKS, and OUTLOOK."
        ),
        agent=agent,
    )


PLATFORM_PROMPTS = {
    "linkedin": (
        "Format as a LinkedIn post (1000-1300 characters):\n"
        "- Start with a strong hook line that grabs attention\n"
        "- Use line breaks between paragraphs for readability\n"
        "- Include 3-5 specific data points woven naturally into the narrative\n"
        "- End with a thought-provoking question or call-to-action\n"
        "- Add 3-5 relevant hashtags at the end\n"
        "- Tone: professional but conversational, data-driven but accessible"
    ),
    "twitter": (
        "Format as a Twitter/X thread of 5-8 tweets:\n"
        "- Tweet 1: Strong hook with the main insight (no thread numbering in first tweet)\n"
        "- Tweets 2-7: One key insight per tweet, each with a specific data point\n"
        "- Final tweet: Summary takeaway + relevant $TICKER cashtags\n"
        "- Each tweet must be under 280 characters\n"
        "- Number tweets as 1/, 2/, etc. starting from tweet 2\n"
        "- Use line breaks between tweets"
    ),
    "blog": (
        "Format as a blog article (800-1500 words):\n"
        "- Compelling title with the key finding\n"
        "- Introduction paragraph setting up the thesis\n"
        "- 3-5 H2 sections, each covering a major insight\n"
        "- Include data tables where appropriate (markdown format)\n"
        "- Conclusion with forward-looking outlook\n"
        "- Tone: authoritative, data-rich, accessible to informed investors"
    ),
}


def create_quant_content_task(
    description: str,
    content_type: str,
    platform: str,
    agent: Agent,
) -> Task:
    """Create a financial content writing task."""
    platform_guide = PLATFORM_PROMPTS.get(platform, PLATFORM_PROMPTS["blog"])

    return Task(
        description=(
            f"Write a {content_type} based on the financial analysis: {description}\n\n"
            "Use the analysis from the previous task as your source material. "
            "Every key claim must include the supporting number.\n\n"
            f"{platform_guide}\n\n"
            "REQUIRED OUTPUT FORMAT:\n"
            "STATUS: done\n"
            "CONTENT: <the full publish-ready content>"
        ),
        expected_output=(
            f"A publish-ready {content_type} with STATUS: done and "
            f"CONTENT: containing the complete piece formatted for {platform}."
        ),
        agent=agent,
    )
