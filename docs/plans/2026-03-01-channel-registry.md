# Channel Registry Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Auto-create per-crew Discord channels so each crew gets its own intake channel, with results cross-posted to a shared #crew-results channel.

**Architecture:** A `CREW_REGISTRY` dict maps crew names to runner functions. On startup the bot finds-or-creates channels under a "Crews" category. `on_message` checks if the channel belongs to a registered crew (direct route) or the smart-router channel (LLM classify). Result delivery replies in-channel and cross-posts to #crew-results.

**Tech Stack:** discord.py (existing), no new dependencies.

---

### Task 1: Create crew_registry.py

**Files:**
- Create: `src/crew_registry.py`

**Step 1: Write the registry module**

```python
"""Crew registry — maps crew names to runner functions and metadata.

Adding a new crew: add one entry to CREW_REGISTRY.
The Discord bot auto-creates a channel for it on startup.
"""

import re

from src.crew import run_content_crew
from src.quant_crew import run_quant_crew


CREW_REGISTRY: dict[str, dict] = {
    "content": {
        "runner": run_content_crew,
        "description": "Blog posts, landing pages, threads, newsletters",
        "default_args": {"include_seo": True, "include_social": False},
        "emoji": "\U0001f4dd",
    },
    "quant": {
        "runner": run_quant_crew,
        "description": "Stock analysis, financial content",
        "default_args": {},
        "emoji": "\U0001f4ca",
        "extract_tickers": True,
    },
}

# Matches $NVDA, $AAPL, or bare uppercase 2-5 letter words after commas
_TICKER_RE = re.compile(r"\$([A-Z]{1,5})\b")
_COMMA_SEP_RE = re.compile(r"^[A-Z]{1,5}(?:\s*,\s*[A-Z]{1,5})+$")


def extract_tickers(text: str) -> list[str]:
    """Pull stock tickers from message text.

    Recognises $NVDA style cashtags and comma-separated lists like
    'NVDA, AAPL, MSFT'.
    """
    # Cashtag style: $NVDA
    tickers = _TICKER_RE.findall(text)

    # Comma-separated at start of message: "NVDA, AAPL analyze these"
    first_line = text.split("\n")[0].strip()
    for segment in first_line.split(" "):
        segment = segment.strip().rstrip(".")
        if _COMMA_SEP_RE.match(segment):
            tickers.extend(t.strip() for t in segment.split(",") if t.strip())

    # Dedupe preserving order
    seen: set[str] = set()
    result: list[str] = []
    for t in tickers:
        t = t.upper()
        if t not in seen:
            seen.add(t)
            result.append(t)
    return result
```

**Step 2: Verify it imports**

Run: `cd /home/botops/crewai-crew && source .venv/bin/activate && python -c "from src.crew_registry import CREW_REGISTRY, extract_tickers; print(list(CREW_REGISTRY.keys())); print(extract_tickers('Analyze \$NVDA and \$AAPL'))"`
Expected: `['content', 'quant']` and `['NVDA', 'AAPL']`

**Step 3: Commit**

```bash
git add src/crew_registry.py
git commit -m "feat: add crew registry mapping crew names to runners"
```

---

### Task 2: Add channel setup on bot startup

**Files:**
- Modify: `src/discord_bot.py:37-42` (config section)
- Modify: `src/discord_bot.py:143-160` (client setup and on_ready)

**Step 1: Add new config vars and channel state**

Replace the config section (lines 37-42) with:

```python
# --- Configuration ---

BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
CHANNEL_ID = int(os.environ.get("DISCORD_CHANNEL_ID", "0"))
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
GUILD_ID = int(os.environ.get("DISCORD_GUILD_ID", "0"))
CATEGORY_NAME = os.environ.get("DISCORD_CATEGORY_NAME", "Crews")
```

**Step 2: Add channel state tracking after `active_messages`**

After line 150 (`active_messages: set[int] = set()`), add:

```python

# Channel routing: channel_id → crew_name (populated on_ready)
channel_to_crew: dict[int, str] = {}
results_channel_id: int | None = None
```

**Step 3: Import crew registry at the top of the file**

Add after the `from src.db import ...` block:

```python
from src.crew_registry import CREW_REGISTRY, extract_tickers
```

**Step 4: Rewrite on_ready to find-or-create channels**

Replace the `on_ready` function with:

