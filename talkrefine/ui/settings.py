"""Settings GUI and History viewer windows for TalkRefine."""

# ── DPI awareness (must be before any tkinter imports) ──
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)  # Per-monitor DPI aware
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

import tkinter as tk
from tkinter import ttk, messagebox
import subprocess
import os
import urllib.request
import urllib.error
import json
from pathlib import Path

_FONT = ("Microsoft YaHei UI", 10)
_FONT_BOLD = ("Microsoft YaHei UI", 10, "bold")
_FONT_SMALL = ("Microsoft YaHei UI", 9)
_FONT_HEADING = ("Microsoft YaHei UI", 11, "bold")

# ── Localisation strings ──

_STRINGS = {
    "zh": {
        "settings_title": "TalkRefine 设置",
        "tab_general": "通用",
        "tab_asr": "语音识别",
        "tab_llm": "LLM 润色",
        "tab_output": "输出",
        "ui_language": "界面语言",
        "autostart": "开机自动启动",
        "record_hotkey": "录音快捷键",
        "cancel_key": "取消快捷键",
        "recognition_lang": "识别语言",
        "asr_model": "识别模型",
        "device": "运行设备",
        "enable_llm": "启用 LLM 润色",
        "provider": "提供者",
        "endpoint": "服务端点",
        "detect": "检测",
        "model": "模型",
        "refresh": "刷新",
        "api_key": "API Key",
        "prompt": "提示词",
        "prompt_presets": "预设模板",
        "general_preset": "通用",
        "meeting_preset": "会议",
        "code_preset": "代码",
        "temperature": "Temperature",
        "auto_paste": "自动粘贴到光标",
        "preserve_clipboard": "粘贴后恢复剪贴板",
        "save": "💾 保存",
        "cancel": "取消",
        "auto_detect": "自动",
        "chinese": "中文",
        "hotkey_conflict": "⚠️ 此快捷键可能与输入法冲突",
        "save_success": "保存成功",
        "save_msg": "配置已生效。ASR 模型更改需要重启。",
        "history_title": "TalkRefine 历史记录",
        "time_col": "时间",
        "duration_col": "时长",
        "raw_col": "原始转写",
        "refined_col": "润色结果",
        "copy_refined": "📋 复制润色结果",
        "copy_raw": "📋 复制原始转写",
        "clear_history": "🗑️ 清空",
        "clear_confirm": "确定要清空所有历史记录吗？",
        "confirm": "确认",
        "detail": "详情",
        "recommended_cn": "推荐中文",
        "endpoint_ok": "✅ 连接成功",
        "endpoint_fail": "❌ 连接失败",
        "search": "搜索...",
        "select_first": "请先选择一条记录",
        "copied": "已复制",
        "lang_change_note": "语言变更将在重新打开设置窗口后生效。",
    },
    "en": {
        "settings_title": "TalkRefine Settings",
        "tab_general": "General",
        "tab_asr": "Speech Recognition",
        "tab_llm": "LLM Refinement",
        "tab_output": "Output",
        "ui_language": "UI Language",
        "autostart": "Start on system boot",
        "record_hotkey": "Record Hotkey",
        "cancel_key": "Cancel Key",
        "recognition_lang": "Recognition Language",
        "asr_model": "Recognition Model",
        "device": "Device",
        "enable_llm": "Enable LLM Refinement",
        "provider": "Provider",
        "endpoint": "Endpoint",
        "detect": "Detect",
        "model": "Model",
        "refresh": "Refresh",
        "api_key": "API Key",
        "prompt": "Prompt",
        "prompt_presets": "Presets",
        "general_preset": "General",
        "meeting_preset": "Meeting",
        "code_preset": "Code",
        "temperature": "Temperature",
        "auto_paste": "Auto-paste at cursor",
        "preserve_clipboard": "Restore clipboard after paste",
        "save": "💾 Save",
        "cancel": "Cancel",
        "auto_detect": "Auto",
        "chinese": "Chinese",
        "hotkey_conflict": "⚠️ May conflict with input method",
        "save_success": "Saved",
        "save_msg": "Config applied. ASR model changes require restart.",
        "history_title": "TalkRefine History",
        "time_col": "Time",
        "duration_col": "Duration",
        "raw_col": "Raw Text",
        "refined_col": "Refined Text",
        "copy_refined": "📋 Copy Refined",
        "copy_raw": "📋 Copy Raw",
        "clear_history": "🗑️ Clear All",
        "clear_confirm": "Clear all history?",
        "confirm": "Confirm",
        "detail": "Detail",
        "recommended_cn": "Best for Chinese",
        "endpoint_ok": "✅ Connected",
        "endpoint_fail": "❌ Failed",
        "search": "Search...",
        "select_first": "Please select an entry first",
        "copied": "Copied",
        "lang_change_note": "Language change takes effect after reopening settings.",
    },
}

