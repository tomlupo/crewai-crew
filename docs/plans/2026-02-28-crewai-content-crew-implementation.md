# CrewAI Content/Marketing Crew — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a 5-agent CrewAI crew (Editor-in-Chief manager + Researcher, Writer, SEO Strategist, Social Monitor) with a Streamlit web UI, using Anthropic Claude models, for content/marketing task orchestration.

**Architecture:** Hierarchical process with custom manager agent. Manager decomposes tasks and delegates to specialists via CrewAI's built-in delegation. Streamlit app submits tasks, displays real-time agent activity, and stores results in SQLite.

**Tech Stack:** Python 3.11+, CrewAI, crewai-tools, Streamlit, Anthropic Claude (Opus/Sonnet/Haiku), SQLite, python-dotenv

---

## Phase 1: Project Scaffolding

### Task 1: Create pyproject.toml and .env

**Files:**
- Create: `/home/botops/crewai-crew/pyproject.toml`
- Create: `/home/botops/crewai-crew/.env.example`
- Create: `/home/botops/crewai-crew/.gitignore`

**Step 1: Write pyproject.toml**

```toml
[project]
name = "crewai-content-crew"
version = "0.1.0"
description = "Content/marketing multi-agent crew powered by CrewAI and Anthropic Claude"
requires-python = ">=3.11"
dependencies = [
    "crewai[tools]>=0.100.0",
    "crewai-tools>=0.30.0",
    "streamlit>=1.40.0",
    "python-dotenv>=1.0.0",
]
```

**Step 2: Write .env.example**

```
ANTHROPIC_API_KEY=sk-ant-REPLACE_ME
SERPER_API_KEY=REPLACE_ME
```

**Step 3: Write .gitignore**

```
__pycache__/
*.pyc
.env
output/
*.db
.venv/
dist/
*.egg-info/
```

**Step 4: Create .env with real keys**

Copy `.env.example` to `.env` and fill in the actual `ANTHROPIC_API_KEY` from `/home/botops/swarm/.openclaw/openclaw.json` (the auth profile). For SERPER_API_KEY, leave as placeholder or use a real key if available.

**Step 5: Commit**

```bash
cd /home/botops/crewai-crew
git add pyproject.toml .env.example .gitignore
git commit -m "chore: add project config, env template, gitignore"
```

---

### Task 2: Create directory structure and __init__.py files

**Files:**
- Create: `/home/botops/crewai-crew/src/__init__.py`
- Create: `/home/botops/crewai-crew/src/tools/__init__.py`
- Create: `/home/botops/crewai-crew/src/config/agents.yaml`
- Create: `/home/botops/crewai-crew/src/config/tasks.yaml`
- Create: `/home/botops/crewai-crew/output/.gitkeep`

**Step 1: Create directories**

```bash
mkdir -p /home/botops/crewai-crew/src/tools
mkdir -p /home/botops/crewai-crew/src/config
mkdir -p /home/botops/crewai-crew/output
```

**Step 2: Write empty __init__.py files**

Create `/home/botops/crewai-crew/src/__init__.py`:
```python
```

Create `/home/botops/crewai-crew/src/tools/__init__.py`:
```python
```

**Step 3: Write agents.yaml**

Create `/home/botops/crewai-crew/src/config/agents.yaml`:

