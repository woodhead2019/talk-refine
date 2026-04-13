"""System tray icon."""

import threading
import pystray
from PIL import Image, ImageDraw

from talkrefine.history import load_recent


def _create_icon_image() -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([20, 6, 44, 36], radius=10, fill="#a6e3a1")
    draw.arc([14, 18, 50, 48], start=0, end=180, fill="#cdd6f4", width=3)
    draw.line([32, 48, 32, 58], fill="#cdd6f4", width=3)
    draw.line([22, 58, 42, 58], fill="#cdd6f4", width=3)
    return img


def _truncate(text: str, max_len: int = 30) -> str:
    """Truncate text and append ellipsis if needed."""
    text = text.replace("\n", " ")
    if len(text) > max_len:
        return text[:max_len] + "..."
    return text


def _copy_to_clipboard(text: str):
    """Copy text to the system clipboard."""
    try:
        import pyperclip
        pyperclip.copy(text)
    except Exception:
        pass


class TrayIcon:
    """System tray icon with context menu."""

    def __init__(self, hotkey: str, on_quit, on_toggle_llm=None,
                 on_open_settings=None, on_open_history=None):
        self._hotkey = hotkey
        self._on_quit = on_quit
        self._on_toggle_llm = on_toggle_llm
        self._on_open_settings = on_open_settings
        self._on_open_history = on_open_history
        self._llm_enabled = True
        self._icon = None

    @property
    def llm_enabled(self) -> bool:
        return self._llm_enabled

    @llm_enabled.setter
    def llm_enabled(self, value: bool):
        self._llm_enabled = value

    def _build_menu(self) -> pystray.Menu:
        """Build the tray context menu with recent history entries."""
        def quit_action(icon, item):
            icon.stop()
            threading.Thread(target=self._on_quit, daemon=True).start()

        def toggle_llm(icon, item):
            self._llm_enabled = not self._llm_enabled
            if self._on_toggle_llm:
                self._on_toggle_llm(self._llm_enabled)

        def open_settings(icon, item):
            if self._on_open_settings:
                self._on_open_settings()

        def open_history(icon, item):
            if self._on_open_history:
                self._on_open_history()

        # Recent history items
        history = load_recent()

        items = []

        if history:
            items.append(pystray.MenuItem(
                "── 最近记录 ──",
                lambda icon, item: None,
                enabled=False,
            ))
            for entry in history:
                refined = entry.get("refined") or entry.get("text", "")
                label = _truncate(refined)

                def make_copy_action(text):
                    return lambda icon, item: _copy_to_clipboard(text)

                items.append(pystray.MenuItem(
                    label,
                    make_copy_action(refined),
                ))
            items.append(pystray.Menu.SEPARATOR)

        items.extend([
            pystray.MenuItem(
                f"按 {self._hotkey.upper()} 录音",
                lambda icon, item: None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "LLM 润色",
                toggle_llm,
                checked=lambda item: self._llm_enabled,
            ),
            pystray.MenuItem("📜 历史记录", open_history),
            pystray.MenuItem("⚙️ 设置", open_settings),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", quit_action),
        ])

        return pystray.Menu(*items)

    def refresh_menu(self):
        """Rebuild the menu with fresh history data."""
        if self._icon:
            self._icon.menu = self._build_menu()
            self._icon.update_menu()

    def start(self):
        """Start tray icon (non-blocking, runs detached)."""
        self._icon = pystray.Icon("talkrefine", _create_icon_image(),
                                   "TalkRefine", self._build_menu())
        self._icon.run_detached()

    def stop(self):
        if self._icon:
            self._icon.stop()
