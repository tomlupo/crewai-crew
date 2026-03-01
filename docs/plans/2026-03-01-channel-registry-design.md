# Channel Registry Pattern — Discord Crew Channels

## Summary

Auto-create dedicated Discord channels per crew type. Messages in a crew channel route directly to that crew (no LLM classification). Results reply in the crew channel and cross-post to a shared #crew-results channel. The existing single-channel smart router mode is preserved alongside.

## Architecture

```
Discord Server
├── Crews (category — auto-created)
│   ├── #crew-content      → run_content_crew()
│   ├── #crew-quant        → run_quant_crew()
│   ├── #crew-results      → aggregated output from all crews
│   └── #crew-<future>     → any new crew you register
└── (existing channels)
    └── #<DISCORD_CHANNEL_ID>  → smart router (LLM classifies, existing behavior)
```

## Crew Registry

Single dict in `src/crew_registry.py` maps crew names to runner functions, default args, and metadata:

```python
CREW_REGISTRY = {
    "content": {
        "runner": run_content_crew,
        "description": "Blog posts, landing pages, threads, newsletters",
        "default_args": {"include_seo": True, "include_social": False},
        "emoji": "📝",
    },
    "quant": {
        "runner": run_quant_crew,
        "description": "Stock analysis, financial content",
        "default_args": {},
        "emoji": "📊",
        "extract_tickers": True,
    },
}
```

Adding a new crew = one dict entry. Bot auto-creates the channel on next startup.

## Message Flow

### Dedicated crew channel (#crew-content, #crew-quant)

1. User posts message
2. Bot looks up channel_id → crew_name (no LLM needed)
3. If `extract_tickers: True`, parse tickers from message text
4. Run crew with default_args merged with parsed params
5. Reply in same channel
6. Cross-post result summary to #crew-results

### Smart router channel (DISCORD_CHANNEL_ID, existing)

1. User posts message
2. LLM classifies → routes to correct crew runner
3. Reply in same channel (no cross-post)

## Startup Behavior

```
on_ready:
  1. Find or create "Crews" category
  2. For each crew in CREW_REGISTRY:
     - Find or create #crew-{name} with description from registry
  3. Find or create #crew-results channel
  4. Build channel_id → crew_name lookup dict
  5. Log channel URLs
```

## Cross-Post Format (#crew-results)

```
📊 **Quant Research** completed (45s) — requested by @user
> Analyze NVIDIA's financials and write a LinkedIn post

[result preview or file attachment]
```

## Config

```env
# Existing (unchanged)
DISCORD_CHANNEL_ID=123456789

# New (optional)
DISCORD_GUILD_ID=987654321
DISCORD_CATEGORY_NAME=Crews
```

Bot needs `manage_channels` permission. Falls back to smart-router-only mode if missing.

## Files

- **New:** `src/crew_registry.py` — registry dict, ticker extraction, content type detection
- **Modified:** `src/discord_bot.py` — channel setup on startup, dual routing, cross-posting
