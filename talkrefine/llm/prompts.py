"""Prompt template loader."""

import os
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"


def load_prompt(name_or_path: str) -> str:
    """Load a prompt template by name or file path.

    Built-in prompts: "default", "meeting", "code"
    Custom: provide a path to a .txt file
    """
    # Check if it's a built-in prompt
    builtin = PROMPTS_DIR / f"{name_or_path}.txt"
    if builtin.exists():
        return builtin.read_text(encoding="utf-8")

    # Check if it's a file path
    custom = Path(name_or_path)
    if custom.exists():
        return custom.read_text(encoding="utf-8")

    # Fallback to default
    default = PROMPTS_DIR / "default.txt"
    if default.exists():
        return default.read_text(encoding="utf-8")

    # Hardcoded fallback
    return (
        "Convert the following speech transcription into clean written text. "
        "Remove filler words and repetition. Output only the result.\n\n"
        "Raw text: {text}"
    )