# ── ASR model options (combined engine + model) ──

_ASR_OPTIONS = [
    ("sensevoice", "FunAudioLLM/SenseVoiceSmall", "SenseVoice - FunAudioLLM/SenseVoiceSmall"),
    ("whisper", "tiny", "Whisper - tiny"),
    ("whisper", "base", "Whisper - base"),
    ("whisper", "small", "Whisper - small"),
    ("whisper", "medium", "Whisper - medium"),
    ("whisper", "large-v3", "Whisper - large-v3"),
]


def _check_asr_availability() -> dict[str, bool]:
    """Check which ASR engines are installed."""
    available = {}
    try:
        import funasr  # noqa: F401
        available["sensevoice"] = True
    except ImportError:
        available["sensevoice"] = False
    try:
        import whisper  # noqa: F401
        available["whisper"] = True
    except ImportError:
        available["whisper"] = False
    return available


_ASR_INSTALL_HINT = {
    "sensevoice": "pip install funasr modelscope",
    "whisper": "pip install openai-whisper",
}

# ── Prompt loading ──

def _load_default_prompt() -> str:
    """Load the default prompt from prompts/default.txt."""
    prompt_path = Path(__file__).parent.parent.parent / "prompts" / "default.txt"
    if prompt_path.exists():
        return prompt_path.read_text(encoding="utf-8")
    return (
        "清理以下语音识别文本。删除语气词和重复内容，保持原始用词，"
        "多个要点用分点列出。只输出结果。\n\n原始文本：{text}"
    )


# ── Utility functions ──

def detect_devices() -> list[str]:
    """Return available compute devices."""
    devices = ["cpu"]
    try:
        import torch
        if torch.cuda.is_available():
            devices.append("cuda")
        if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            devices.append("mps")
    except Exception:
        pass
    return devices


def is_autostart_enabled() -> bool:
    """Check if TalkRefine is in Windows startup folder."""
    shortcut = os.path.join(
        os.environ.get("APPDATA", ""),
        r"Microsoft\Windows\Start Menu\Programs\Startup",
        "TalkRefine.lnk"
    )
    return os.path.exists(shortcut)


def discover_ollama_models() -> list[str]:
    """Run ``ollama list`` and return model names."""
    try:
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True, text=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        if result.returncode != 0:
            return []
        lines = result.stdout.strip().splitlines()
        models: list[str] = []
        for line in lines[1:]:
            parts = line.split()
            if parts:
                models.append(parts[0])
        return models
    except Exception:
        return []


def _probe_endpoint(url: str) -> bool:
    """Check whether *url* responds with HTTP 200."""
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def _load_prompt_from_config(config: dict) -> str:
    """Return prompt text from config, falling back to presets / file."""
    llm = config.get("llm", {})
    # Inline text takes precedence
    if llm.get("prompt_text"):
        return llm["prompt_text"]
    # Load from prompts/default.txt
    try:
        from talkrefine.llm.prompts import load_prompt
        name_or_path = llm.get("prompt", "default")
        return load_prompt(name_or_path)
    except Exception:
        return _load_default_prompt()


# ────────────────────────────────────────────────────────────
# Settings Window
# ────────────────────────────────────────────────────────────

