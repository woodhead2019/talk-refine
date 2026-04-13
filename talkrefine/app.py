"""TalkRefine - Main application."""

import sys
import os
import wave
import time
import tempfile
import threading
import argparse

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


def _create_asr_engine(config: dict):
    """Factory for ASR engines."""
    asr_cfg = config["asr"]
    engine = asr_cfg["engine"]

    if engine == "sensevoice":
        from talkrefine.asr.sensevoice import SenseVoiceEngine
        return SenseVoiceEngine(model=asr_cfg["model"], device=asr_cfg["device"])
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
        # Load overlay UI strings based on config
        ui_lang = config.get("ui_language", "zh")
        from talkrefine.ui.overlay import get_overlay_strings
        self.os = get_overlay_strings(ui_lang)

    def init_models(self):
        """Load ASR model and LLM provider."""
        print("⏳ Loading ASR model...")
        if self.overlay:
            self.overlay.show(self.os["loading"])

        self.asr = _create_asr_engine(self.config)
        self.asr.load()
        print(f"✅ ASR: {self.asr.name}")

        self.llm = _create_llm_provider(self.config)
        print(f"✅ LLM: {self.llm.name}")

        from talkrefine.llm.prompts import load_prompt
        prompt_cfg = self.config["llm"]
        # Support inline prompt_text from settings UI
        if prompt_cfg.get("prompt_text"):
            self.prompt_template = prompt_cfg["prompt_text"]
        else:
            self.prompt_template = load_prompt(prompt_cfg["prompt"])

        hotkey = self.config["hotkey"].upper()
        print(f"\n🟢 Ready! Press [{hotkey}] to record")

        if self.overlay:
            self.overlay.set_status(
                self.os["ready"].format(hotkey=hotkey), "#a6e3a1")
            self.overlay.schedule_hide(2000)

    def toggle_recording(self):
        if not self.recorder.recording:
            self._start_recording()
        else:
            threading.Thread(target=self._stop_and_process, daemon=True).start()

    def cancel_recording(self):
        if not self.recorder.recording:
            return
        self.recorder.stop()
        print("🚫 Recording cancelled")
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
        import keyboard
        new_hotkey = new_config["hotkey"]
        new_cancel = new_config.get("cancel_key", "esc")
        if new_hotkey != old_hotkey or new_cancel != old_cancel:
            keyboard.unhook_all_hotkeys()
            from talkrefine.platform import windows as plat
            plat.register_hotkey(new_hotkey, self.toggle_recording)
            plat.register_hotkey(new_cancel, self.cancel_recording)
            print(f"🔄 Hotkeys updated: {new_hotkey.upper()} / {new_cancel.upper()}")

        # Recreate LLM provider
        self.llm = _create_llm_provider(new_config)
        print(f"🔄 LLM: {self.llm.name}")

        # Reload prompt
        prompt_cfg = new_config["llm"]
        if prompt_cfg.get("prompt_text"):
            self.prompt_template = prompt_cfg["prompt_text"]
        else:
            from talkrefine.llm.prompts import load_prompt
            self.prompt_template = load_prompt(prompt_cfg["prompt"])

        # ASR model change requires restart
        if new_asr != old_asr:
            print("⚠️  ASR model changed, restart required")
        else:
            print("✅ Config applied (no restart needed)")

    def _start_recording(self):
        self.recorder.start()
        hotkey = self.config["hotkey"].upper()
        cancel = self.config.get("cancel_key", "esc").upper()
        print(f"🎙️  Recording...")
        if self.overlay:
            text = self.os["recording"].format(hotkey=hotkey, cancel=cancel)
            self.overlay.show(text)

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

        print(f"⏳ {duration:.1f}s recorded, recognizing...")
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
            raw_text = self.asr.transcribe(tmp_path, self.config["language"])
            # Skip if empty or only punctuation
            import re
            cleaned = re.sub(r'[\s。，、！？,.!?\-—…]+', '', raw_text or '')
            if not cleaned:
                self._show_warning(self.os["no_speech"])
                return

            print(f"📝 Raw: {raw_text}")

            # LLM refinement
            if self.config["llm"]["enabled"] and self.tray and not self.tray.llm_enabled:
                final_text = raw_text
            elif self.config["llm"]["enabled"]:
                if self.overlay:
                    self.overlay.set_status(self.os["refining"], "#cba6f7")
                final_text = self.llm.refine(raw_text, self.prompt_template)
            else:
                final_text = raw_text

            print(f"✨ Result: {final_text}")

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
                print(self.os["pasted"])
            else:
                plat.copy_text(final_text)
                print(self.os["copied"])

            if self.overlay:
                self.overlay.schedule_hide(3000)

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            if self.overlay:
                self.overlay.set_status(self.os["error"], "#f38ba8")
                self.overlay.schedule_hide(3000)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

    def _show_warning(self, msg: str):
        print(f"⚠️  {msg}")
        if self.overlay:
            self.overlay.set_status(f"⚠️ {msg}", "#f38ba8")
            self.overlay.schedule_hide(2000)

    def run(self):
        """Start the application."""
        hotkey = self.config["hotkey"]
        cancel_key = self.config.get("cancel_key", "esc")

        print("=" * 50)
        print("  🎤 TalkRefine")
        print("=" * 50)
        print(f"  Record:       [{hotkey.upper()}] (toggle)")
        print(f"  Cancel:       [{cancel_key.upper()}]")
        print(f"  ASR engine:   {self.config['asr']['engine']}"
              f" ({self.config['asr']['model']})")
        print(f"  LLM:          {self.config['llm']['provider']}"
              f" / {self.config['llm']['model']}"
              f" ({'on' if self.config['llm']['enabled'] else 'off'})")
        print(f"  Prompt:       {self.config['llm']['prompt']}")
        print(f"  Language:     {self.config['language']}")
        print(f"  Auto-paste:   {'✅' if self.config['output']['auto_paste'] else '❌'}")
        print(f"  Keep clipboard: {'✅' if self.config['output']['preserve_clipboard'] else '❌'}")
        print("=" * 50)

        # UI: overlay
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

        # UI: tray icon
        def on_quit():
            print("\n👋 Bye!")
            time.sleep(0.3)
            os._exit(0)

        self._settings_win = None
        self._history_win = None

        if self.config["ui"]["tray_icon"]:
            from talkrefine.ui.tray import TrayIcon
            from talkrefine.ui.settings import SettingsWindow, HistoryWindow

            ui_lang = self.config.get("ui_language", "zh")
            self._settings_win = SettingsWindow(self.config, on_save=self.reload_config)
            self._history_win = HistoryWindow(lang=ui_lang)

            self.tray = TrayIcon(
                hotkey=hotkey,
                on_quit=on_quit,
                on_toggle_llm=lambda v: print(
                    f"LLM: {'✅ on' if v else '❌ off'}"),
                on_open_settings=lambda: self._settings_win.show(),
                on_open_history=lambda: self._history_win.show(),
                tk_root=self.overlay.root if self.overlay else None,
                ui_language=self.config.get("ui_language", "zh"),
            )
            self.tray.start()

        # Init models + register hotkey in background
        def init_bg():
            self.init_models()
            from talkrefine.platform import windows as plat
            plat.register_hotkey(hotkey, self.toggle_recording)
            plat.register_hotkey(cancel_key, self.cancel_recording)
            print("💡 Right-click tray icon to quit\n")

        threading.Thread(target=init_bg, daemon=True).start()

        # Main loop
        if self.overlay:
            try:
                self.overlay.run()
            except KeyboardInterrupt:
                on_quit()
        else:
            from talkrefine.platform import windows as plat
            plat.wait_forever()


def main():
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
        print("✅ Autostart enabled")
        if result:
            print(f"✅ Start Menu shortcut: {result}")
        return

    if args.uninstall:
        from talkrefine.platform import windows as plat
        plat.setup_autostart(False)
        plat.remove_start_menu_shortcut()
        print("✅ Autostart removed")
        print("✅ Start Menu shortcut removed")
        return

    config = load_config(args.config)

    # Single instance check (Windows named mutex)
    import ctypes
    mutex = ctypes.windll.kernel32.CreateMutexW(None, True, "TalkRefine_SingleInstance")
    if ctypes.windll.kernel32.GetLastError() == 183:  # ERROR_ALREADY_EXISTS
        print("⚠️  TalkRefine 已在运行中，请勿重复启动。")
        print("   请在系统托盘找到 TalkRefine 图标。")
        ctypes.windll.kernel32.CloseHandle(mutex)
        return

    app = TalkRefineApp(config)
    app.run()


if __name__ == "__main__":
    main()
