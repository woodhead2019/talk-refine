"""TalkRefine - Local voice input with LLM refinement."""

# Fix stdout/stderr FIRST — before any import that might print/flush.
# pythonw.exe may set them to None OR to a closed file handle.
# Third-party libs (funasr, tqdm, huggingface_hub) crash on print()/flush().
import sys as _sys, os as _os
for _name in ("stdout", "stderr"):
    _s = getattr(_sys, _name, None)
    if _s is None or getattr(_s, "closed", False):
        setattr(_sys, _name, open(_os.devnull, "w", encoding="utf-8"))

__version__ = "0.1.0"

# Validate i18n strings in debug/development
from talkrefine.locale import validate_strings
_i18n_issues = validate_strings()
if _i18n_issues:
    import logging
    _logger = logging.getLogger("talkrefine")
    for _issue in _i18n_issues:
        _logger.warning("i18n: %s", _issue)

# Set DPI awareness at import time (earliest possible)
# Must be before ANY window/UI creation including pystray
import ctypes
try:
    # Windows 10 1703+ : Per Monitor V2 (best quality)
    ctypes.windll.user32.SetProcessDpiAwarenessContext(
        ctypes.c_void_p(-4)  # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
    )
except Exception:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass
