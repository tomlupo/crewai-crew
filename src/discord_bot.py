"""Discord bot for the CrewAI content crew.

Post a task in a Discord channel, the crew runs, and the result comes back.

Run with: python -m src.discord_bot
"""

import asyncio
import json
import logging
import os
import time

import discord
import httpx
from dotenv import load_dotenv

load_dotenv()

from src.crew import run_content_crew
from src.quant_crew import run_quant_crew
from src.crew_registry import CREW_REGISTRY, extract_tickers
from src.db import (
    init_db,
    is_html_output,
    save_output_file,
    save_task,
    strip_code_fences,
    update_task,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("discord_bot")

# --- Configuration ---

BOT_TOKEN = os.environ["DISCORD_BOT_TOKEN"]
CHANNEL_ID = int(os.environ.get("DISCORD_CHANNEL_ID", "0"))
OPENROUTER_API_KEY = os.environ["OPENROUTER_API_KEY"]
GUILD_ID = int(os.environ.get("DISCORD_GUILD_ID", "0"))
CATEGORY_NAME = os.environ.get("DISCORD_CATEGORY_NAME", "Crews")

# --- Content type detection via LLM ---

VALID_CONTENT_TYPES = [
    "blog post",
    "landing page",
    "Twitter/X thread",
    "LinkedIn post",
    "newsletter",
    "report",
]

PLATFORM_MAP = {
    "landing page": "website",
    "Twitter/X thread": "twitter",
    "LinkedIn post": "linkedin",
    "newsletter": "newsletter",
    "report": "internal",
    "blog post": "blog",
}

CLASSIFY_SYSTEM = """You are a task classifier that routes requests to either a content creation crew or a quantitative research crew.

Respond with ONLY a JSON object (no markdown fences, no explanation).
Fields:
- "crew": "quant" or "content"
- "content_type": one of "blog post", "landing page", "Twitter/X thread", "LinkedIn post", "newsletter", "report"
- "platform": one of "blog", "website", "twitter", "linkedin", "newsletter", "internal"
- "description": a clean task description
- "tickers": list of stock ticker symbols mentioned or implied (e.g. ["NVDA", "AAPL"]). Empty list if none.

Crew routing rules:
- Use "quant" when the request involves: stock tickers, financial metrics, earnings, revenue, valuation, market cap, P/E ratio, EPS, margins, stock analysis, company financials, "analyze a company", price performance, investment analysis
- Use "content" for everything else: blog posts, landing pages, marketing content, general writing

Content type rules:
- webpage / HTML page / landing page → "landing page" / "website"
- Twitter / X / tweet / thread → "Twitter/X thread" / "twitter"
- LinkedIn → "LinkedIn post" / "linkedin"
- newsletter / email → "newsletter" / "newsletter"
- report / analysis / internal doc → "report" / "internal"
- anything else or general requests → "blog post" / "blog"
- The description should be a clear brief, even if the user's message is casual or vague"""


async def classify_message(text: str) -> dict:
    """Use Haiku via OpenRouter to classify the message intent."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "anthropic/claude-haiku-4-5",
                    "messages": [
                        {"role": "system", "content": CLASSIFY_SYSTEM},
                        {"role": "user", "content": text},
                    ],
                    "temperature": 0,
                    "max_tokens": 200,
                },
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"].strip()
            # Strip markdown fences if model wraps the JSON
            if content.startswith("```"):
                # Remove opening fence (```json or ```) and closing fence
                lines = content.split("\n")
                # Drop first line (```json) and last line (```)
                inner = "\n".join(
                    line for line in lines if not line.strip().startswith("```")
                )
                content = inner.strip()
            parsed = json.loads(content)
            # Validate crew
            if parsed.get("crew") not in ("quant", "content"):
                parsed["crew"] = "content"
            # Validate content_type
            if parsed.get("content_type") not in VALID_CONTENT_TYPES:
                parsed["content_type"] = "blog post"
            if parsed.get("platform") not in PLATFORM_MAP.values():
                parsed["platform"] = PLATFORM_MAP.get(parsed["content_type"], "blog")
            if not parsed.get("description"):
                parsed["description"] = text
            if not isinstance(parsed.get("tickers"), list):
                parsed["tickers"] = []
            return parsed
    except Exception as e:
        logger.warning("LLM classification failed: %s: %s", type(e).__name__, e)
        return {
            "crew": "content",
            "content_type": "blog post",
            "platform": "blog",
            "description": text,
            "tickers": [],
        }


# --- Discord bot ---

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Track active tasks to prevent duplicates
active_messages: set[int] = set()

# Channel routing: channel_id -> crew_name (populated on_ready)
channel_to_crew: dict[int, str] = {}
results_channel_id: int | None = None


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
        task_id,
        crew_name,
        message.author,
        text[:80],
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
        message,
        result,
        content_type,
        filepath,
        crew_name,
        emoji,
        duration,
    )


async def process_task(message: discord.Message, text: str):
    """Run the crew for a Discord message and post the result."""
    # Classify the message with LLM
    classification = await classify_message(text)
    crew_type = classification["crew"]
    content_type = classification["content_type"]
    platform = classification["platform"]
    description = classification["description"]
    tickers = classification["tickers"]

    # Reply with status
    if crew_type == "quant":
        ticker_str = ", ".join(tickers) if tickers else "none"
        status_msg = await message.reply(
            f"**Working on it...** (Quant Research crew | type: {content_type}, tickers: {ticker_str})"
        )
    else:
        status_msg = await message.reply(
            f"**Working on it...** (Content crew | type: {content_type}, platform: {platform})"
        )

    # Save to shared DB
    init_db()
    task_id = save_task(
        description=description,
        content_type=content_type,
        platform=platform,
        include_seo=(crew_type == "content"),
        include_social=False,
        crew_type=crew_type,
    )

    logger.info(
        "Task #%d started (crew=%s) for message %s from %s: %s",
        task_id,
        crew_type,
        message.id,
        message.author,
        description[:80],
    )

    # Run the blocking crew in a thread executor
    loop = asyncio.get_running_loop()
    start_time = time.time()

    try:
        if crew_type == "quant":
            result = await loop.run_in_executor(
                None,
                lambda: run_quant_crew(
                    task_description=description,
                    tickers=tickers or None,
                    content_type=content_type,
                    platform=platform,
                ),
            )
        else:
            result = await loop.run_in_executor(
                None,
                lambda: run_content_crew(
                    task_description=description,
                    content_type=content_type,
                    platform=platform,
                    include_seo=True,
                    include_social=False,
                ),
            )
        duration = time.time() - start_time
        update_task(task_id, result, "complete", duration)
        logger.info("Task #%d completed in %.0fs", task_id, duration)

    except Exception as e:
        duration = time.time() - start_time
        update_task(task_id, str(e), "error", duration)
        logger.exception("Task #%d failed after %.0fs", task_id, duration)
        await status_msg.edit(content=f"**Error** (after {duration:.0f}s): {e}")
        return

    # Update status message
    await status_msg.edit(content=f"**Done!** (took {duration:.0f}s)")

    # Save output file
    filepath = save_output_file(result, content_type, task_id)
    await send_result(message, result, content_type, filepath)


def main():
    init_db()
    logger.info("Starting Discord bot...")
    client.run(BOT_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
