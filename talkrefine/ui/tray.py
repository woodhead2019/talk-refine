"""System tray icon with custom popup menu."""

import threading
import tkinter as tk
import pystray
from PIL import Image, ImageDraw
from talkrefine.ui.icon import create_app_icon

from talkrefine.history import load_recent

_MENU_FONT = ("Microsoft YaHei UI", 10)
_MENU_FONT_SMALL = ("Microsoft YaHei UI", 9)

_TRAY_STRINGS = {
    "zh": {
        "recent": "── 最近记录 ──",
        "history": "📜 历史记录",
        "settings": "⚙️ 设置",
        "quit": "退出",
    },
    "en": {
        "recent": "── Recent ──",
        "history": "📜 History",
        "settings": "⚙️ Settings",
        "quit": "Quit",
    },
}


def _create_icon_image() -> Image.Image:
    size = 128
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([40, 12, 88, 72], radius=20, fill="#a6e3a1")
    draw.arc([28, 36, 100, 96], start=0, end=180, fill="#cdd6f4", width=5)
    draw.line([64, 96, 64, 116], fill="#cdd6f4", width=5)
    draw.line([44, 116, 84, 116], fill="#cdd6f4", width=5)
    return img


def _truncate(text: str, max_len: int = 18) -> str:
    text = text.replace("\n", " ")
    return text[:max_len] + "..." if len(text) > max_len else text


def _copy_to_clipboard(text: str):
    try:
        import pyperclip
        pyperclip.copy(text)
    except Exception:
        pass


class TrayIcon:
    """System tray icon.
    - Left click (default action) → open settings
    - Right click → custom popup menu (history, settings, quit)
    """

    def __init__(self, hotkey: str, on_quit, on_toggle_llm=None,
                 on_open_settings=None, on_open_history=None,
                 tk_root=None, ui_language: str = "zh"):
        self._hotkey = hotkey
        self._on_quit = on_quit
        self._on_toggle_llm = on_toggle_llm
        self._on_open_settings = on_open_settings
        self._on_open_history = on_open_history
        self._llm_enabled = True
        self._icon = None
        self._tk_root = tk_root
        self._s = _TRAY_STRINGS.get(ui_language, _TRAY_STRINGS["zh"])

    @property
    def llm_enabled(self) -> bool:
        return self._llm_enabled

    @llm_enabled.setter
    def llm_enabled(self, value: bool):
        self._llm_enabled = value

    # ── Left click: open settings ──

    def _on_left_click(self, icon, item=None):
        if self._tk_root and self._on_open_settings:
            self._tk_root.after(0, self._on_open_settings)

    # ── Right click: popup menu ──

    def _on_right_click(self, icon, item=None):
        if self._tk_root is None:
            return
        self._tk_root.after(0, self._show_popup)

    def _show_popup(self):
        menu = tk.Menu(self._tk_root, tearoff=0, font=_MENU_FONT,
                       bg="#ffffff", fg="#1e1e2e", activebackground="#e0e0e0",
                       activeforeground="#1e1e2e", relief="flat", bd=1)

        # Recent history
        history = load_recent(5)
        if history:
            menu.add_command(label=self._s["recent"], state="disabled",
                           font=_MENU_FONT_SMALL)
            for entry in history:
                refined = entry.get("refined", "")
                label = _truncate(refined)
                menu.add_command(label=f"  {label}",
                               command=lambda t=refined: _copy_to_clipboard(t),
                               font=_MENU_FONT)
            menu.add_separator()

        menu.add_command(label=f"  {self._s['history']}", command=self._open_history,
                        font=_MENU_FONT)
        menu.add_command(label=f"  {self._s['settings']}", command=self._open_settings,
                        font=_MENU_FONT)
        menu.add_separator()
        menu.add_command(label=f"  {self._s['quit']}", command=self._quit, font=_MENU_FONT)

        # Position near cursor
        try:
            x = self._tk_root.winfo_pointerx()
            y = self._tk_root.winfo_pointery()
        except Exception:
            x, y = 0, 0

        # tk_popup auto-closes when clicking outside
        menu.tk_popup(x, y - 10)

    def _open_settings(self):
        if self._on_open_settings:
            self._on_open_settings()

    def _open_history(self):
        if self._on_open_history:
            self._on_open_history()

    def _quit(self):
        if self._icon:
            self._icon.stop()
        threading.Thread(target=self._on_quit, daemon=True).start()

    def refresh_menu(self):
        pass

    def start(self):
        """Start tray icon."""
        # pystray menu: default item = left click → settings
        # Right-click shows native menu with "退出" as fallback
        # But we also intercept right-click via Windows message hook
        menu = pystray.Menu(
            # Default (left-click / double-click) → open settings
            pystray.MenuItem("设置", self._on_left_click, default=True, visible=False),
            # Right-click native fallback
            pystray.MenuItem("📜 历史记录",
                           lambda icon, item: self._tk_root.after(0, self._open_history) if self._tk_root else None),
            pystray.MenuItem("⚙️ 设置",
                           lambda icon, item: self._tk_root.after(0, self._open_settings) if self._tk_root else None),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("退出", lambda icon, item: self._quit()),
        )

        self._icon = pystray.Icon("talkrefine", create_app_icon(128),
                                   "TalkRefine", menu)
        self._icon.run_detached()

    def stop(self):
        if self._icon:
            self._icon.stop()
