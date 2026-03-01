# CrewAI Content Crew

Multi-agent content and quant research crew powered by CrewAI and Anthropic Claude, with Antfarm-style reliability patterns.

## Agents

### Content Crew

| Agent | Role | Model |
|-------|------|-------|
| Researcher | Web research and data collection | Claude Haiku |
| Writer | Content creation | Claude Sonnet |
| SEO Strategist | Keyword research and optimization | Claude Haiku |
| Social Monitor | Brand and trend monitoring | Claude Haiku |

### Quant Research Crew

| Agent | Role | Model |
|-------|------|-------|
| Quant Researcher | Financial data via YFinance + web news | Claude Haiku |
| Data Analyst | Interpret data, calculate trends | Claude Sonnet |
| Financial Writer | Platform-specific financial content | Claude Sonnet |

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

**Discord Bot:**
```bash
python3 -m src.discord_bot
```

## CrewFarm (Reliability Layer)

Each task runs as an isolated mini-crew with fresh context, structured KEY: value output, and verification gates. Everything is logged to SQLite.

| Feature | How it works |
|---------|-------------|
| Context isolation | Fresh `Crew()` per step — no shared context window bloat |
| Verification gates | `expects`, `required_keys`, custom checks on every step |
| Retry with feedback | Failed steps retry with the error message injected |
| State tracking | Every run, step, and retry logged to `crewfarm_db.sqlite` |
| Verifier agent | Separate QA agent checks work (cheap model, e.g. Haiku) |

```bash
# Query run history
sqlite3 crewfarm_db.sqlite "SELECT id, workflow_name, status FROM runs ORDER BY created_at DESC LIMIT 10"

# See steps for a run
sqlite3 crewfarm_db.sqlite "SELECT step_id, agent_name, status, attempt FROM steps WHERE run_id = 'abc123'"
```

## Discord Channels

The bot auto-creates per-crew channels on startup:

```
Crews/
├── #crew-content      → post task, content crew runs
├── #crew-quant        → post task, quant crew runs
└── #crew-results      → aggregated output from all crews
```

Adding a new crew: one entry in `src/crew_registry.py` → channel auto-created on next startup.

The existing single-channel smart-router mode (LLM classifies the task) still works alongside via `DISCORD_CHANNEL_ID`.

## API Keys

| Variable | Required | Source |
|----------|----------|--------|
| `OPENROUTER_API_KEY` | Yes | https://openrouter.ai |
| `BRAVE_API_KEY` | Yes (for web search) | https://brave.com/search/api |
| `DISCORD_BOT_TOKEN` | For Discord bot | https://discord.com/developers |
| `DISCORD_CHANNEL_ID` | Optional (smart-router) | Discord channel ID |
| `DISCORD_GUILD_ID` | Optional (auto-create channels) | Discord server ID |
| `DISCORD_CATEGORY_NAME` | Optional (default: "Crews") | Category name for crew channels |