```yaml
editor_in_chief:
  role: >
    Content Strategy Manager
  goal: >
    Decompose content tasks, delegate to the right specialists, review quality,
    and synthesize polished deliverables. Your final output IS the deliverable
    the user receives — make it publish-ready.
  backstory: >
    You are an experienced editorial director who has managed content teams at
    major publications. You know exactly what research is needed, what angle to
    take, and how to combine specialist work into a single polished piece.
    You never write content yourself — you delegate and synthesize.
  allow_delegation: true
  verbose: true

researcher:
  role: >
    Content Researcher
  goal: >
    Find accurate, current information from web sources. Deliver structured
    research briefs with data, comparisons, and source URLs.
  backstory: >
    You are an investigative journalist turned research analyst. Thorough, fast,
    and source-obsessed. You never report a claim without a URL to back it up.
    You structure findings as: Summary, Key Findings, Data Table, Sources.
  allow_delegation: false
  verbose: true

writer:
  role: >
    Content Writer
  goal: >
    Create compelling, publish-ready content tailored to the target platform
    and audience. Every piece should be edited, polished, and ready to publish.
  backstory: >
    You are a senior content strategist who has written for tech blogs,
    newsletters, and social media. You adapt voice and format to the platform.
    You show, don't tell. You cut filler ruthlessly. Your output is never a draft.
  allow_delegation: false
  verbose: true

seo_strategist:
  role: >
    SEO and Content Optimization Specialist
  goal: >
    Research keywords, analyze search intent, and provide SEO recommendations.
    Deliver keyword targets, meta descriptions, and optimization suggestions.
  backstory: >
    You are a technical SEO consultant who understands both search algorithms
    and human readers. You optimize without sacrificing readability. You focus
    on search intent, not keyword stuffing.
  allow_delegation: false
  verbose: true

social_monitor:
  role: >
    Social Intelligence Analyst
  goal: >
    Track brand mentions, competitor activity, and emerging trends across
    social platforms and news. Report only what is actionable.
  backstory: >
    You are a former social media strategist who monitors the pulse of the
    internet. You distinguish signal from noise. You report alert level
    (urgent/notable/routine), what changed, context, and recommended action.
  allow_delegation: false
  verbose: true
```

**Step 4: Write tasks.yaml**

Create `/home/botops/crewai-crew/src/config/tasks.yaml`:

```yaml
research_task:
  description: >
    Research the following topic thoroughly: {topic}

    Find current, accurate information from multiple web sources.
    Focus on: key facts, recent developments, notable players, and data points.
  expected_output: >
    A structured research brief with:
    - Summary (2-3 sentences)
    - Key Findings (bullet points with specifics)
    - Data/Comparisons (table if applicable)
    - Sources (URLs for every claim)
  agent: researcher

writing_task:
  description: >
    Write {content_type} about: {topic}

    Use the research findings provided by the researcher as your source material.
    Target platform: {platform}
    Target audience: {audience}
    Tone: {tone}
  expected_output: >
    Publish-ready {content_type} with:
    - Compelling headline
    - Well-structured body
    - Clear call-to-action if appropriate
    - Formatted for {platform}
  agent: writer

seo_task:
  description: >
    Analyze and provide SEO optimization for content about: {topic}

    Research target keywords, analyze search intent, and suggest optimizations.
  expected_output: >
    SEO optimization brief with:
    - Primary keyword and 3-5 secondary keywords
    - Search intent analysis
    - Suggested meta title (under 60 chars)
    - Suggested meta description (under 160 chars)
    - Content optimization recommendations
  agent: seo_strategist

social_monitoring_task:
  description: >
    Monitor and report on social/news activity related to: {topic}

    Search for recent mentions, competitor activity, and emerging trends.
  expected_output: >
    Social intelligence report with:
    - Alert level (urgent/notable/routine)
    - Key mentions and their sentiment
    - Competitor activity summary
    - Emerging trends
    - Recommended actions
  agent: social_monitor
```

**Step 5: Create output/.gitkeep**

```bash
touch /home/botops/crewai-crew/output/.gitkeep
```

**Step 6: Commit**

```bash
cd /home/botops/crewai-crew
git add src/ output/.gitkeep
git commit -m "chore: add project structure, agent and task YAML configs"
```

---

## Phase 2: Core Crew Implementation

### Task 3: Install dependencies

**Step 1: Create virtual environment and install**

```bash
cd /home/botops/crewai-crew
python3 -m venv .venv
source .venv/bin/activate
pip install "crewai[tools]>=0.100.0" "crewai-tools>=0.30.0" "streamlit>=1.40.0" "python-dotenv>=1.0.0"
```

**Step 2: Verify installation**