class SettingsWindow:
    """Tab-based configuration settings window with i18n support."""

    def __init__(self, config: dict, on_save=None):
        self.config = config
        self.on_save = on_save
        self.win = None

        lang = config.get("ui_language", "zh")
        if lang not in _STRINGS:
            lang = "zh"
        self.s = _STRINGS[lang]

    def show(self):
        if self.win and self.win.winfo_exists():
            self.win.lift()
            return

        self.win = tk.Toplevel()
        self.win.title(self.s["settings_title"])
        self.win.geometry("950x850")
        self.win.attributes("-topmost", True)
        self.win.resizable(True, True)
        self.win.minsize(900, 800)
        # Set window icon
        try:
            ico_path = Path(__file__).parent.parent.parent / "assets" / "talkrefine.ico"
            if ico_path.exists():
                self.win.iconbitmap(str(ico_path))
        except Exception:
            pass

        style = ttk.Style(self.win)
        style.configure("TNotebook.Tab", font=_FONT, padding=[14, 5])
        style.configure("TLabelframe.Label", font=_FONT_BOLD)
        style.configure("TLabel", font=_FONT)
        style.configure("TCheckbutton", font=_FONT)
        style.configure("TRadiobutton", font=_FONT)
        style.configure("TButton", font=_FONT)

        notebook = ttk.Notebook(self.win)
        notebook.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        self._build_general_tab(notebook)
        self._build_asr_tab(notebook)
        self._build_llm_tab(notebook)
        self._build_output_tab(notebook)

        # Auto-load Ollama models on startup
        self.win.after(500, self._refresh_ollama_models)

        # Bottom buttons
        btn_frame = ttk.Frame(self.win)
        btn_frame.pack(fill="x", padx=10, pady=12)
        ttk.Button(btn_frame, text=self.s["save"], width=12,
                   command=self._save).pack(side="right", padx=(5, 0))
        ttk.Button(btn_frame, text=self.s["cancel"], width=10,
                   command=self.win.destroy).pack(side="right")

    # ────────────── Tab 1: General ──────────────

    def _build_general_tab(self, notebook: ttk.Notebook):
        tab = ttk.Frame(notebook, padding=12)
        notebook.add(tab, text=self.s["tab_general"])

        # UI language
        lang_frame = ttk.LabelFrame(tab, text=f"🌐 {self.s['ui_language']}", padding=10)
        lang_frame.pack(fill="x", pady=(0, 10))
        lang_frame.columnconfigure(1, weight=1)

        ttk.Label(lang_frame, text=self.s["ui_language"] + ":").grid(
            row=0, column=0, sticky="w", padx=8, pady=4)
        self.ui_lang_var = tk.StringVar(
            value="中文" if self.config.get("ui_language", "zh") == "zh" else "English")
        ui_lang_combo = ttk.Combobox(
            lang_frame, textvariable=self.ui_lang_var,
            values=["中文", "English"], width=14, state="readonly", font=_FONT)
        ui_lang_combo.grid(row=0, column=1, sticky="w", padx=8, pady=4)
        self.ui_lang_note = ttk.Label(lang_frame, text="", foreground="gray")
        self.ui_lang_note.grid(row=1, column=0, columnspan=2, sticky="w", padx=8)
        # Language change takes effect after save & restart

        # Hotkeys
        hk_frame = ttk.LabelFrame(tab, text=f"⌨️ {self.s['record_hotkey']}", padding=10)
        hk_frame.pack(fill="x", pady=(0, 10))
        hk_frame.columnconfigure(1, weight=1)

        ttk.Label(hk_frame, text=self.s["record_hotkey"] + ":").grid(
            row=0, column=0, sticky="w", padx=8, pady=4)
        self.hotkey_var = tk.StringVar(value=self.config.get("hotkey", "f7"))
        hotkey_entry = ttk.Entry(hk_frame, textvariable=self.hotkey_var,
                                 width=20, font=_FONT)
        hotkey_entry.grid(row=0, column=1, sticky="w", padx=8, pady=4)
        self.hotkey_warn = ttk.Label(hk_frame, text="", foreground="#cc6600")
        self.hotkey_warn.grid(row=0, column=2, sticky="w", padx=4, pady=4)
        self.hotkey_var.trace_add("write", self._check_hotkey_conflict)

        ttk.Label(hk_frame, text=self.s["cancel_key"] + ":").grid(
            row=1, column=0, sticky="w", padx=8, pady=4)
        self.cancel_var = tk.StringVar(value=self.config.get("cancel_key", "esc"))
        ttk.Entry(hk_frame, textvariable=self.cancel_var, width=20, font=_FONT).grid(
            row=1, column=1, sticky="w", padx=8, pady=4)

        # Recognition language
        rec_frame = ttk.LabelFrame(
            tab, text=f"🌍 {self.s['recognition_lang']}", padding=10)
        rec_frame.pack(fill="x", pady=(0, 10))

        self.lang_var = tk.StringVar(value=self.config.get("language", "auto"))
        lang_inner = ttk.Frame(rec_frame)
        lang_inner.pack(fill="x")
        for code, label in [("auto", self.s["auto_detect"]),
                            ("zh", "中文"),
                            ("en", "English"),
                            ("ja", "日本語"),
                            ("ko", "한국어")]:
            ttk.Radiobutton(lang_inner, text=label, variable=self.lang_var,
                            value=code).pack(side="left", padx=6)

        self._check_hotkey_conflict()

        # ── Autostart ──
        self.autostart_var = tk.BooleanVar(value=is_autostart_enabled())
        ttk.Checkbutton(tab, text=self.s["autostart"],
                        variable=self.autostart_var, style="TCheckbutton").pack(
            anchor="w", padx=12, pady=(8, 0))

    def _on_ui_lang_change(self, _event=None):
        self.ui_lang_note.configure(text=self.s["lang_change_note"])

    def _check_hotkey_conflict(self, *_args):
        key = self.hotkey_var.get().strip().lower()
        if key in ("ctrl+space", "ctrl + space"):
            self.hotkey_warn.configure(text=self.s["hotkey_conflict"])
        else:
            self.hotkey_warn.configure(text="")

    # ────────────── Tab 2: ASR ──────────────

    def _build_asr_tab(self, notebook: ttk.Notebook):
        tab = ttk.Frame(notebook, padding=12)
        notebook.add(tab, text=self.s["tab_asr"])

        asr = self.config.get("asr", {})
        cur_engine = asr.get("engine", "sensevoice")
        cur_model = asr.get("model", "FunAudioLLM/SenseVoiceSmall")

        # Check which engines are installed
        avail = _check_asr_availability()

        # Only show installed models in dropdown
        display_values: list[str] = []
        current_display = ""
        for engine, model, label in _ASR_OPTIONS:
            if not avail.get(engine, False):
                continue
            disp = label
            if engine == "sensevoice":
                disp += f" ({self.s['recommended_cn']})"
            display_values.append(disp)
            if engine == cur_engine and model == cur_model:
                current_display = disp
        if not current_display and display_values:
            current_display = display_values[0]

        # ── Installed models ──
        frame = ttk.LabelFrame(
            tab, text=f"🎙️ {self.s['asr_model']}", padding=10)
        frame.pack(fill="x", pady=(0, 10))
        frame.columnconfigure(1, weight=1)

        ttk.Label(frame, text=self.s["asr_model"] + ":").grid(
            row=0, column=0, sticky="w", padx=8, pady=4)
        self.asr_combo_var = tk.StringVar(value=current_display)
        self.asr_combo = ttk.Combobox(frame, textvariable=self.asr_combo_var,
                     values=display_values, width=42,
                     state="readonly", font=_FONT)
        self.asr_combo.grid(row=0, column=1, sticky="w", padx=8, pady=4)

        # Device
        devices = detect_devices()
        cur_device = asr.get("device", "cpu")
        if cur_device not in devices:
            cur_device = devices[0]

        ttk.Label(frame, text=self.s["device"] + ":").grid(
            row=1, column=0, sticky="w", padx=8, pady=4)
        self.asr_device_var = tk.StringVar(value=cur_device)
        state = "readonly" if len(devices) > 1 else "disabled"
        ttk.Combobox(frame, textvariable=self.asr_device_var,
                     values=devices, width=14, state=state, font=_FONT).grid(
            row=1, column=1, sticky="w", padx=8, pady=4)

        # ── Install more engines section ──
        not_installed = [e for e in ("sensevoice", "whisper") if not avail.get(e, False)]
        if not_installed:
            install_frame = ttk.LabelFrame(
                tab, text="📦 " + ("安装更多引擎" if self.s == _STRINGS["zh"] else "Install More Engines"),
                padding=10)
            install_frame.pack(fill="x", pady=(5, 0))

            for engine in not_installed:
                row_frame = ttk.Frame(install_frame)
                row_frame.pack(fill="x", pady=2)

                name = "SenseVoice (FunASR)" if engine == "sensevoice" else "Whisper (OpenAI)"
                cmd = _ASR_INSTALL_HINT[engine]

                ttk.Label(row_frame, text=f"  {name}:", font=_FONT).pack(side="left")
                cmd_entry = ttk.Entry(row_frame, font=_FONT_SMALL, width=35)
                cmd_entry.insert(0, cmd)
                cmd_entry.configure(state="readonly")
                cmd_entry.pack(side="left", padx=6)

                def make_copy(text, entry):
                    def _copy():
                        tab.clipboard_clear()
                        tab.clipboard_append(text)
                        entry.configure(state="normal")
                        entry.delete(0, "end")
                        entry.insert(0, "✅ Copied!")
                        entry.configure(state="readonly")
                        tab.after(1500, lambda: (
                            entry.configure(state="normal"),
                            entry.delete(0, "end"),
                            entry.insert(0, text),
                            entry.configure(state="readonly"),
                        ))
                    return _copy

                ttk.Button(row_frame, text="📋",  width=3,
                          command=make_copy(cmd, cmd_entry)).pack(side="left")

    def _parse_asr_selection(self) -> tuple[str, str]:
        """Extract (engine, model) from the combined ASR combobox value."""
        text = self.asr_combo_var.get()
        for engine, model, label in _ASR_OPTIONS:
            if text.startswith(label):
                return engine, model
        return "sensevoice", "FunAudioLLM/SenseVoiceSmall"

    # ────────────── Tab 3: LLM ──────────────

    def _build_llm_tab(self, notebook: ttk.Notebook):
        tab = ttk.Frame(notebook, padding=12)
        notebook.add(tab, text=self.s["tab_llm"])

        llm = self.config.get("llm", {})

        # Enable checkbox
        self.llm_enabled_var = tk.BooleanVar(value=llm.get("enabled", True))
        ttk.Checkbutton(tab, text=self.s["enable_llm"],
                        variable=self.llm_enabled_var).pack(anchor="w", pady=(0, 10))

        # Provider
        prov_frame = ttk.LabelFrame(
            tab, text=f"🔗 {self.s['provider']}", padding=10)
        prov_frame.pack(fill="x", pady=(0, 10))
        prov_frame.columnconfigure(1, weight=1)

        ttk.Label(prov_frame, text=self.s["provider"] + ":").grid(
            row=0, column=0, sticky="w", padx=8, pady=4)
        self.llm_provider_var = tk.StringVar(value=llm.get("provider", "ollama"))
        provider_combo = ttk.Combobox(
            prov_frame, textvariable=self.llm_provider_var,
            values=["ollama", "openai", "none"], width=14,
            state="readonly", font=_FONT)
        provider_combo.grid(row=0, column=1, sticky="w", padx=8, pady=4)
        provider_combo.bind("<<ComboboxSelected>>", self._on_provider_change)

        # Endpoint + detect
        ttk.Label(prov_frame, text=self.s["endpoint"] + ":").grid(
            row=1, column=0, sticky="w", padx=8, pady=4)
        ep_inner = ttk.Frame(prov_frame)
        ep_inner.grid(row=1, column=1, sticky="ew", padx=8, pady=4)
        self.llm_endpoint_var = tk.StringVar(
            value=llm.get("endpoint", "http://localhost:11434"))
        ttk.Entry(ep_inner, textvariable=self.llm_endpoint_var, width=35,
                  font=_FONT).pack(side="left")
        ttk.Button(ep_inner, text=f"🔍 {self.s['detect']}", width=8,
                   command=self._detect_endpoint).pack(side="left", padx=4)
        self.endpoint_status = ttk.Label(ep_inner, text="", foreground="green",
                                          font=_FONT)
        self.endpoint_status.pack(side="left", padx=4)

        # API key (openai only)
        self.api_key_label = ttk.Label(prov_frame, text=self.s["api_key"] + ":")
        self.api_key_label.grid(row=2, column=0, sticky="w", padx=8, pady=4)
        self.llm_api_key_var = tk.StringVar(value=llm.get("api_key", ""))
        self.api_key_entry = ttk.Entry(prov_frame, textvariable=self.llm_api_key_var,
                                       width=35, font=_FONT, show="*")
        self.api_key_entry.grid(row=2, column=1, sticky="w", padx=8, pady=4)

        # Model + refresh
        ttk.Label(prov_frame, text=self.s["model"] + ":").grid(
            row=3, column=0, sticky="w", padx=8, pady=4)
        model_inner = ttk.Frame(prov_frame)
        model_inner.grid(row=3, column=1, sticky="ew", padx=8, pady=4)
        self.llm_model_var = tk.StringVar(value=llm.get("model", "qwen2.5:3b"))
        self.llm_model_combo = ttk.Combobox(
            model_inner, textvariable=self.llm_model_var, width=24, font=_FONT)
        self.llm_model_combo.pack(side="left")
        self.refresh_btn = ttk.Button(
            model_inner, text=f"🔄 {self.s['refresh']}", width=10,
            command=self._refresh_ollama_models)
        self.refresh_btn.pack(side="left", padx=4)

        # Prompt
        prompt_frame = ttk.LabelFrame(
            tab, text=f"📝 {self.s['prompt']}", padding=10)
        prompt_frame.pack(fill="x", pady=(0, 10))

        self.prompt_text = tk.Text(prompt_frame, height=6, wrap="word", font=_FONT)
        self.prompt_text.pack(fill="x", padx=4, pady=(0, 4))
        self.prompt_text.insert("1.0", _load_prompt_from_config(self.config))

        restore_label = "🔄 恢复默认" if self.s == _STRINGS["zh"] else "🔄 Restore Default"
        ttk.Button(prompt_frame, text=restore_label, width=14,
                   command=self._restore_default_prompt).pack(anchor="e", padx=4, pady=(0, 4))



        # Temperature
        temp_frame = ttk.Frame(tab)
        temp_frame.pack(fill="x", pady=(0, 4))
        ttk.Label(temp_frame, text=self.s["temperature"] + ":").pack(
            side="left", padx=8)
        self.llm_temp_var = tk.DoubleVar(value=llm.get("temperature", 0.1))
        ttk.Scale(temp_frame, from_=0.0, to=1.0, variable=self.llm_temp_var,
                  orient="horizontal", length=220).pack(side="left")
        self.temp_label = ttk.Label(temp_frame,
                                    text=f"{self.llm_temp_var.get():.2f}", width=5)
        self.temp_label.pack(side="left", padx=6)
        self.llm_temp_var.trace_add("write", self._update_temp_label)

        # Initial visibility
        self._on_provider_change()

    def _load_preset(self, name: str):
        """Load prompt from prompts/ directory."""
        try:
            from talkrefine.llm.prompts import load_prompt
            text = load_prompt(name)
            self.prompt_text.delete("1.0", "end")
            self.prompt_text.insert("1.0", text)
        except Exception:
            pass

    def _restore_default_prompt(self):
        """Restore prompt to the default template from prompts/default.txt."""
        text = _load_default_prompt()
        self.prompt_text.delete("1.0", "end")
        self.prompt_text.insert("1.0", text)

    def _update_temp_label(self, *_args):
        try:
            self.temp_label.configure(text=f"{self.llm_temp_var.get():.2f}")
        except Exception:
            pass

    def _on_provider_change(self, _event=None):
        provider = self.llm_provider_var.get()
        if provider == "openai":
            self.api_key_label.grid()
            self.api_key_entry.grid()
        else:
            self.api_key_label.grid_remove()
            self.api_key_entry.grid_remove()

        if provider == "ollama":
            self.refresh_btn.pack(side="left", padx=4)
        else:
            self.refresh_btn.pack_forget()

    def _detect_endpoint(self):
        url = self.llm_endpoint_var.get().rstrip("/")
        # Try Ollama /api/tags first, then bare endpoint
        ok = _probe_endpoint(url + "/api/tags") or _probe_endpoint(url)
        if ok:
            self.endpoint_status.configure(
                text=self.s["endpoint_ok"], foreground="green")
        else:
            self.endpoint_status.configure(
                text=self.s["endpoint_fail"], foreground="red")

    def _refresh_ollama_models(self):
        models = discover_ollama_models()
        if models:
            self.llm_model_combo["values"] = models
        else:
            # Also try the HTTP API
            try:
                url = self.llm_endpoint_var.get().rstrip("/") + "/api/tags"
                with urllib.request.urlopen(url, timeout=5) as resp:
                    data = json.loads(resp.read())
                    models = [m["name"] for m in data.get("models", [])]
                    if models:
                        self.llm_model_combo["values"] = models
            except Exception:
                pass

    # ────────────── Tab 4: Output ──────────────

    def _build_output_tab(self, notebook: ttk.Notebook):
        tab = ttk.Frame(notebook, padding=12)
        notebook.add(tab, text=self.s["tab_output"])

        output = self.config.get("output", {})

        frame = ttk.LabelFrame(tab, text=f"📋 {self.s['tab_output']}", padding=10)
        frame.pack(fill="x", pady=(0, 10))

        self.auto_paste_var = tk.BooleanVar(value=output.get("auto_paste", True))
        ttk.Checkbutton(frame, text=self.s["auto_paste"],
                        variable=self.auto_paste_var).pack(anchor="w", pady=4)

        self.preserve_clip_var = tk.BooleanVar(
            value=output.get("preserve_clipboard", True))
        ttk.Checkbutton(frame, text=self.s["preserve_clipboard"],
                        variable=self.preserve_clip_var).pack(anchor="w", pady=4)

    # ────────────── Save ──────────────

    def _save(self):
        try:
            import yaml
        except ImportError:
            messagebox.showerror("Error", "pyyaml required:\npip install pyyaml",
                                 parent=self.win)
            return

        engine, model = self._parse_asr_selection()
        ui_lang = "en" if self.ui_lang_var.get() == "English" else "zh"
        prompt_text = self.prompt_text.get("1.0", "end").strip()

        new_config = {
            "ui_language": ui_lang,
            "hotkey": self.hotkey_var.get().strip(),
            "cancel_key": self.cancel_var.get().strip(),
            "language": self.lang_var.get(),
            "asr": {
                "engine": engine,
                "model": model,
                "device": self.asr_device_var.get(),
            },
            "llm": {
                "enabled": self.llm_enabled_var.get(),
                "provider": self.llm_provider_var.get(),
                "endpoint": self.llm_endpoint_var.get().strip(),
                "model": self.llm_model_var.get(),
                "api_key": self.llm_api_key_var.get(),
                "temperature": round(self.llm_temp_var.get(), 2),
                "max_tokens": self.config.get("llm", {}).get("max_tokens", 512),
            },
            "output": {
                "auto_paste": self.auto_paste_var.get(),
                "preserve_clipboard": self.preserve_clip_var.get(),
            },
            "ui": self.config.get("ui", {"overlay": True, "tray_icon": True}),
        }

        # Only store prompt_text if user edited it (different from default template)
        default_prompt = _load_default_prompt()
        if prompt_text and prompt_text.strip() != default_prompt.strip():
            new_config["llm"]["prompt_text"] = prompt_text
        else:
            new_config["llm"]["prompt"] = "default"

        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                yaml.dump(new_config, f, allow_unicode=True,
                          default_flow_style=False, sort_keys=False)
        except Exception as exc:
            messagebox.showerror("Error", str(exc), parent=self.win)
            return

        # Handle autostart toggle
        try:
            from talkrefine.platform import windows as plat
            plat.setup_autostart(self.autostart_var.get())
            if self.autostart_var.get():
                plat.create_start_menu_shortcut()
        except Exception:
            pass

        messagebox.showinfo(self.s["save_success"], self.s["save_msg"],
                            parent=self.win)
        self.win.destroy()

        if self.on_save:
            self.on_save(new_config)


# ────────────────────────────────────────────────────────────
# History Window
# ────────────────────────────────────────────────────────────

class HistoryWindow:
    """History viewer window showing all entries by default."""

    def __init__(self, lang: str = "zh"):
        self.win = None
        self._show_all = True
        self.history_data: list[dict] = []
        self._filter_text = ""
        if lang not in _STRINGS:
            lang = "zh"
        self.s = _STRINGS[lang]

    def show(self):
        from talkrefine.history import load_history  # noqa: F811

        if self.win and self.win.winfo_exists():
            self.win.lift()
            return

        self._show_all = True
        self._filter_text = ""
        self.tree = None
        self.win = tk.Toplevel()
        self.win.title(self.s["history_title"])
        self.win.geometry("950x1050")
        self.win.attributes("-topmost", True)
        self.win.resizable(True, True)
        self.win.minsize(850, 950)
        try:
            ico_path = Path(__file__).parent.parent.parent / "assets" / "talkrefine.ico"
            if ico_path.exists():
                self.win.iconbitmap(str(ico_path))
        except Exception:
            pass

        # Toolbar
        toolbar = ttk.Frame(self.win, padding=8)
        toolbar.pack(fill="x")
        ttk.Label(toolbar, text="📜 " + self.s["history_title"],
                  font=_FONT_HEADING).pack(side="left")
        ttk.Button(toolbar, text=self.s["clear_history"], width=10,
                   command=self._clear).pack(side="right")
        ttk.Button(toolbar, text=f"🔄 {self.s.get('refresh', '刷新')}", width=10,
                   command=self._refresh).pack(side="right", padx=5)

        # Search bar
        search_frame = ttk.Frame(self.win, padding=(10, 0, 10, 4))
        search_frame.pack(fill="x")
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", self._on_search)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var,
                                 width=40, font=_FONT)
        search_entry.pack(side="left", fill="x", expand=True)
        search_entry.insert(0, "")
        # Placeholder handled via focus events
        self._search_placeholder = self.s["search"]
        search_entry.insert(0, self._search_placeholder)
        search_entry.configure(foreground="gray")
        search_entry.bind("<FocusIn>", lambda e: self._search_focus_in(e))
        search_entry.bind("<FocusOut>", lambda e: self._search_focus_out(e))
        self._search_entry_widget = search_entry

        # Treeview
        list_frame = ttk.Frame(self.win)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)

        columns = ("time", "duration", "raw", "refined")
        self.tree = ttk.Treeview(list_frame, columns=columns, show="headings",
                                 selectmode="browse")
        self.tree.heading("time", text=self.s["time_col"])
        self.tree.heading("duration", text=self.s["duration_col"])
        self.tree.heading("raw", text=self.s["raw_col"])
        self.tree.heading("refined", text=self.s["refined_col"])

        self.tree.column("time", width=140, minwidth=130)
        self.tree.column("duration", width=55, minwidth=50)
        self.tree.column("raw", width=230, minwidth=100)
        self.tree.column("refined", width=260, minwidth=100)

        scrollbar = ttk.Scrollbar(list_frame, orient="vertical",
                                  command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        style = ttk.Style(self.win)
        style.configure("Treeview", rowheight=36)

        # Detail panel- two separate text areas
        detail_frame = ttk.Frame(self.win, padding=(10, 0, 10, 10))
        detail_frame.pack(fill="both", expand=True)

        # Raw text area
        raw_label_frame = ttk.LabelFrame(detail_frame,
            text=self.s["raw_col"], padding=4)
        raw_label_frame.pack(fill="both", expand=True, pady=(0, 4))
        self.raw_text = tk.Text(raw_label_frame, height=5, wrap="word", font=_FONT,
                                state="normal", cursor="arrow")
        self.raw_text.pack(fill="x")
        raw_btn = ttk.Button(raw_label_frame, text=self.s["copy_raw"], width=16,
                             command=self._copy_raw)
        raw_btn.pack(anchor="e", pady=2)

        # Refined text area
        refined_label_frame = ttk.LabelFrame(detail_frame,
            text=self.s["refined_col"], padding=4)
        refined_label_frame.pack(fill="both", expand=True)
        self.refined_text = tk.Text(refined_label_frame, height=5, wrap="word",
                                    font=_FONT, state="normal", cursor="arrow")
        self.refined_text.pack(fill="x")
        refined_btn = ttk.Button(refined_label_frame, text=self.s["copy_refined"],
                                 width=16, command=self._copy_refined)
        refined_btn.pack(anchor="e", pady=2)

        # Load data BEFORE any treeview access
        self.history_data = []
        self._refresh()

    # ── search helpers ──

    def _search_focus_in(self, event):
        w = event.widget
        if w.get() == self._search_placeholder:
            w.delete(0, "end")
            w.configure(foreground="black")

    def _search_focus_out(self, event):
        w = event.widget
        if not w.get():
            w.insert(0, self._search_placeholder)
            w.configure(foreground="gray")

    def _on_search(self, *_args):
        text = self.search_var.get().strip()
        if text == self._search_placeholder:
            text = ""
        self._filter_text = text.lower()
        self._populate_tree()

    # ── data ──

    def _refresh(self):
        from talkrefine.history import load_history
        try:
            all_data = load_history()
        except Exception:
            all_data = []
        self.history_data = all_data if self._show_all else all_data[:5]
        self._populate_tree()

    def _populate_tree(self):
        if self.tree is None:
            return
        self.tree.delete(*self.tree.get_children())
        for entry in self.history_data:
            raw = entry.get("raw", "")
            refined = entry.get("refined", "")
            if self._filter_text:
                combined = (raw + refined).lower()
                if self._filter_text not in combined:
                    continue
            ts = entry.get("timestamp", "")
            dur = f"{entry.get('duration', 0)}s"
            self.tree.insert("", "end", values=(
                ts, dur,
                raw[:80].replace("\n", " "),
                refined[:80].replace("\n", " "),
            ))

    def _on_select(self, _event):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        visible = self._visible_entries()
        if idx < len(visible):
            entry = visible[idx]
            self.raw_text.delete("1.0", "end")
            self.raw_text.insert("1.0", entry.get("raw", ""))
            self.refined_text.delete("1.0", "end")
            self.refined_text.insert("1.0", entry.get("refined", ""))

    def _visible_entries(self) -> list[dict]:
        if not self._filter_text:
            return self.history_data
        result = []
        for entry in self.history_data:
            combined = (entry.get("raw", "") + entry.get("refined", "")).lower()
            if self._filter_text in combined:
                result.append(entry)
        return result

    def _copy_refined(self):
        text = self.refined_text.get("1.0", "end-1c").strip()
        if text:
            self.win.clipboard_clear()
            self.win.clipboard_append(text)

    def _copy_raw(self):
        text = self.raw_text.get("1.0", "end-1c").strip()
        if text:
            self.win.clipboard_clear()
            self.win.clipboard_append(text)

    def _clear(self):
        if not messagebox.askyesno(
                self.s["confirm"], self.s["clear_confirm"], parent=self.win):
            return
        try:
            from talkrefine.history import clear_history
            clear_history()
        except Exception:
            pass
        self.history_data = []
        self._populate_tree()
        self.raw_text.delete("1.0", "end")
        self.refined_text.delete("1.0", "end")
