"""Monitor Windows session events (lock/unlock) for resource management."""

import ctypes
import ctypes.wintypes
import threading
import logging

logger = logging.getLogger("talkrefine")

# Windows constants
WM_WTSSESSION_CHANGE = 0x02B1
WTS_SESSION_LOCK = 0x7
WTS_SESSION_UNLOCK = 0x8
NOTIFY_FOR_THIS_SESSION = 0

_on_lock = None
_on_unlock = None


def _create_hidden_window():
    """Create a hidden window to receive session change messages."""
    WNDPROC = ctypes.WINFUNCTYPE(
        ctypes.c_long, ctypes.wintypes.HWND, ctypes.c_uint,
        ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM
    )

    def wnd_proc(hwnd, msg, wparam, lparam):
        if msg == WM_WTSSESSION_CHANGE:
            if wparam == WTS_SESSION_LOCK and _on_lock:
                logger.info("🔒 Session locked — releasing LLM memory")
                try:
                    _on_lock()
                except Exception:
                    logger.exception("Error in lock handler")
            elif wparam == WTS_SESSION_UNLOCK and _on_unlock:
                logger.info("🔓 Session unlocked — warming up LLM")
                try:
                    _on_unlock()
                except Exception:
                    logger.exception("Error in unlock handler")
        return ctypes.windll.user32.DefWindowProcW(hwnd, msg, wparam, lparam)

    wnd_proc_cb = WNDPROC(wnd_proc)

    # Define WNDCLASSW manually (not available in all ctypes.wintypes versions)
    class WNDCLASSW(ctypes.Structure):
        _fields_ = [
            ("style", ctypes.c_uint),
            ("lpfnWndProc", WNDPROC),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", ctypes.wintypes.HINSTANCE),
            ("hIcon", ctypes.wintypes.HICON),
            ("hCursor", ctypes.wintypes.HANDLE),
            ("hbrBackground", ctypes.wintypes.HANDLE),
            ("lpszMenuName", ctypes.wintypes.LPCWSTR),
            ("lpszClassName", ctypes.wintypes.LPCWSTR),
        ]

    wc = WNDCLASSW()
    wc.lpfnWndProc = wnd_proc_cb
    wc.lpszClassName = "TalkRefineSessionMonitor"
    wc.hInstance = ctypes.windll.kernel32.GetModuleHandleW(None)

    atom = ctypes.windll.user32.RegisterClassW(ctypes.byref(wc))
    if not atom:
        logger.error("Failed to register session monitor window class")
        return

    hwnd = ctypes.windll.user32.CreateWindowExW(
        0, wc.lpszClassName, "TalkRefine Session Monitor",
        0, 0, 0, 0, 0, None, None, wc.hInstance, None
    )
    if not hwnd:
        logger.error("Failed to create session monitor window")
        return

    # Register for session notifications
    wtsapi32 = ctypes.windll.wtsapi32
    wtsapi32.WTSRegisterSessionNotification(hwnd, NOTIFY_FOR_THIS_SESSION)

    # Message loop
    msg = ctypes.wintypes.MSG()
    while ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
        ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
        ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))


def start_session_monitor(on_lock=None, on_unlock=None):
    """Start monitoring lock/unlock events in a background thread."""
    global _on_lock, _on_unlock
    _on_lock = on_lock
    _on_unlock = on_unlock
    t = threading.Thread(target=_create_hidden_window, daemon=True)
    t.start()
    logger.info("Session monitor started (lock→unload, unlock→warmup)")
