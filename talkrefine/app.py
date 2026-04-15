"""TalkRefine - Main application."""

import sys
import os
import wave
import time
import tempfile
import threading
import argparse
import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

# Windows DPI awareness (must be before tkinter)
import ctypes
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Handle pythonw.exe (no stdout)
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w")
try:
    sys.stdout.reconfigure(line_buffering=True)
    sys.stderr.reconfigure(line_buffering=True)
except Exception:
    pass

from talkrefine import __version__
from talkrefine.config import load_config

logger = logging.getLogger("talkrefine")


def setup_logging():
    log_dir = Path.home() / ".talkrefine"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "talkrefine.log"

    logger.setLevel(logging.INFO)

    # File handler with rotation
    fh = RotatingFileHandler(
        log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
    logger.addHandler(fh)

    # Console handler (stdout) - only if stdout exists
    try:
        if sys.stdout and hasattr(sys.stdout, "write"):
            ch = logging.StreamHandler(sys.stdout)
            ch.setFormatter(logging.Formatter("%(message)s"))
            logger.addHandler(ch)
    except Exception:
        pass

    return logger


def _create_asr_engine(config: dict):
    """Factory for ASR engines."""
    asr_cfg = config["asr"]
    engine = asr_cfg["engine"]

    if engine == "sensevoice":
        from talkrefine.asr.sensevoice import SenseVoiceEngine
        return SenseVoiceEngine(
            model=asr_cfg["model"], device=asr_cfg["device"],
            hub=asr_cfg.get("hub", "hf"),
        )
    elif engine in ("whisper", "faster-whisper"):
        from talkrefine.asr.whisper import WhisperEngine
        return WhisperEngine(model=asr_cfg["model"], device=asr_cfg["device"])
    else:
        raise ValueError(f"Unknown ASR engine: {engine}")


def _create_llm_provider(config: dict):
    """Factory for LLM providers."""
    llm_cfg = config["llm"]

    if not llm_cfg["enabled"]:
        from talkrefine.llm.none import NoneProvider
        return NoneProvider()

    provider = llm_cfg["provider"]

    if provider == "ollama":
        from talkrefine.llm.ollama import OllamaProvider
        return OllamaProvider(
            endpoint=llm_cfg["endpoint"],
            model=llm_cfg["model"],
            temperature=llm_cfg["temperature"],
            max_tokens=llm_cfg["max_tokens"],
        )
    elif provider == "openai":
        from talkrefine.llm.openai_compat import OpenAIProvider
        return OpenAIProvider(
            endpoint=llm_cfg["endpoint"],
            model=llm_cfg["model"],
            api_key=llm_cfg.get("api_key", ""),
            temperature=llm_cfg["temperature"],
            max_tokens=llm_cfg["max_tokens"],
        )
    elif provider == "none":
        from talkrefine.llm.none import NoneProvider
        return NoneProvider()
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")


class TalkRefineApp:
    """Main application class."""

    def __init__(self, config: dict):
        self.config = config
        from talkrefine.recorder import Recorder
        self.recorder = Recorder()
        self.asr = None
        self.llm = None
        self.prompt_template = ""
        self.overlay = None
        self.tray = None
        self._models_ready = False
        self._processing = False  # Lock to prevent re-entry during ASR/LLM
        # Load overlay UI strings based on config
        ui_lang = config.get("ui_language", "zh")
        from talkrefine.ui.overlay import get_overlay_strings
        self.os = get_overlay_strings(ui_lang)

    def init_models(self):
        """Load ASR model and LLM provider (called from background thread)."""
        # Update overlay via tkinter thread-safe method
        def _show_status(text, color="#89b4fa"):
            if self.overlay:
                self.overlay.root.after(0, lambda: (
                    self.overlay.show(text),
                    self.overlay.set_status(text, color)
                ))

        _show_status(self.os["loading"])

        logger.info("⏳ Loading ASR model...")
        _show_status("⏳ ASR model loading...")
        t0 = time.time()
        self.asr = _create_asr_engine(self.config)
        self.asr.load()
        logger.info("✅ ASR: %s (loaded in %.1fs)", self.asr.name, time.time() - t0)

        logger.info("⏳ Loading LLM...")
        _show_status("⏳ LLM loading...")
        t0 = time.time()
        self.llm = _create_llm_provider(self.config)
        # Pre-load LLM into memory only if enabled (non-blocking warmup)
        if self.config["llm"]["enabled"] and hasattr(self.llm, 'warmup'):
            threading.Thread(target=self.llm.warmup, daemon=True).start()
        logger.info("✅ LLM: %s (loaded in %.1fs)", self.llm.name, time.time() - t0)

        from talkrefine.llm.prompts import load_prompt
        prompt_cfg = self.config["llm"]
        # Support inline prompt_text from settings UI
        if prompt_cfg.get("prompt_text"):
            self.prompt_template = prompt_cfg["prompt_text"]
        else:
            self.prompt_template = load_prompt(prompt_cfg["prompt"])

        self._models_ready = True

        # Start session monitor (unload LLM on lock, warmup on unlock)
        if self.config["llm"]["enabled"]:
            try:
                from talkrefine.platform.session_monitor import start_session_monitor

                def on_lock():
                    if hasattr(self.llm, 'unload'):
                        self.llm.unload()

                def on_unlock():
                    if hasattr(self.llm, 'warmup'):
                        self.llm.warmup()

                start_session_monitor(on_lock=on_lock, on_unlock=on_unlock)
            except Exception:
                logger.exception("Session monitor failed to start")

        hotkey = self.config["hotkey"].upper()
        logger.info("\n🟢 Ready! Press [%s] to record", hotkey)

        if self.overlay:
            self.overlay.root.after(0, lambda: (
                self.overlay.set_status(
                    self.os["ready"].format(hotkey=hotkey), "#a6e3a1"),
                self.overlay.schedule_hide(2000)
            ))

    def toggle_recording(self):
        if not self._models_ready:
            if self.overlay:
                self.overlay.show("⏳ Model still loading...")
                self.overlay.schedule_hide(2000)
            return
        if self._processing:
            logger.info("⏳ Still processing previous recording, ignoring")
            return
        if not self.recorder.recording:
            self._start_recording()
        else:
            self._processing = True
            threading.Thread(target=self._stop_and_process_safe, daemon=True).start()

    def _stop_and_process_safe(self):
        """Wrapper that ensures _processing flag is cleared."""
        try:
            self._stop_and_process()
        finally:
            self._processing = False

    def cancel_recording(self):
        if not self.recorder.recording:
            return
        self.recorder.stop()
        logger.info("🚫 Recording cancelled")
        if self.overlay:
            self.overlay.set_status(self.os["cancelled"], "#f9e2af")
            self.overlay.schedule_hide(1500)

    def reload_config(self, new_config: dict):
        """Hot-reload config. ASR model changes still need restart."""
        old_asr = (self.config["asr"]["engine"], self.config["asr"]["model"])
        new_asr = (new_config["asr"]["engine"], new_config["asr"]["model"])
        old_hotkey = self.config["hotkey"]
        old_cancel = self.config.get("cancel_key", "esc")

        self.config = new_config

        # Update UI language
        from talkrefine.ui.overlay import get_overlay_strings
        ui_lang = new_config.get("ui_language", "zh")
        self.os = get_overlay_strings(ui_lang)

        # Update settings window config + language for next open
        if self._settings_win:
            self._settings_win.config = new_config
            from talkrefine.ui.settings import _STRINGS
            if ui_lang in _STRINGS:
                self._settings_win.s = _STRINGS[ui_lang]

        # Update tray language + rebuild native menu
        if self.tray:
            from talkrefine.ui.tray import _TRAY_STRINGS
            self.tray._s = _TRAY_STRINGS.get(ui_lang, _TRAY_STRINGS["zh"])
            self.tray.refresh_menu()

        # Update history window language
        if self._history_win:
            if ui_lang in _STRINGS:
                self._history_win.s = _STRINGS[ui_lang]

        # Re-register hotkeys if changed
        new_hotkey = new_config["hotkey"]
        new_cancel = new_config.get("cancel_key", "esc")
        if new_hotkey != old_hotkey or new_cancel != old_cancel:
            logger.info("⚠️  Hotkey changed to %s / %s — restart needed to apply",
                        new_hotkey.upper(), new_cancel.upper())

        # Recreate LLM provider
        old_llm = self.llm
        self.llm = _create_llm_provider(new_config)
        logger.info("🔄 LLM: %s", self.llm.name)

        # Unload old model if LLM was disabled, warmup if enabled (non-blocking)
        def _llm_memory_op():
            if not new_config["llm"]["enabled"]:
                if hasattr(old_llm, 'unload'):
                    old_llm.unload()
                    logger.info("💾 LLM model unloaded (freed memory)")
            elif new_config["llm"]["enabled"] and hasattr(self.llm, 'warmup'):
                self.llm.warmup()
                logger.info("🔥 LLM model warmed up")
        threading.Thread(target=_llm_memory_op, daemon=True).start()

        # Reload prompt
        prompt_cfg = new_config["llm"]
        if prompt_cfg.get("prompt_text"):
            self.prompt_template = prompt_cfg["prompt_text"]
        else:
            from talkrefine.llm.prompts import load_prompt
            self.prompt_template = load_prompt(prompt_cfg["prompt"])

        # ASR model change → auto-restart
        if new_asr != old_asr:
            logger.info("🔄 ASR model changed, auto-restarting...")
            self._auto_restart()
        else:
            logger.info("✅ Config applied (no restart needed)")

    def _auto_restart(self):
        """Restart the program automatically."""
        import subprocess
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        vbs_path = os.path.join(project_root, "scripts", "start_hidden.vbs")

        # Launch new instance
        subprocess.Popen(["wscript.exe", vbs_path])
        logger.info("🔄 New instance launched, exiting current...")

        # Exit current
        time.sleep(1)
        os._exit(0)

    def _start_recording(self):
        self.recorder.start()
        hotkey = self.config["hotkey"].upper()
        cancel = self.config.get("cancel_key", "esc").upper()
        logger.info("🎙️  Recording...")
        if self.overlay:
            text = self.os["recording"].format(hotkey=hotkey, cancel=cancel)
            self.overlay.show(text)

        # Poll cancel key (ESC) during recording — not registered globally
        cancel_key = self.config.get("cancel_key", "esc")
        from talkrefine.platform.hotkeys import _parse_key
        _, cancel_vk = _parse_key(cancel_key)

        def poll_cancel():
            import ctypes
            import time
            user32 = ctypes.windll.user32
            while self.recorder.recording:
                # GetAsyncKeyState returns negative if key is pressed
                if user32.GetAsyncKeyState(cancel_vk) & 0x8000:
                    self.cancel_recording()
                    break
                time.sleep(0.1)

        threading.Thread(target=poll_cancel, daemon=True).start()

    def _stop_and_process(self):
        from talkrefine.recorder import SAMPLE_RATE, CHANNELS
        frames = self.recorder.stop()

        if not frames:
            self._show_warning(self.os["no_audio"])
            return

        duration = len(frames) * 1024 / SAMPLE_RATE
        if duration < 0.5:
            self._show_warning(self.os["too_short"])
            return

        logger.info("⏳ %.1fs recorded, recognizing...", duration)
        if self.overlay:
            self.overlay.set_status(self.os["recognizing"], "#89b4fa")

        # Save to temp WAV
        tmp_path = os.path.join(tempfile.gettempdir(),
                                f"talkrefine_{int(time.time())}.wav")
        with wave.open(tmp_path, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(b"".join(frames))

        try:
            # ASR
            t0 = time.time()
            raw_text = self.asr.transcribe(tmp_path, self.config["language"])
            asr_time = time.time() - t0
            # Skip if empty or only punctuation
            import re
            cleaned = re.sub(r'[\s。，、！？,.!?\-—…]+', '', raw_text or '')
            if not cleaned:
                self._show_warning(self.os["no_speech"])
                return

            logger.info("📝 Raw (ASR %.1fs): %s", asr_time, raw_text)

            # LLM refinement
            if self.config["llm"]["enabled"] and self.tray and not self.tray.llm_enabled:
                final_text = raw_text
            elif self.config["llm"]["enabled"]:
                if self.overlay:
                    self.overlay.set_status(self.os["refining"], "#cba6f7")
                t0 = time.time()
                final_text = self.llm.refine(raw_text, self.prompt_template)
                logger.info("✨ Result (LLM %.1fs): %s", time.time() - t0, final_text)
            else:
                final_text = raw_text

            if not self.config["llm"]["enabled"] or \
                    (self.tray and not self.tray.llm_enabled):
                logger.info("✨ Result: %s", final_text)

            # Save to history
            from talkrefine.history import add_entry
            add_entry(
                raw_text=raw_text,
                refined_text=final_text,
                duration=duration,
                language=self.config["language"],
                engine=self.config["asr"]["engine"],
                llm=self.config["llm"]["model"] if self.config["llm"]["enabled"] else "",
            )

            # Refresh tray menu to show latest history
            if self.tray:
                try:
                    self.tray.refresh_menu()
                except Exception:
                    pass

            # Output
            if self.overlay:
                display = final_text[:25] + ("..." if len(final_text) > 25 else "")
                self.overlay.set_status(f"✅ {display}", "#a6e3a1")

            from talkrefine.platform import windows as plat
            if self.config["output"]["auto_paste"]:
                plat.paste_text(final_text, self.config["output"]["preserve_clipboard"])
                logger.info(self.os["pasted"])
            else:
                plat.copy_text(final_text)
                logger.info(self.os["copied"])

            if self.overlay:
                self.overlay.schedule_hide(3000)

        except Exception as e:
            logger.exception("❌ Error: %s", e)
            if self.overlay:
                self.overlay.set_status(self.os["error"], "#f38ba8")
                self.overlay.schedule_hide(3000)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def _show_warning(self, msg: str):
        logger.info("⚠️  %s", msg)
        if self.overlay:
            self.overlay.set_status(f"⚠️ {msg}", "#f38ba8")
            self.overlay.schedule_hide(2000)

    def run(self):
        """Start the application."""
        hotkey = self.config["hotkey"]
        cancel_key = self.config.get("cancel_key", "esc")

        logger.info("=" * 50)
        logger.info("  🎤 TalkRefine")
        logger.info("=" * 50)
        logger.info("  Record:       [%s] (toggle)", hotkey.upper())
        logger.info("  Cancel:       [%s]", cancel_key.upper())
        logger.info("  ASR engine:   %s (%s)",
                     self.config["asr"]["engine"], self.config["asr"]["model"])
        logger.info("  LLM:          %s / %s (%s)",
                     self.config["llm"]["provider"], self.config["llm"]["model"],
                     "on" if self.config["llm"]["enabled"] else "off")
        logger.info("  Prompt:       %s", self.config["llm"]["prompt"])
        logger.info("  Language:     %s", self.config["language"])
        logger.info("  Auto-paste:   %s",
                     "✅" if self.config["output"]["auto_paste"] else "❌")
        logger.info("  Keep clipboard: %s",
                     "✅" if self.config["output"]["preserve_clipboard"] else "❌")
        logger.info("=" * 50)

        # 1. UI: overlay
        if self.config["ui"]["overlay"]:
            from talkrefine.ui.overlay import VolumeOverlay
            self.overlay = VolumeOverlay()

            # Feed volume data to overlay
            def volume_updater():
                while True:
                    if self.overlay:
                        self.overlay.update_volume(
                            self.recorder.volume, self.recorder.recording)
                    time.sleep(0.05)
            threading.Thread(target=volume_updater, daemon=True).start()

        # 2. UI: tray icon
        def on_quit():
            logger.info("\n👋 Bye!")
            time.sleep(0.3)
            os._exit(0)

        self._settings_win = None
        self._history_win = None

        if self.config["ui"]["tray_icon"]:
            from talkrefine.ui.tray import TrayIcon
            from talkrefine.ui.settings import SettingsWindow, HistoryWindow

            ui_lang = self.config.get("ui_language", "zh")
            tk_root = self.overlay.root if self.overlay else None
            self._settings_win = SettingsWindow(
                self.config, on_save=self.reload_config, parent=tk_root)
            self._history_win = HistoryWindow(lang=ui_lang, parent=tk_root)

            self.tray = TrayIcon(
                hotkey=hotkey,
                on_quit=on_quit,
                on_toggle_llm=lambda v: logger.info(
                    "LLM: %s", "✅ on" if v else "❌ off"),
                on_open_settings=lambda: self._settings_win.show(),
                on_open_history=lambda: self._history_win.show(),
                tk_root=self.overlay.root if self.overlay else None,
                ui_language=self.config.get("ui_language", "zh"),
            )
            self.tray.start()

        # 3. Register hotkeys immediately (before models are loaded)
        from talkrefine.platform import windows as plat
        plat.register_hotkey(hotkey, self.toggle_recording)
        # ESC is NOT registered globally — only polled during recording
        plat.start_hotkey_listener()
        logger.info("💡 Right-click tray icon to quit\n")

        # 4. Load models in background thread
        def init_models_bg():
            try:
                self.init_models()
            except Exception as e:
                logger.exception("❌ Model loading failed: %s", e)
                if self.overlay:
                    self.overlay.set_status(
                        f"❌ Model load failed: {e}", "#f38ba8")
                    self.overlay.schedule_hide(5000)

        threading.Thread(target=init_models_bg, daemon=True).start()

        # 5. Main loop
        if self.overlay:
            try:
                self.overlay.run()
            except KeyboardInterrupt:
                on_quit()
            else:
                logger.warning("⚠️  Main loop exited unexpectedly, restarting...")
                self.overlay.run()
        else:
            plat.wait_forever()


def main():
    setup_logging()

    # Log unhandled exceptions (critical for pythonw where stderr is hidden)
    def _excepthook(exc_type, exc_value, exc_tb):
        logger.critical("Unhandled exception", exc_info=(exc_type, exc_value, exc_tb))
    sys.excepthook = _excepthook

    # Also catch unhandled exceptions in threads
    def _thread_excepthook(args):
        logger.critical("Unhandled thread exception in %s",
                        args.thread, exc_info=(args.exc_type, args.exc_value, args.exc_traceback))
    threading.excepthook = _thread_excepthook

    parser = argparse.ArgumentParser(
        prog="talkrefine",
        description="TalkRefine - Local voice input with LLM refinement",
    )
    parser.add_argument("-c", "--config", help="Path to config.yaml")
    parser.add_argument("--install", action="store_true",
                        help="Set up autostart and Start Menu shortcut")
    parser.add_argument("--uninstall", action="store_true",
                        help="Remove autostart and shortcut")
    parser.add_argument("--version", action="version",
                        version=f"TalkRefine {__version__}")
    args = parser.parse_args()

    if args.install:
        from talkrefine.platform import windows as plat
        plat.setup_autostart(True)
        result = plat.create_start_menu_shortcut()
        logger.info("✅ Autostart enabled")
        if result:
            logger.info("✅ Start Menu shortcut: %s", result)
        return

    if args.uninstall:
        from talkrefine.platform import windows as plat
        plat.setup_autostart(False)
        plat.remove_start_menu_shortcut()
        logger.info("✅ Autostart removed")
        logger.info("✅ Start Menu shortcut removed")
        return

    config = load_config(args.config)
    logger.info("Config loaded from %s", args.config or "default location")

    # Single instance check (Windows named mutex)
    import ctypes
    mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "TalkRefine_SingleInstance")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        logger.info("⚠️  TalkRefine 已在运行中，请勿重复启动。")
        logger.info("   请在系统托盘找到 TalkRefine 图标。")
        ctypes.windll.kernel32.CloseHandle(mutex)
        return

    try:
        app = TalkRefineApp(config)
        app.run()
    except Exception:
        logger.exception("❌ Fatal error")
        raise


if __name__ == "__main__":
    main()