```bash
source .venv/bin/activate
python3 -c "import crewai; print(f'CrewAI version: {crewai.__version__}')"
python3 -c "from crewai import Agent, Task, Crew, Process, LLM; print('All imports OK')"
```

Expected: Version number printed, "All imports OK"

**Step 3: Freeze dependencies (optional)**

```bash
pip freeze > requirements.txt
```

---

### Task 4: Write agents.py — Agent definitions

**Files:**
- Create: `/home/botops/crewai-crew/src/agents.py`

**Step 1: Write agents.py**

```python
"""Agent definitions for the content/marketing crew."""

from crewai import Agent, LLM
from crewai_tools import SerperDevTool, ScrapeWebsiteTool, WebsiteSearchTool

# LLM instances — one per cost tier
opus = LLM(model="anthropic/claude-opus-4-6", temperature=0.3)
sonnet = LLM(model="anthropic/claude-sonnet-4-6", temperature=0.7)
haiku = LLM(model="anthropic/claude-haiku-4-5", temperature=0.3)

# Shared tool instances
search_tool = SerperDevTool()
scrape_tool = ScrapeWebsiteTool()
website_search_tool = WebsiteSearchTool()


def create_editor_in_chief() -> Agent:
    """Manager agent that decomposes tasks and delegates to specialists."""
    return Agent(
        role="Content Strategy Manager",
        goal=(
            "Decompose content tasks, delegate to the right specialists, "
            "review quality, and synthesize polished deliverables. "
            "Your final output IS the deliverable the user receives."
        ),
        backstory=(
            "You are an experienced editorial director who has managed content "
            "teams at major publications. You know exactly what research is "
            "needed, what angle to take, and how to combine specialist work "
            "into a single polished piece. You never write content yourself."
        ),
        llm=opus,
        allow_delegation=True,
        verbose=True,
    )


def create_researcher() -> Agent:
    """Research agent — web search, data collection, competitor analysis."""
    return Agent(
        role="Content Researcher",
        goal=(
            "Find accurate, current information from web sources. "
            "Deliver structured research briefs with data, comparisons, "
            "and source URLs."
        ),
        backstory=(
            "You are an investigative journalist turned research analyst. "
            "Thorough, fast, and source-obsessed. You never report a claim "
            "without a URL to back it up."
        ),
        llm=haiku,
        tools=[search_tool, scrape_tool, website_search_tool],
        allow_delegation=False,
        verbose=True,
    )


def create_writer() -> Agent:
    """Content writer — blog posts, threads, newsletters, copy."""
    return Agent(
        role="Content Writer",
        goal=(
            "Create compelling, publish-ready content tailored to the target "
            "platform and audience."
        ),
        backstory=(
            "You are a senior content strategist who has written for tech "
            "blogs, newsletters, and social media. You adapt voice and format "
            "to the platform. Every piece is polished and ready to publish."
        ),
        llm=sonnet,
        allow_delegation=False,
        verbose=True,
    )


def create_seo_strategist() -> Agent:
    """SEO agent — keyword research, content optimization."""
    return Agent(
        role="SEO and Content Optimization Specialist",
        goal=(
            "Research keywords, analyze search intent, and provide SEO "
            "recommendations including meta titles and descriptions."
        ),
        backstory=(
            "You are a technical SEO consultant who understands both search "
            "algorithms and human readers. You optimize without sacrificing "
            "readability."
        ),
        llm=haiku,
        tools=[search_tool, scrape_tool],
        allow_delegation=False,
        verbose=True,
    )


def create_social_monitor() -> Agent:
    """Social monitor — brand mentions, trends, competitor tracking."""
    return Agent(
        role="Social Intelligence Analyst",
        goal=(
            "Track brand mentions, competitor activity, and emerging trends. "
            "Report only what is actionable."
        ),
        backstory=(
            "You are a former social media strategist who monitors the pulse "
            "of the internet. You distinguish signal from noise."
        ),
        llm=haiku,
        tools=[search_tool, scrape_tool],
        allow_delegation=False,
        verbose=True,
    )
```

**Step 2: Verify imports work**

```bash
cd /home/botops/crewai-crew
source .venv/bin/activate
python3 -c "from src.agents import create_editor_in_chief, create_researcher, create_writer, create_seo_strategist, create_social_monitor; print('All agent factories OK')"
```

Expected: "All agent factories OK"

**Step 3: Commit**

```bash
git add src/agents.py
git commit -m "feat: add agent definitions with Claude model tiers"
```

---

### Task 5: Write tasks.py — Task factory

**Files:**
- Create: `/home/botops/crewai-crew/src/tasks.py`

**Step 1: Write tasks.py**

```python
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
```

**Step 2: Verify imports**

```bash
python3 -c "from src.tasks import create_research_task, create_writing_task, create_seo_task, create_social_monitoring_task; print('All task factories OK')"
```

Expected: "All task factories OK"

**Step 3: Commit**

```bash
git add src/tasks.py
git commit -m "feat: add task factory functions for content workflows"
```

---

### Task 6: Write crew.py — Crew orchestration

**Files:**
- Create: `/home/botops/crewai-crew/src/crew.py`

**Step 1: Write crew.py**

```python
"""Crew orchestration — assembles agents and tasks into a hierarchical crew."""

from crewai import Crew, Process

from src.agents import (
    create_editor_in_chief,
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
    editor = create_editor_in_chief()
    researcher = create_researcher()
    writer = create_writer()

    agents = [researcher, writer]
    tasks = []

    # Research task always runs first
    research_task = create_research_task(topic=task_description, agent=researcher)
    tasks.append(research_task)

    # SEO task (optional)
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

    # Writing task runs after research
    writing_task = create_writing_task(
        topic=task_description,
        content_type=content_type,
        agent=writer,
        platform=platform,
        audience=audience,
        tone=tone,
    )
    tasks.append(writing_task)

    # Assemble crew with hierarchical process
    crew = Crew(
        agents=agents,
        tasks=tasks,
        process=Process.hierarchical,
        manager_agent=editor,
        verbose=True,
    )

    result = crew.kickoff()
    return str(result)
```

**Step 2: Verify imports**

```bash
python3 -c "from src.crew import run_content_crew; print('Crew module OK')"
```

Expected: "Crew module OK"

**Step 3: Commit**

```bash
git add src/crew.py
git commit -m "feat: add hierarchical crew orchestration with manager agent"
```

---

### Task 7: Write main.py — CLI entry point for testing

**Files:**
- Create: `/home/botops/crewai-crew/src/main.py`

**Step 1: Write main.py**

```python
"""CLI entry point for testing the crew without the web UI."""

import sys

from dotenv import load_dotenv

load_dotenv()

from src.crew import run_content_crew


def main():
    task = " ".join(sys.argv[1:]) if len(sys.argv) > 1 else (
        "Research the top 5 AI coding tools in 2026 and write a blog post about them"
    )
    print(f"\n--- Running crew on: {task} ---\n")
    result = run_content_crew(task_description=task)
    print(f"\n--- RESULT ---\n{result}")


if __name__ == "__main__":
    main()
```

**Step 2: Test the crew end-to-end (requires valid ANTHROPIC_API_KEY and SERPER_API_KEY)**

```bash
cd /home/botops/crewai-crew
source .venv/bin/activate
python3 -m src.main "What are the best AI agent frameworks in 2026?"
```

Expected: Agents execute in sequence, manager delegates, final output printed. This may take 2-5 minutes depending on model speed.

If SERPER_API_KEY is not set, the search tool will fail. In that case, test with a simpler task that doesn't require web search, or get a free Serper API key from https://serper.dev.

**Step 3: Commit**

```bash
git add src/main.py
git commit -m "feat: add CLI entry point for crew testing"
```

---

## Phase 3: Streamlit Web UI

### Task 8: Write the Streamlit app — task submission and results

**Files:**
- Create: `/home/botops/crewai-crew/app.py`

**Step 1: Write app.py**

