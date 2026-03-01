"""Discord bot for the CrewAI content crew.

Post a task in a Discord channel, the crew runs, and the result comes back.

Run with: python -m src.discord_bot
"""

import asyncio
import logging
import os
import re
import time

import discord
from dotenv import load_dotenv

load_dotenv()

from src.crew import run_content_crew
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
CHANNEL_ID = int(os.environ["DISCORD_CHANNEL_ID"])

# --- Content type detection ---

CONTENT_TYPE_PATTERNS = {
    "landing page": re.compile(r"\blanding\s*page\b", re.IGNORECASE),
    "Twitter/X thread": re.compile(r"\b(twitter|tweet|x\s*thread)\b", re.IGNORECASE),
    "LinkedIn post": re.compile(r"\blinkedin\b", re.IGNORECASE),
    "newsletter": re.compile(r"\bnewsletter\b", re.IGNORECASE),
    "report": re.compile(r"\breport\b", re.IGNORECASE),
}

PLATFORM_MAP = {
    "landing page": "website",
    "Twitter/X thread": "twitter",
    "LinkedIn post": "linkedin",
    "newsletter": "newsletter",
    "report": "internal",
    "blog post": "blog",
}


def detect_content_type(text: str) -> str:
    """Detect content type from message text via keyword matching."""
    for content_type, pattern in CONTENT_TYPE_PATTERNS.items():
        if pattern.search(text):
            return content_type
    return "blog post"


def detect_platform(content_type: str) -> str:
    """Map content type to platform."""
    return PLATFORM_MAP.get(content_type, "blog")


# --- Discord bot ---

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Track active tasks to prevent duplicates
active_messages: set[int] = set()


@client.event
async def on_ready():
    logger.info("Logged in as %s (id=%s)", client.user, client.user.id)
    channel = client.get_channel(CHANNEL_ID)
    if channel:
        logger.info("Watching channel: #%s", channel.name)
    else:
        logger.warning("Channel %s not found — check DISCORD_CHANNEL_ID", CHANNEL_ID)


@client.event
async def on_message(message: discord.Message):
    # Ignore own messages
    if message.author == client.user:
        return

    # Only respond in the configured channel
    if message.channel.id != CHANNEL_ID:
        return

    # Ignore messages that are already being processed
    if message.id in active_messages:
        return

    # Ignore very short messages (likely not a task)
    text = message.content.strip()
    if len(text) < 10:
        return

    active_messages.add(message.id)
    try:
        await process_task(message, text)
    finally:
        active_messages.discard(message.id)


async def process_task(message: discord.Message, text: str):
    """Run the crew for a Discord message and post the result."""
    content_type = detect_content_type(text)
    platform = detect_platform(content_type)

    # Reply with status
    status_msg = await message.reply(
        f"**Working on it...** (type: {content_type}, platform: {platform})"
    )

    # Save to shared DB
    init_db()
    task_id = save_task(
        description=text,
        content_type=content_type,
        platform=platform,
        include_seo=True,
        include_social=False,
    )

    logger.info(
        "Task #%d started for message %s from %s",
        task_id,
        message.id,
        message.author,
    )

    # Run the blocking crew in a thread executor
    loop = asyncio.get_running_loop()
    start_time = time.time()

    try:
        result = await loop.run_in_executor(
            None,
            lambda: run_content_crew(
                task_description=text,
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

    # Decide how to send the result
    html = is_html_output(content_type, result)

    if html:
        # HTML always goes as a file attachment
        clean = strip_code_fences(result)
        await message.reply(
            f"Here's your {content_type}:",
            file=discord.File(fp=filepath, filename=filepath.name),
        )
    elif len(result) <= 1900:
        # Short text fits in a message
        await message.reply(f"**Result:**\n\n{result}")
    else:
        # Long text: preview + file attachment
        preview = result[:1500] + "\n\n*(truncated — see attached file)*"
        await message.reply(
            preview,
            file=discord.File(fp=filepath, filename=filepath.name),
        )


def main():
    init_db()
    logger.info("Starting Discord bot...")
    client.run(BOT_TOKEN, log_handler=None)


if __name__ == "__main__":
    main()
