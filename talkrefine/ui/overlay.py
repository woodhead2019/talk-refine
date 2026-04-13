"""Floating volume overlay window."""

import tkinter as tk

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


def get_overlay_strings(lang: str = "zh") -> dict:
    return _OVERLAY_STRINGS.get(lang, _OVERLAY_STRINGS["en"])


class VolumeOverlay:
    """Semi-transparent floating window showing recording status and volume."""

    def __init__(self):
        self.root = tk.Tk()
        self.root.title("TalkRefine")
        self.root.attributes("-topmost", True)
        self.root.overrideredirect(True)
        self.root.attributes("-alpha", 0.85)

        self.width = 320
        self.height = 60
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        x = (screen_w - self.width) // 2
        y = screen_h - self.height - 100
        self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        self.root.configure(bg="#1e1e2e")

        self.status_label = tk.Label(
            self.root, text="TalkRefine", font=("Microsoft YaHei UI", 11),
            fg="#cdd6f4", bg="#1e1e2e"
        )
        self.status_label.pack(pady=(6, 2))

        self.canvas = tk.Canvas(
            self.root, width=self.width - 20, height=14,
            bg="#313244", highlightthickness=0
        )
        self.canvas.pack(pady=(0, 6))
        self._volume_bar = self.canvas.create_rectangle(
            0, 0, 0, 14, fill="#a6e3a1", outline=""
        )

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
        self.status_label.config(text=text, fg=color)

    def update_volume(self, volume: float, is_recording: bool):
        self._volume_ref = volume
        self._recording_ref = is_recording

    def schedule_hide(self, delay_ms: int = 3000):
        self.root.after(delay_ms, self.hide)

    def _update_loop(self):
        if self._recording_ref:
            bar_width = int(self._volume_ref * (self.width - 20))
            bar_width = min(bar_width, self.width - 20)
            if self._volume_ref < 0.3:
                color = "#a6e3a1"
            elif self._volume_ref < 0.7:
                color = "#f9e2af"
            else:
                color = "#f38ba8"
            self.canvas.coords(self._volume_bar, 0, 0, bar_width, 14)
            self.canvas.itemconfig(self._volume_bar, fill=color)
        else:
            self.canvas.coords(self._volume_bar, 0, 0, 0, 14)
        self.root.after(50, self._update_loop)

    def run(self):
        self.root.mainloop()