```python
"""Streamlit web UI for the content/marketing crew."""

import json
import sqlite3
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.crew import run_content_crew

DB_PATH = Path("output/history.db")


def init_db():
    """Create the history database if it doesn't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            description TEXT NOT NULL,
            content_type TEXT NOT NULL,
            platform TEXT NOT NULL,
            include_seo INTEGER NOT NULL,
            include_social INTEGER NOT NULL,
            result TEXT,
            status TEXT NOT NULL DEFAULT 'running',
            duration_seconds REAL
        )
        """
    )
    conn.commit()
    conn.close()


def save_task(description, content_type, platform, include_seo, include_social):
    """Save a new task to the database. Returns the task ID."""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.execute(
        "INSERT INTO tasks (created_at, description, content_type, platform, "
        "include_seo, include_social) VALUES (?, ?, ?, ?, ?, ?)",
        (
            datetime.now(timezone.utc).isoformat(),
            description,
            content_type,
            platform,
            int(include_seo),
            int(include_social),
        ),
    )
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return task_id


def update_task(task_id, result, status, duration):
    """Update a task with its result."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute(
        "UPDATE tasks SET result = ?, status = ?, duration_seconds = ? WHERE id = ?",
        (result, status, duration, task_id),
    )
    conn.commit()
    conn.close()


def get_history():
    """Get all past tasks."""
    if not DB_PATH.exists():
        return []
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM tasks ORDER BY created_at DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_task_by_id(task_id):
    """Get a specific task by ID."""
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


# --- Streamlit App ---

st.set_page_config(page_title="Content Crew", page_icon="📝", layout="wide")
st.title("📝 Content Crew")
st.caption("Multi-agent content creation powered by CrewAI + Claude")

init_db()

# Sidebar — History
with st.sidebar:
    st.header("History")
    history = get_history()
    if not history:
        st.info("No tasks yet. Submit one to get started.")
    for task in history:
        status_icon = "✅" if task["status"] == "complete" else (
            "❌" if task["status"] == "error" else "⏳"
        )
        if st.button(
            f"{status_icon} {task['description'][:50]}...",
            key=f"hist_{task['id']}",
        ):
            st.session_state["view_task_id"] = task["id"]

# Main area
if "view_task_id" in st.session_state:
    # Viewing a past task
    task = get_task_by_id(st.session_state["view_task_id"])
    if task:
        st.subheader(task["description"])
        col1, col2, col3 = st.columns(3)
        col1.metric("Type", task["content_type"])
        col2.metric("Platform", task["platform"])
        col3.metric(
            "Duration",
            f"{task['duration_seconds']:.0f}s" if task["duration_seconds"] else "—",
        )
        st.markdown("---")
        st.markdown(task["result"] or "*No result yet*")
    if st.button("← Back to new task"):
        del st.session_state["view_task_id"]
        st.rerun()
else:
    # New task form
    with st.form("task_form"):
        description = st.text_area(
            "What do you need?",
            placeholder="Research AI coding tools and write a blog post about them",
            height=100,
        )

        col1, col2 = st.columns(2)
        with col1:
            content_type = st.selectbox(
                "Content type",
                ["blog post", "Twitter/X thread", "LinkedIn post", "newsletter", "report"],
            )
            platform = st.selectbox(
                "Platform",
                ["blog", "twitter", "linkedin", "newsletter", "internal"],
            )
        with col2:
            include_seo = st.checkbox("Include SEO optimization", value=True)
            include_social = st.checkbox("Include social monitoring", value=False)

        submitted = st.form_submit_button("🚀 Run Crew", type="primary")

    if submitted and description:
        task_id = save_task(
            description, content_type, platform, include_seo, include_social
        )

        with st.status("Crew is working...", expanded=True) as status:
            st.write("Editor-in-Chief is analyzing the task...")
            start_time = time.time()

            try:
                result = run_content_crew(
                    task_description=description,
                    content_type=content_type,
                    platform=platform,
                    include_seo=include_seo,
                    include_social=include_social,
                )
                duration = time.time() - start_time
                update_task(task_id, result, "complete", duration)
                status.update(label="Crew finished!", state="complete")
            except Exception as e:
                duration = time.time() - start_time
                update_task(task_id, str(e), "error", duration)
                status.update(label="Crew encountered an error", state="error")
                st.error(f"Error: {e}")
                result = None

        if result:
            st.markdown("---")
            st.subheader("Result")
            st.markdown(result)

            st.download_button(
                "📥 Download as Markdown",
                data=result,
                file_name=f"crew-output-{task_id}.md",
                mime="text/markdown",
            )
```

