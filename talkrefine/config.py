"""Configuration management for TalkRefine."""

import os
import copy
from pathlib import Path

DEFAULTS = {
    "hotkey": "f6",
    "cancel_key": "esc",
    "language": "auto",
    "ui_language": "zh",
    "asr": {
        "engine": "sensevoice",
        "model": "iic/SenseVoiceSmall",
        "device": "cpu",
    },
    "llm": {
        "enabled": True,
        "provider": "ollama",
        "endpoint": "http://localhost:11434",
        "model": "qwen3.5:2b",
        "api_key": "",
        "prompt": "default",
        "temperature": 0.1,
        "max_tokens": 512,
    },
    "output": {
        "auto_paste": True,
        "preserve_clipboard": True,
    },
    "ui": {
        "overlay": True,
        "tray_icon": True,
    },
    "recording": {
        "sample_rate": 16000,
        "min_duration": 0.5,
    },
}

CONFIG_FILENAME = "config.yaml"


def _deep_merge(base: dict, override: dict) -> dict:
    """Merge override into base recursively."""
    result = copy.deepcopy(base)
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def find_config_path() -> Path | None:
    """Search for config.yaml in current dir, script dir, and user config dir."""
    candidates = [
        Path.cwd() / CONFIG_FILENAME,
        Path(__file__).parent.parent.parent / CONFIG_FILENAME,
        Path(__file__).parent.parent / CONFIG_FILENAME,
        Path.home() / ".config" / "talkrefine" / CONFIG_FILENAME,
    ]
    for p in candidates:
        if p.exists():
            return p
    return None


def load_config(path: str | Path | None = None) -> dict:
    """Load configuration from YAML file, merged with defaults."""
    try:
        import yaml
    except ImportError:
        print("⚠️  PyYAML not installed, using default config")
        return copy.deepcopy(DEFAULTS)

    if path is None:
        path = find_config_path()

    if path is None:
        return copy.deepcopy(DEFAULTS)

    path = Path(path)
    if not path.exists():
        return copy.deepcopy(DEFAULTS)

    with open(path, "r", encoding="utf-8") as f:
        user_config = yaml.safe_load(f) or {}

    config = _deep_merge(DEFAULTS, user_config)
    print(f"📄 配置: {path}")
    return config
