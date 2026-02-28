# CrewAI Content/Marketing Crew — Design Document

> Approved 2026-02-28. Replaces OpenClaw swarm for content/marketing workflows.

---

## Goal

Build a CrewAI-based multi-agent crew focused on content and marketing tasks: research, writing, SEO optimization, and social monitoring. Hierarchical architecture with a manager agent (Editor-in-Chief) coordinating 4 specialist agents. Streamlit web UI for task submission and result viewing. Anthropic Claude models throughout.

---

## Architecture

**Approach:** Hierarchical process with custom manager agent.

The Editor-in-Chief receives natural language tasks, decomposes them, delegates to specialists, reviews output, and synthesizes a final deliverable. This maps to the Atlas pattern from the OpenClaw swarm but with CrewAI's built-in delegation, error handling, and verification.

```
User (Streamlit UI)
    ↓
  Editor-in-Chief (Manager, Opus)
    ↓
    ├── Researcher (Haiku) — web search, data collection, competitor analysis
    ├── Writer (Sonnet) — blog posts, threads, newsletters, copy
    ├── SEO Strategist (Haiku) — keyword research, optimization, meta tags
    └── Social Monitor (Haiku) — brand mentions, trends, social snippets
```

---

## Agents

### Editor-in-Chief (Manager)

- **Role:** Content Strategy Manager
- **Goal:** Decompose content tasks, delegate to the right specialists, review quality, and synthesize polished deliverables
- **Backstory:** Experienced editorial director who has managed content teams at major publications. Expert at identifying what research is needed, what angle to take, and how to combine specialist work into publish-ready content.
- **Model:** Claude Opus (claude-opus-4-6)
- **Tools:** None (delegation only)
- **Config:** `allow_delegation=True`

### Researcher

- **Role:** Content Researcher
- **Goal:** Find accurate, current information from web sources. Deliver structured research briefs with data, comparisons, and source URLs.
- **Backstory:** Investigative journalist turned research analyst. Thorough, fast, and source-obsessed. Never reports a claim without a URL to back it up.
- **Model:** Claude Haiku (claude-haiku-4-5)
- **Tools:** SerperDevTool (web search), ScrapeWebsiteTool (page content), WebsiteSearchTool (site-specific search)

### Writer

- **Role:** Content Writer
- **Goal:** Create compelling, publish-ready content tailored to the target platform and audience.
- **Backstory:** Senior content strategist who has written for tech blogs, newsletters, and social media. Adapts voice and format to the platform. Every piece is edited, polished, and ready to publish.
- **Model:** Claude Sonnet (claude-sonnet-4-6)
- **Tools:** FileWriterTool (save drafts to output/)

### SEO Strategist

- **Role:** SEO & Content Optimization Specialist
- **Goal:** Research keywords, analyze search intent, and optimize content for organic visibility.
- **Backstory:** Technical SEO consultant who understands both search algorithms and human readers. Optimizes without sacrificing readability. Focuses on search intent, not keyword stuffing.
- **Model:** Claude Haiku (claude-haiku-4-5)
- **Tools:** SerperDevTool (SERP analysis), ScrapeWebsiteTool (competitor content)

### Social Monitor

- **Role:** Social Intelligence Analyst
- **Goal:** Track brand mentions, competitor activity, and emerging trends across social platforms and news.
- **Backstory:** Former social media strategist who monitors the pulse of the internet. Distinguishes signal from noise. Reports only what's actionable.
- **Model:** Claude Haiku (claude-haiku-4-5)
- **Tools:** SerperDevTool (news/social search), ScrapeWebsiteTool (article extraction)

---

## Project Structure

```
/home/botops/crewai-crew/
├── src/
│   ├── __init__.py
│   ├── crew.py              # Crew definition (agents, tasks, process)
│   ├── agents.py            # Agent definitions
│   ├── tasks.py             # Task factory functions
│   ├── tools/
│   │   ├── __init__.py
│   │   └── custom_tools.py  # Any project-specific tools
│   └── config/
│       ├── agents.yaml      # Agent config (role, goal, backstory, llm)
│       └── tasks.yaml       # Task templates
├── app.py                   # Streamlit web UI
├── pyproject.toml           # Project metadata + dependencies
├── .env                     # ANTHROPIC_API_KEY, SERPER_API_KEY
├── .env.example             # Template without secrets
├── output/                  # Saved results (git-ignored)
├── docs/
│   └── plans/
│       └── 2026-02-28-crewai-content-crew-design.md  # This file
└── README.md
```

---

## Web UI (Streamlit)

### Pages

1. **Task Input** (main page)
   - Text area for natural language task description
   - Optional: select task type (blog post, competitor analysis, social scan, SEO audit)
   - "Run" button kicks off the crew
   - Shows agent activity in real-time (via CrewAI verbose output)

2. **Results**
   - Final synthesized output from Editor-in-Chief
   - Expandable sections for individual agent outputs
   - Copy-to-clipboard button
   - Save to file button

3. **History** (sidebar)
   - Past tasks with timestamps
   - Click to view previous results
   - Stored in SQLite (`output/history.db`)

### Real-time Updates

Use Streamlit's `st.status` and `st.expander` to show agent progress. CrewAI's verbose mode provides step-by-step agent actions that can be streamed to the UI.

---

## LLM Configuration

All agents use Anthropic Claude via the `litellm` integration in CrewAI:

| Agent | Model ID | Cost Tier |
|-------|----------|-----------|
| Editor-in-Chief | `anthropic/claude-opus-4-6` | High (manager decisions) |
| Researcher | `anthropic/claude-haiku-4-5` | Low (fast research) |
| Writer | `anthropic/claude-sonnet-4-6` | Medium (quality writing) |
| SEO Strategist | `anthropic/claude-haiku-4-5` | Low (data analysis) |
| Social Monitor | `anthropic/claude-haiku-4-5` | Low (monitoring) |

Environment variables:
```
ANTHROPIC_API_KEY=sk-ant-...
SERPER_API_KEY=...          # For web search tool
```

---

## Key Improvements Over OpenClaw Swarm

| Issue in OpenClaw | Fix in CrewAI |
|-------------------|---------------|
| Silent failures | CrewAI built-in error handling + verbose logging |
| No verification loops | Manager agent reviews specialist output before synthesis |
| Channel ID fragility | No Discord — agents communicate via CrewAI internals |
| Markdown state files | SQLite for task history |
| Hours of config | `pip install crewai` + Python files |
| Non-deterministic routing | Still non-deterministic (hierarchical), but CrewAI handles it more reliably |
| Opus routing overhead | Manager can optionally use Sonnet to reduce cost |

---

## Dependencies

```
crewai[tools]>=0.100.0
crewai-tools>=0.30.0
streamlit>=1.40.0
python-dotenv>=1.0.0
```

---

## Success Criteria

1. Submit "Research AI coding tools and write a blog post" via web UI
2. Editor-in-Chief delegates: Researcher gathers data, Writer produces post, SEO Strategist optimizes
3. Final output is a publish-ready blog post with SEO metadata
4. Total execution under 5 minutes
5. All agent activity visible in the web UI
6. Results saved and retrievable from history

---

## Future Extensions

- Add Flows for common pipelines (blog post flow, SEO audit flow)
- Discord integration (add as second interface alongside web UI)
- Memory/knowledge persistence between sessions
- Scheduled monitoring via cron (Social Monitor runs every 4 hours)
- Add more agents: Designer (image prompts), Analyst (performance data)