```python
@client.event
async def on_ready():
    global results_channel_id
    logger.info("Logged in as %s (id=%s)", client.user, client.user.id)

    # Smart-router channel (existing behavior)
    if CHANNEL_ID:
        channel = client.get_channel(CHANNEL_ID)
        if channel:
            logger.info("Smart-router channel: #%s", channel.name)
        else:
            logger.warning("DISCORD_CHANNEL_ID %s not found", CHANNEL_ID)

    # --- Auto-create crew channels ---
    guild = None
    if GUILD_ID:
        guild = client.get_guild(GUILD_ID)
    elif client.guilds:
        guild = client.guilds[0]

    if not guild:
        logger.warning("No guild found — crew channels disabled")
        return

    # Check manage_channels permission
    me = guild.me
    if not me or not me.guild_permissions.manage_channels:
        logger.warning(
            "Missing manage_channels permission in %s — crew channels disabled",
            guild.name,
        )
        return

    # Find or create category
    category = discord.utils.get(guild.categories, name=CATEGORY_NAME)
    if not category:
        category = await guild.create_category(CATEGORY_NAME)
        logger.info("Created category: %s", CATEGORY_NAME)

    # Find or create per-crew channels
    for crew_name, crew_config in CREW_REGISTRY.items():
        channel_name = f"crew-{crew_name}"
        ch = discord.utils.get(category.text_channels, name=channel_name)
        if not ch:
            ch = await guild.create_text_channel(
                channel_name,
                category=category,
                topic=f"{crew_config['emoji']} {crew_config['description']}",
            )
            logger.info("Created channel: #%s", channel_name)
        channel_to_crew[ch.id] = crew_name
        logger.info("Crew channel: #%s → %s", ch.name, crew_name)

    # Find or create results channel
    results_ch = discord.utils.get(category.text_channels, name="crew-results")
    if not results_ch:
        results_ch = await guild.create_text_channel(
            "crew-results",
            category=category,
            topic="Aggregated results from all crews",
        )
        logger.info("Created channel: #crew-results")
    results_channel_id = results_ch.id
    logger.info("Results channel: #%s", results_ch.name)
```

**Step 5: Verify syntax**

Run: `python -c "import ast; ast.parse(open('src/discord_bot.py').read()); print('syntax OK')"`
Expected: `syntax OK`

**Step 6: Commit**

```bash
git add src/discord_bot.py
git commit -m "feat: auto-create crew channels on Discord bot startup"
```

---

### Task 3: Add dual routing in on_message

**Files:**
- Modify: `src/discord_bot.py` (on_message handler)

**Step 1: Replace the on_message handler**

Replace the current `on_message` function with:

```python
@client.event
async def on_message(message: discord.Message):
    # Ignore own messages
    if message.author == client.user:
        return

    # Ignore messages already being processed
    if message.id in active_messages:
        return

    text = message.content.strip()
    if len(text) < 10:
        return

    # --- Route by channel ---
    crew_name = channel_to_crew.get(message.channel.id)

    if crew_name:
        # Dedicated crew channel — direct route, no LLM classification
        active_messages.add(message.id)
        try:
            await process_crew_task(message, text, crew_name)
        finally:
            active_messages.discard(message.id)

    elif CHANNEL_ID and message.channel.id == CHANNEL_ID:
        # Smart-router channel — LLM classifies (existing behavior)
        active_messages.add(message.id)
        try:
            await process_task(message, text)
        finally:
            active_messages.discard(message.id)
```

**Step 2: Verify syntax**

Run: `python -c "import ast; ast.parse(open('src/discord_bot.py').read()); print('syntax OK')"`

**Step 3: Commit**

```bash
git add src/discord_bot.py
git commit -m "feat: add dual routing — crew channels vs smart-router"
```

---

### Task 4: Add process_crew_task function

**Files:**
- Modify: `src/discord_bot.py` (add new function before `process_task`)

**Step 1: Add the dedicated-channel task processor**

Add this function before the existing `process_task` function:

```python
async def process_crew_task(message: discord.Message, text: str, crew_name: str):
    """Run a crew from a dedicated crew channel — no LLM classification needed."""
    crew_config = CREW_REGISTRY[crew_name]
    emoji = crew_config["emoji"]

    # Parse content type hints from message
    content_type = "blog post"
    platform = "blog"
    for ct in VALID_CONTENT_TYPES:
        if ct.lower() in text.lower():
            content_type = ct
            platform = PLATFORM_MAP.get(ct, "blog")
            break

    # Extract tickers if crew supports it
    tickers = []
    if crew_config.get("extract_tickers"):
        tickers = extract_tickers(text)

    # Status reply
    ticker_str = f", tickers: {', '.join(tickers)}" if tickers else ""
    status_msg = await message.reply(
        f"{emoji} **Working on it...** ({crew_name} crew{ticker_str})"
    )

    # Save to DB
    init_db()
    task_id = save_task(
        description=text,
        content_type=content_type,
        platform=platform,
        include_seo=crew_config.get("default_args", {}).get("include_seo", False),
        include_social=crew_config.get("default_args", {}).get("include_social", False),
        crew_type=crew_name,
    )

    logger.info(
        "Task #%d started (crew=%s, channel=dedicated) from %s: %s",
        task_id, crew_name, message.author, text[:80],
    )

    # Run crew
    loop = asyncio.get_running_loop()
    start_time = time.time()

    try:
        runner = crew_config["runner"]
        kwargs = dict(crew_config.get("default_args", {}))
        kwargs["task_description"] = text
        kwargs["content_type"] = content_type
        kwargs["platform"] = platform
        if tickers and crew_config.get("extract_tickers"):
            kwargs["tickers"] = tickers

        result = await loop.run_in_executor(None, lambda: runner(**kwargs))
        duration = time.time() - start_time
        update_task(task_id, result, "complete", duration)
        logger.info("Task #%d completed in %.0fs", task_id, duration)

    except Exception as e:
        duration = time.time() - start_time
        update_task(task_id, str(e), "error", duration)
        logger.exception("Task #%d failed after %.0fs", task_id, duration)
        await status_msg.edit(content=f"**Error** (after {duration:.0f}s): {e}")
        return

    # Reply in crew channel
    await status_msg.edit(content=f"{emoji} **Done!** (took {duration:.0f}s)")
    filepath = save_output_file(result, content_type, task_id)
    await send_result(message, result, content_type, filepath)

    # Cross-post to results channel
    await cross_post_result(
        message, result, content_type, filepath, crew_name, emoji, duration,
    )
```

**Step 2: Verify syntax**

Run: `python -c "import ast; ast.parse(open('src/discord_bot.py').read()); print('syntax OK')"`

**Step 3: Commit**

```bash
git add src/discord_bot.py
git commit -m "feat: add process_crew_task for dedicated channel routing"
```

---

### Task 5: Extract send_result and add cross_post_result

**Files:**
- Modify: `src/discord_bot.py` (refactor result delivery, add cross-post)

**Step 1: Extract result delivery into a reusable function**

Add before `process_task`:

```python
async def send_result(
    message: discord.Message,
    result: str,
    content_type: str,
    filepath,
):
    """Send crew result as a Discord reply — handles HTML, long text, and short text."""
    html = is_html_output(content_type, result)

    if html:
        clean = strip_code_fences(result)
        await message.reply(
            f"Here's your {content_type}:",
            file=discord.File(fp=filepath, filename=filepath.name),
        )
    elif len(result) <= 1900:
        await message.reply(f"**Result:**\n\n{result}")
    else:
        preview = result[:1500] + "\n\n*(truncated — see attached file)*"
        await message.reply(
            preview,
            file=discord.File(fp=filepath, filename=filepath.name),
        )


async def cross_post_result(
    message: discord.Message,
    result: str,
    content_type: str,
    filepath,
    crew_name: str,
    emoji: str,
    duration: float,
):
    """Cross-post a result summary to #crew-results."""
    if not results_channel_id:
        return

    results_ch = client.get_channel(results_channel_id)
    if not results_ch:
        return

    # Build summary
    preview = result[:300].replace("\n", " ")
    if len(result) > 300:
        preview += "..."

    summary = (
        f"{emoji} **{crew_name.title()}** completed ({duration:.0f}s) "
        f"— requested by {message.author.mention}\n"
        f"> {message.content[:200]}\n\n"
        f"{preview}"
    )

    html = is_html_output(content_type, result)
    if html or len(result) > 1900:
        await results_ch.send(
            summary,
            file=discord.File(fp=filepath, filename=filepath.name),
        )
    else:
        await results_ch.send(summary)
```

**Step 2: Update `process_task` to use `send_result`**

Replace the result delivery section at the bottom of `process_task` (from `# Save output file` to end) with:

```python
    # Save output file
    filepath = save_output_file(result, content_type, task_id)
    await send_result(message, result, content_type, filepath)
```

**Step 3: Verify syntax**

Run: `python -c "import ast; ast.parse(open('src/discord_bot.py').read()); print('syntax OK')"`

**Step 4: Commit**

```bash
git add src/discord_bot.py
git commit -m "feat: extract send_result, add cross_post_result to #crew-results"
```

---

### Task 6: Update .env.example and verify full import

**Files:**
- Modify: `.env.example`

**Step 1: Add new env vars to .env.example**

Append to `.env.example`:

```
DISCORD_GUILD_ID=REPLACE_ME
DISCORD_CATEGORY_NAME=Crews
```

**Step 2: Verify the full bot imports cleanly**

Run: `cd /home/botops/crewai-crew && source .venv/bin/activate && python -c "from src.discord_bot import main, channel_to_crew, results_channel_id; print('All imports OK')"`
Expected: `All imports OK`

**Step 3: Commit**

```bash
git add .env.example src/discord_bot.py
git commit -m "feat: add guild/category config for auto-created crew channels"
```
