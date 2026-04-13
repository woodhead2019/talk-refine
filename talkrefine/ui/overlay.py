"""Floating volume overlay window with rounded corners and gradient bar."""

import tkinter as tk
import math

# Overlay strings by language
_OVERLAY_STRINGS = {
    "zh": {
        "recording": "🎤 录音中... {hotkey}=完成  {cancel}=取消",
        "recognizing": "⏳ 识别中...",
        "refining": "✍️ 润色中...",
        "cancelled": "🚫 已取消",
        "no_audio": "⚠️ 未检测到音频",
        "too_short": "⚠️ 录音太短",
        "no_speech": "⚠️ 未识别到内容",
        "error": "❌ 出错",
        "ready": "🟢 按 {hotkey} 开始录音",
        "loading": "⏳ 加载模型中...",
        "pasted": "📋 已粘贴",
        "copied": "📋 已复制",
    },
    "en": {
        "recording": "🎤 Recording... {hotkey}=done  {cancel}=cancel",
        "recognizing": "⏳ Recognizing...",
        "refining": "✍️ Refining...",
        "cancelled": "🚫 Cancelled",
        "no_audio": "⚠️ No audio detected",
        "too_short": "⚠️ Too short",
        "no_speech": "⚠️ No speech detected",
        "error": "❌ Error",
        "ready": "🟢 Press {hotkey} to record",
        "loading": "⏳ Loading model...",
        "pasted": "📋 Pasted",
        "copied": "📋 Copied",
    },
}

# AI gradient colors: purple → blue → cyan → orange → red
_GRADIENT_COLORS = [
    (138, 43, 226),   # purple
    (88, 101, 242),   # blue
    (6, 182, 212),    # cyan
    (245, 158, 11),   # orange
    (239, 68, 68),    # red
]


def get_overlay_strings(lang: str = "zh") -> dict:
    return _OVERLAY_STRINGS.get(lang, _OVERLAY_STRINGS["en"])


def _interpolate_color(colors, t):
    """Interpolate between gradient colors. t in [0, 1]."""
    t = max(0, min(1, t))
    n = len(colors) - 1
    idx = t * n
    i = int(idx)
    if i >= n:
        return f"#{colors[-1][0]:02x}{colors[-1][1]:02x}{colors[-1][2]:02x}"
    frac = idx - i
    r = int(colors[i][0] + (colors[i+1][0] - colors[i][0]) * frac)
    g = int(colors[i][1] + (colors[i+1][1] - colors[i][1]) * frac)
    b = int(colors[i][2] + (colors[i+1][2] - colors[i][2]) * frac)
    return f"#{r:02x}{g:02x}{b:02x}"


def _round_rect(canvas, x1, y1, x2, y2, radius, **kwargs):
    """Draw a rounded rectangle on canvas."""
    r = radius
    canvas.create_arc(x1, y1, x1+2*r, y1+2*r, start=90, extent=90,
                      style="pieslice", outline="", **kwargs)
    canvas.create_arc(x2-2*r, y1, x2, y1+2*r, start=0, extent=90,
                      style="pieslice", outline="", **kwargs)
    canvas.create_arc(x2-2*r, y2-2*r, x2, y2, start=270, extent=90,
                      style="pieslice", outline="", **kwargs)
    canvas.create_arc(x1, y2-2*r, x1+2*r, y2, start=180, extent=90,
                      style="pieslice", outline="", **kwargs)
    canvas.create_rectangle(x1+r, y1, x2-r, y2, outline="", **kwargs)
    canvas.create_rectangle(x1, y1+r, x2, y2-r, outline="", **kwargs)


class VolumeOverlay:
    """Semi-transparent floating window with rounded corners and AI gradient bar."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TalkRefine")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.9)
        # Transparent background for rounded corners
        self.root.attributes("-transparentcolor", "#010101")

        self.width = 420
        self.height = 70
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - self.width) // 2
        y = screen_h - self.height - 100
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.root.configure(bg="#010101")

        try:
            from pathlib import Path
            ico_path = Path(__file__).parent.parent / "assets" / "talkrefine.ico"
            if not ico_path.exists():
                ico_path = Path(__file__).parent.parent.parent / "assets" / "talkrefine.ico"
            if ico_path.exists():
                self.root.iconbitmap(str(ico_path))
        except Exception:
            pass

        # Main canvas for rounded background
        self.bg_canvas = tk.Canvas(
            self.root, width=self.width, height=self.height,
            bg="#010101", highlightthickness=0
        )
        self.bg_canvas.pack(fill="both", expand=True)

        # Draw rounded background
        _round_rect(self.bg_canvas, 2, 2, self.width-2, self.height-2,
                     radius=16, fill="#1e1e2e")

        # Status text
        self.status_label = self.bg_canvas.create_text(
            self.width // 2, 22,
            text="TalkRefine", font=("Microsoft YaHei UI", 10),
            fill="#cdd6f4"
        )

        # Volume bar background (rounded)
        bar_x = 20
        bar_y = 40
        self.bar_w = self.width - 40
        self.bar_h = 14
        _round_rect(self.bg_canvas, bar_x, bar_y,
                     bar_x + self.bar_w, bar_y + self.bar_h,
                     radius=7, fill="#313244")

        # Gradient bar segments (pre-create for performance)
        self._bar_x = bar_x
        self._bar_y = bar_y
        self._bar_segments = []
        seg_count = 50  # number of gradient segments
        seg_w = self.bar_w / seg_count
        for i in range(seg_count):
            t = i / (seg_count - 1)
            color = _interpolate_color(_GRADIENT_COLORS, t)
            sx = bar_x + i * seg_w
            seg = self.bg_canvas.create_rectangle(
                sx, bar_y + 1, sx + seg_w + 1, bar_y + self.bar_h - 1,
                fill=color, outline="", state="hidden"
            )
            self._bar_segments.append(seg)

        self._volume_ref = 0.0
        self._recording_ref = False
        self.root.withdraw()
        self._update_loop()

    def show(self, text: str = "🎤 录音中..."):
        self.set_status(text, "#a6e3a1")
        self.root.deiconify()

    def hide(self):
        self.root.withdraw()

    def set_status(self, text: str, color: str = "#cdd6f4"):
        self.bg_canvas.itemconfig(self.status_label, text=text, fill=color)

    def update_volume(self, volume: float, is_recording: bool):
        self._volume_ref = volume
        self._recording_ref = is_recording

    def schedule_hide(self, delay_ms: int = 3000):
        self.root.after(delay_ms, self.hide)

    def _update_loop(self):
        if self._recording_ref:
            vol = self._volume_ref
            active_count = int(vol * len(self._bar_segments))
            for i, seg in enumerate(self._bar_segments):
                if i < active_count:
                    self.bg_canvas.itemconfig(seg, state="normal")
                else:
                    self.bg_canvas.itemconfig(seg, state="hidden")
        else:
            for seg in self._bar_segments:
                self.bg_canvas.itemconfig(seg, state="hidden")
        self.root.after(50, self._update_loop)

    def run(self):
        self.root.mainloop()
