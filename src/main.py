"""CLI entry point — run the crew and auto-save output."""

import argparse
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from src.crew import run_content_crew

OUTPUT_DIR = Path("output")


def slugify(text: str, max_len: int = 50) -> str:
    """Turn a task description into a filename-safe slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:max_len].rstrip("-")


def strip_code_fences(text: str) -> str:
    """Remove markdown code fences if the model wrapped the output."""
    t = text.strip()
    if t.startswith("```html"):
        t = t[7:].strip()
    elif t.startswith("```"):
        t = t[3:].strip()
    if t.endswith("```"):
        t = t[:-3].strip()
    return t


def save_output(result: str, task: str, content_type: str) -> Path:
    """Save crew output to file with appropriate extension."""
    OUTPUT_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    slug = slugify(task)

    # Detect HTML output
    is_html = (
        content_type in ("landing page", "html page", "webpage", "website")
        or "<!DOCTYPE html>" in result[:200].upper()
        or "<html" in result[:200].lower()
    )

    if is_html:
        result = strip_code_fences(result)
        ext = ".html"
    else:
        ext = ".md"

    filename = f"{timestamp}-{slug}{ext}"
    filepath = OUTPUT_DIR / filename
    filepath.write_text(result, encoding="utf-8")
    return filepath


def open_file(filepath: Path) -> None:
    """Open the output file in the default browser/viewer."""
    try:
        if sys.platform == "darwin":
            subprocess.run(["open", str(filepath)], check=False)
        elif sys.platform == "linux":
            subprocess.run(["xdg-open", str(filepath)], check=False)
        elif sys.platform == "win32":
            os.startfile(str(filepath))
    except Exception:
        pass  # Non-critical — user can open manually


def main():
    parser = argparse.ArgumentParser(description="Run the CrewAI content crew")
    parser.add_argument("task", nargs="*", help="Task description")
    parser.add_argument(
        "--type",
        "-t",
        default="blog post",
        dest="content_type",
        help="Content type: 'blog post', 'landing page', 'thread', 'newsletter'",
    )
    parser.add_argument("--platform", "-p", default="blog", help="Target platform")
    parser.add_argument("--audience", "-a", default="tech professionals")
    parser.add_argument("--tone", default="informative and engaging")
    parser.add_argument("--seo", action="store_true", default=True)
    parser.add_argument("--no-seo", action="store_false", dest="seo")
    parser.add_argument("--social", action="store_true", default=False)
    parser.add_argument("--no-open", action="store_true", help="Don't auto-open output")

    args = parser.parse_args()
    task = (
        " ".join(args.task)
        if args.task
        else ("Research the top 5 AI coding tools and write a blog post")
    )

    print(f"\n--- Crew starting: {task} ---")
    print(f"    Type: {args.content_type} | Platform: {args.platform}")
    print(
        f"    SEO: {'yes' if args.seo else 'no'} | Social: {'yes' if args.social else 'no'}\n"
    )

    result = run_content_crew(
        task_description=task,
        content_type=args.content_type,
        platform=args.platform,
        audience=args.audience,
        tone=args.tone,
        include_seo=args.seo,
        include_social=args.social,
    )

    filepath = save_output(str(result), task, args.content_type)
    print(f"\n--- Done! Output saved to: {filepath} ---")

    if not args.no_open:
        open_file(filepath)


if __name__ == "__main__":
    main()
