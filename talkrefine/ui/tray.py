"""System tray icon."""

import threading
import pystray
from PIL import Image, ImageDraw


def _create_icon_image() -> Image.Image:
    size = 64
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle([20, 6, 44, 36], radius=10, fill="#a6e3a1")
    draw.arc([14, 18, 50, 48], start=0, end=180, fill="#cdd6f4", width=3)
    draw.line([32, 48, 32, 58], fill="#cdd6f4", width=3)
    draw.line([22, 58, 42, 58], fill="#cdd6f4", width=3)
    return img


class TrayIcon:
    """System tray icon with context menu."""

    def __init__(self, hotkey: str, on_quit, on_toggle_llm=None):
        self._hotkey = hotkey
        self._on_quit = on_quit
        self._on_toggle_llm = on_toggle_llm
        self._llm_enabled = True
        self._icon = None

    @property
    def llm_enabled(self) -> bool:
        return self._llm_enabled

    @llm_enabled.setter
    def llm_enabled(self, value: bool):
        self._llm_enabled = value

    def start(self):
        """Start tray icon (non-blocking, runs detached)."""
        def quit_action(icon, item):
            icon.stop()
            threading.Thread(target=self._on_quit, daemon=True).start()

        def toggle_llm(icon, item):
            self._llm_enabled = not self._llm_enabled
            if self._on_toggle_llm:
                self._on_toggle_llm(self._llm_enabled)

        menu = pystray.Menu(
            pystray.MenuItem(
                f"Press {self._hotkey.upper()} to record",
                lambda icon, item: None,
                enabled=False,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "LLM Refinement",
                toggle_llm,
                checked=lambda item: self._llm_enabled,
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit", quit_action),
        )

        self._icon = pystray.Icon("talkrefine", _create_icon_image(),
                                   "TalkRefine", menu)
        self._icon.run_detached()

    def stop(self):
        if self._icon:
            self._icon.stop()
