"""History storage for transcription results."""

import json
import time
from pathlib import Path
from datetime import datetime, timezone

HISTORY_DIR = Path.home() / ".talkrefine"
HISTORY_FILE = HISTORY_DIR / "history.json"
MAX_HISTORY = 500
TRAY_HISTORY_COUNT = 10


def _ensure_dir():
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)


def _local_timestamp() -> str:
    """Return current local time as ISO string."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def add_entry(raw_text: str, refined_text: str, duration: float,
              language: str = "", engine: str = "", llm: str = ""):
    """Add a transcription result to history."""
    _ensure_dir()
    history = load_history()
    entry = {
        "id": int(time.time() * 1000),
        "timestamp": _local_timestamp(),
        "duration": round(duration, 1),
        "raw": raw_text,
        "refined": refined_text,
        "language": language,
        "engine": engine,
        "llm": llm,
    }
    history.insert(0, entry)
    history = history[:MAX_HISTORY]
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)
    return entry


def load_history() -> list[dict]:
    """Load history from file."""
    if not HISTORY_FILE.exists():
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, Exception):
        return []


def load_recent(count: int = TRAY_HISTORY_COUNT) -> list[dict]:
    """Load most recent N entries for tray menu."""
    return load_history()[:count]


def clear_history():
    """Delete all history."""
    if HISTORY_FILE.exists():
        HISTORY_FILE.unlink()
