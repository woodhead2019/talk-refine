"""TalkRefine - Local voice input with LLM refinement."""

__version__ = "0.1.0"

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
