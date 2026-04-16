"""Windows global hotkeys using RegisterHotKey API (reliable, survives lock/unlock)."""

import ctypes
import ctypes.wintypes
import threading
import logging

logger = logging.getLogger("talkrefine")

WM_HOTKEY = 0x0312

_VK_MAP = {
    'f1': 0x70, 'f2': 0x71, 'f3': 0x72, 'f4': 0x73,
    'f5': 0x74, 'f6': 0x75, 'f7': 0x76, 'f8': 0x77,
    'f9': 0x78, 'f10': 0x79, 'f11': 0x7A, 'f12': 0x7B,
    'esc': 0x1B, 'escape': 0x1B,
    'space': 0x20, 'enter': 0x0D, 'tab': 0x09,
    'insert': 0x2D, 'delete': 0x2E, 'home': 0x24, 'end': 0x23,
    'pageup': 0x21, 'pagedown': 0x22,
}

_MOD_MAP = {
    'ctrl': 0x0002, 'control': 0x0002,
    'alt': 0x0001,
    'shift': 0x0004,
    'win': 0x0008,
}

MOD_NOREPEAT = 0x4000


def _parse_key(key_str: str):
    """Parse key string like 'f6' or 'ctrl+shift+a' into (modifiers, vk)."""
    parts = [p.strip().lower() for p in key_str.split('+')]
    modifiers = 0
    vk = 0
    for part in parts:
        if part in _MOD_MAP:
            modifiers |= _MOD_MAP[part]
        elif part in _VK_MAP:
            vk = _VK_MAP[part]
        elif len(part) == 1 and part.isalnum():
            vk = ord(part.upper())
        else:
            logger.warning("Unknown key component: %s", part)
    return modifiers, vk


class KeySuppressor:
    """Low-level keyboard hook that intercepts a key and prevents it from
    reaching other applications.  Used during recording so that ESC only
    cancels recording and is not forwarded to the focused window behind
    the overlay."""

    _WH_KEYBOARD_LL = 13
    _WM_KEYDOWN = 0x0100

    def __init__(self, vk_code: int, callback):
        self._vk = vk_code
        self._callback = callback
        self._hook = None
        self._thread = None
        self._thread_id = None
        self._active = False
        # prevent GC of the C callback
        self._c_proc = ctypes.CFUNCTYPE(
            ctypes.c_long, ctypes.c_int,
            ctypes.wintypes.WPARAM, ctypes.wintypes.LPARAM
        )(self._hook_proc)

    # -- public API -----------------------------------------------------------

    def start(self):
        if self._active:
            return
        self._active = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        if not self._active:
            return
        self._active = False
        if self._thread_id:
            # WM_QUIT = 0x0012
            ctypes.windll.user32.PostThreadMessageW(
                self._thread_id, 0x0012, 0, 0)

    # -- internals ------------------------------------------------------------

    def _hook_proc(self, nCode, wParam, lParam):
        if nCode >= 0 and self._active and wParam == self._WM_KEYDOWN:
            # lParam points to KBDLLHOOKSTRUCT; first DWORD is vkCode
            vk = ctypes.cast(lParam, ctypes.POINTER(ctypes.c_ulong))[0]
            if vk == self._vk:
                try:
                    self._callback()
                except Exception:
                    logger.exception("KeySuppressor callback error")
                return 1  # suppress — do NOT call next hook
        return ctypes.windll.user32.CallNextHookEx(
            self._hook, nCode, wParam, lParam)

    def _run(self):
        user32 = ctypes.windll.user32
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

        self._hook = user32.SetWindowsHookExW(
            self._WH_KEYBOARD_LL, self._c_proc, None, 0)
        if not self._hook:
            logger.error("SetWindowsHookExW failed, error=%d",
                         ctypes.GetLastError())
            self._active = False
            return

        msg = ctypes.wintypes.MSG()
        while self._active:
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret <= 0:
                break

        user32.UnhookWindowsHookEx(self._hook)
        self._hook = None
        self._thread_id = None


class HotkeyManager:
    """Manages global hotkeys via Win32 RegisterHotKey API."""

    def __init__(self):
        self._callbacks = {}
        self._next_id = 1
        self._thread = None
        self._thread_id = None
        self._registrations = []  # (id, modifiers, vk, callback)
        self._lock = threading.Lock()
        self._ready = threading.Event()

    def register(self, key: str, callback):
        """Register a global hotkey. Must be called before start()."""
        modifiers, vk = _parse_key(key)
        if vk == 0:
            logger.error("Cannot parse hotkey: %s", key)
            return

        with self._lock:
            hid = self._next_id
            self._next_id += 1
            self._registrations.append((hid, modifiers, vk, callback))

        logger.info("Hotkey queued: %s (id=%d)", key, hid)

    def start(self):
        """Start the hotkey listener thread. Call after all register() calls."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=5)

    def unregister_all(self):
        """Unregister all hotkeys (must be called from the listener thread)."""
        if self._thread_id is None:
            return
        user32 = ctypes.windll.user32
        for hid in list(self._callbacks):
            user32.UnregisterHotKey(None, hid)
        self._registrations.clear()
        self._callbacks.clear()

    def _run(self):
        """Message loop thread — registers hotkeys and processes WM_HOTKEY."""
        user32 = ctypes.windll.user32
        self._thread_id = ctypes.windll.kernel32.GetCurrentThreadId()

        with self._lock:
            for hid, mods, vk, cb in self._registrations:
                result = user32.RegisterHotKey(None, hid, mods | MOD_NOREPEAT, vk)
                if result:
                    self._callbacks[hid] = cb
                    logger.info("Hotkey id=%d registered OK", hid)
                else:
                    err = ctypes.GetLastError()
                    logger.error("RegisterHotKey failed for id=%d, error=%d", hid, err)

        self._ready.set()

        msg = ctypes.wintypes.MSG()
        while True:
            ret = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if ret <= 0:
                break
            if msg.message == WM_HOTKEY:
                hid = msg.wParam
                cb = self._callbacks.get(hid)
                if cb:
                    try:
                        cb()
                    except Exception:
                        logger.exception("Hotkey callback error (id=%d)", hid)
