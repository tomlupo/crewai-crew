"""CLI entry point for testing the crew without the web UI."""

import sys

from dotenv import load_dotenv

load_dotenv()

from src.crew import run_content_crew


def main():
    task = (
        " ".join(sys.argv[1:])
        if len(sys.argv) > 1
        else (
            "Research the top 5 AI coding tools in 2026 and write a blog post about them"
        )
    )
    print(f"\n--- Running crew on: {task} ---\n")
    result = run_content_crew(task_description=task)
    print(f"\n--- RESULT ---\n{result}")


if __name__ == "__main__":
    main()