**Step 2: Verify Streamlit can import the app**

```bash
cd /home/botops/crewai-crew
source .venv/bin/activate
python3 -c "import app; print('App imports OK')"
```

Note: This may show Streamlit warnings outside the browser — that's fine. We just want to verify no import errors.

**Step 3: Commit**

```bash
git add app.py
git commit -m "feat: add Streamlit web UI with task form, results, and history"
```

---

### Task 9: Test the full stack

**Step 1: Start Streamlit**

```bash
cd /home/botops/crewai-crew
source .venv/bin/activate
streamlit run app.py --server.port 8501
```

Expected: Streamlit opens on http://localhost:8501

**Step 2: Submit a test task**

In the web UI:
- Description: "Research the top 5 AI agent frameworks and write a brief comparison"
- Content type: blog post
- Platform: blog
- Include SEO: checked
- Include social: unchecked
- Click "Run Crew"

Expected:
1. Status shows "Crew is working..."
2. After 2-5 minutes, result appears below the form
3. Result is a structured blog post with research, SEO metadata
4. Task appears in the sidebar history
5. Download button works

**Step 3: Test history**

Click a past task in the sidebar. Verify the result displays correctly.

**Step 4: Fix any issues and commit**

```bash
git add -A
git commit -m "fix: adjustments after end-to-end testing"
```

---

## Phase 4: Polish

### Task 10: Add error handling and logging

**Files:**
- Modify: `/home/botops/crewai-crew/src/crew.py`

**Step 1: Add a logger and wrap the crew kickoff in try/except**

Add at the top of `crew.py`:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
```

Wrap `crew.kickoff()` in the `run_content_crew` function:

```python
    logger.info("Starting crew with %d agents and %d tasks", len(agents), len(tasks))
    result = crew.kickoff()
    logger.info("Crew finished successfully")
    return str(result)
```

**Step 2: Commit**

```bash
git add src/crew.py
git commit -m "feat: add logging to crew orchestration"
```

---

### Task 11: Write README.md

**Files:**
- Create: `/home/botops/crewai-crew/README.md`

**Step 1: Write README**

```markdown
# CrewAI Content Crew

Multi-agent content/marketing crew powered by CrewAI and Anthropic Claude.

## Agents

| Agent | Role | Model |
|-------|------|-------|
| Editor-in-Chief | Manager — delegates and synthesizes | Claude Opus |
| Researcher | Web research and data collection | Claude Haiku |
| Writer | Content creation | Claude Sonnet |
| SEO Strategist | Keyword research and optimization | Claude Haiku |
| Social Monitor | Brand and trend monitoring | Claude Haiku |

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your API keys
```

## Run

**Web UI:**
```bash
streamlit run app.py
```

**CLI:**
```bash
python3 -m src.main "Research AI tools and write a blog post"
```

## API Keys

- `ANTHROPIC_API_KEY` — Required. Get from https://console.anthropic.com
- `SERPER_API_KEY` — Required for web search. Get from https://serper.dev
```

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: add README with setup and usage instructions"
```

---

## Verification Checklist

After all tasks are complete, verify:

1. [ ] `python3 -m src.main` runs and produces output (CLI test)
2. [ ] `streamlit run app.py` starts the web UI
3. [ ] Submitting a task in the UI kicks off the crew
4. [ ] Editor-in-Chief delegates to Researcher, Writer, and optionally SEO/Social
5. [ ] Final result is coherent and publish-ready
6. [ ] Task history persists in SQLite and is viewable in sidebar
7. [ ] Download button exports the result as markdown
8. [ ] `.env.example` has no real keys, `.env` is gitignored
