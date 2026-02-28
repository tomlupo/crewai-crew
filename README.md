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

- `OPENROUTER_API_KEY` — Required. Get from https://openrouter.ai
- `BRAVE_API_KEY` — Required for web search. Get from https://brave.com/search/api
