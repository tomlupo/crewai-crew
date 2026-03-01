"""
Output parsing and verification for CrewAI tasks.

Antfarm pattern: every step output must contain `expects:` string and
communicate via KEY: value pairs that become variables for later steps.
"""

import re
from typing import Any


def extract_key_values(output: str) -> dict[str, Any]:
    """
    Parse KEY: value pairs from agent output.

    Antfarm convention: agents communicate structured data via
    KEY: value lines in their output. Keys are uppercase.
    Multi-line values continue until the next KEY: line.

    Example output:
        STATUS: done
        FINDINGS: The analysis shows three key trends...
        SCORE: 8.5
        DATA: {"funds": [{"name": "X", "sharpe": 1.2}]}

    Returns:
        {"status": "done", "findings": "The analysis shows...",
         "score": "8.5", "data": '{"funds": [...]}'}
    """
    result = {}
    current_key = None
    current_value_lines = []

    for line in output.split("\n"):
        # Match KEY: value pattern (key is uppercase letters/underscores/numbers)
        match = re.match(r"^([A-Z][A-Z0-9_]*)\s*:\s*(.*)$", line.strip())

        if match:
            # Save previous key-value pair
            if current_key is not None:
                result[current_key] = "\n".join(current_value_lines).strip()

            current_key = match.group(1).lower()
            current_value_lines = [match.group(2)]
        elif current_key is not None:
            # Continuation of multi-line value
            current_value_lines.append(line)

    # Save last key-value pair
    if current_key is not None:
        result[current_key] = "\n".join(current_value_lines).strip()

    return result


def verify_output(
    output: str,
    expects: str | None = None,
    required_keys: list[str] | None = None,
    custom_checks: list[callable] | None = None,
) -> tuple[bool, str | None]:
    """
    Verify agent output meets requirements.

    Antfarm pattern: `expects: "STATUS: done"` in workflow.yml.
    We extend this with additional verification layers.

    Args:
        output: Raw agent output string
        expects: String that must appear in output (Antfarm's expects:)
        required_keys: List of KEY names that must be present in parsed output
        custom_checks: List of callables that take (output, parsed_keys) and
                        return (bool, error_msg)

    Returns:
        (passed: bool, error_message: str | None)
    """
    # --- CHECK 1: expects string (Antfarm core pattern) ---
    if expects and expects not in output:
        return False, f"Expected string '{expects}' not found in output"

    # --- CHECK 2: required keys present ---
    if required_keys:
        parsed = extract_key_values(output)
        missing = [k for k in required_keys if k.lower() not in parsed]
        if missing:
            return False, f"Missing required keys: {missing}"

    # --- CHECK 3: custom verification functions ---
    if custom_checks:
        parsed = extract_key_values(output)
        for check in custom_checks:
            passed, error = check(output, parsed)
            if not passed:
                return False, error

    return True, None


# --- REUSABLE CUSTOM CHECKS ---


def check_non_empty(*keys: str):
    """Verify specified keys have non-empty values."""

    def _check(output: str, parsed: dict) -> tuple[bool, str | None]:
        for key in keys:
            k = key.lower()
            if k not in parsed or not parsed[k].strip():
                return False, f"Key '{key}' is empty or missing"
        return True, None

    return _check


def check_numeric(*keys: str):
    """Verify specified keys contain numeric values."""

    def _check(output: str, parsed: dict) -> tuple[bool, str | None]:
        for key in keys:
            k = key.lower()
            if k not in parsed:
                return False, f"Key '{key}' missing"
            try:
                float(parsed[k].strip())
            except ValueError:
                return False, f"Key '{key}' is not numeric: '{parsed[k].strip()}'"
        return True, None

    return _check


def check_json_parseable(*keys: str):
    """Verify specified keys contain valid JSON."""
    import json

    def _check(output: str, parsed: dict) -> tuple[bool, str | None]:
        for key in keys:
            k = key.lower()
            if k not in parsed:
                return False, f"Key '{key}' missing"
            try:
                json.loads(parsed[k].strip())
            except json.JSONDecodeError as e:
                return False, f"Key '{key}' is not valid JSON: {e}"
        return True, None

    return _check


def check_min_length(key: str, min_chars: int):
    """Verify a key's value meets minimum length."""

    def _check(output: str, parsed: dict) -> tuple[bool, str | None]:
        k = key.lower()
        if k not in parsed:
            return False, f"Key '{key}' missing"
        if len(parsed[k].strip()) < min_chars:
            return (
                False,
                f"Key '{key}' too short ({len(parsed[k].strip())} chars, need {min_chars})",
            )
        return True, None

    return _check
