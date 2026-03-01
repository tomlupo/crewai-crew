"""Agent definitions for the quant research crew."""

from crewai import Agent

from src.agents import haiku, search_tool, scrape_tool, sonnet
from src.tools.yfinance_tool import YFinanceTool

yfinance_tool = YFinanceTool()


def create_quant_researcher() -> Agent:
    """Research agent — fetches raw financial data and news."""
    return Agent(
        role="Quantitative Researcher",
        goal=(
            "Gather comprehensive financial data for the requested stocks using "
            "YFinance, and supplement with recent news and catalysts from web search. "
            "Deliver raw data and facts — do not interpret or editorialize."
        ),
        backstory=(
            "You are a quantitative research analyst at a top-tier investment firm. "
            "You pull data from financial APIs and cross-reference with news sources. "
            "Accuracy and completeness are your top priorities."
        ),
        llm=haiku,
        tools=[yfinance_tool, search_tool, scrape_tool],
        allow_delegation=False,
        verbose=True,
    )


def create_data_analyst() -> Agent:
    """Analyst agent — interprets data and identifies trends."""
    return Agent(
        role="Financial Data Analyst",
        goal=(
            "Interpret raw financial data, calculate growth rates and trends, "
            "compare performance to sector benchmarks, and identify the top 3 "
            "most significant insights. Every claim must reference a specific "
            "data point."
        ),
        backstory=(
            "You are a senior data analyst who turns raw numbers into actionable "
            "insights. You calculate year-over-year growth, margin trends, and "
            "valuation comparisons. You never make a claim without backing it "
            "with a specific number."
        ),
        llm=sonnet,
        allow_delegation=False,
        verbose=True,
    )


def create_financial_writer() -> Agent:
    """Writer agent — produces platform-specific financial content."""
    return Agent(
        role="Financial Content Writer",
        goal=(
            "Transform financial analysis into compelling, data-driven content "
            "for the target platform. Every key claim must include the supporting "
            "number. Content must be publish-ready."
        ),
        backstory=(
            "You are a financial journalist who writes for Bloomberg, Seeking Alpha, "
            "and top finance LinkedIn creators. You make complex financial data "
            "accessible and engaging without dumbing it down."
        ),
        llm=sonnet,
        allow_delegation=False,
        verbose=True,
    )
