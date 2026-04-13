"""Windows platform implementation."""

import os
import sys
import time
import threading


_hotkey_manager = None


def register_hotkey(key: str, callback):
    """Register a global hotkey (uses Win32 API, survives lock/unlock)."""
    global _hotkey_manager
    if _hotkey_manager is None:
        from talkrefine.platform.hotkeys import HotkeyManager
        _hotkey_manager = HotkeyManager()
    _hotkey_manager.register(key, callback)


def start_hotkey_listener():
    """Start the hotkey message loop. Call after all register_hotkey() calls."""
    if _hotkey_manager:
        _hotkey_manager.start()


def wait_forever():
    """Block the current thread until interrupted."""
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass


def paste_text(text: str, preserve_clipboard: bool = True):
    """Paste text at current cursor position."""
    import pyperclip
    import pyautogui

    old_clipboard = None
    if preserve_clipboard:
        try:
            old_clipboard = pyperclip.paste()
        except Exception:
            pass

    pyperclip.copy(text)
    time.sleep(0.15)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.15)

    if preserve_clipboard and old_clipboard is not None:
        try:
            pyperclip.copy(old_clipboard)
        except Exception:
            pass


def copy_text(text: str):
    """Copy text to clipboard."""
    import pyperclip
    pyperclip.copy(text)


def _create_shortcut_ps(shortcut_path, target, arguments, working_dir, description,
                        icon_path=None):
    """Create .lnk shortcut using PowerShell (fallback when pywin32 unavailable)."""
    import subprocess
    ps_lines = [
        '$ws = New-Object -ComObject WScript.Shell',
        f'$sc = $ws.CreateShortcut("{shortcut_path}")',
        f'$sc.TargetPath = "{target}"',
        f"$sc.Arguments = '{arguments}'",
        f'$sc.WorkingDirectory = "{working_dir}"',
        f'$sc.Description = "{description}"',
        '$sc.WindowStyle = 7',
    ]
    if icon_path and os.path.exists(icon_path):
        ps_lines.append(f'$sc.IconLocation = "{icon_path}"')
    ps_lines.append('$sc.Save()')
    ps_script = '; '.join(ps_lines)
    subprocess.run(["powershell", "-Command", ps_script],
                   capture_output=True, timeout=10)


def setup_autostart(enable: bool = True):
    """Add/remove from Windows startup folder."""
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    vbs_path = os.path.join(project_root, "scripts", "start_hidden.vbs")
    ico_path = os.path.join(project_root, "assets", "talkrefine.ico")

    startup_folder = os.path.join(
        os.environ.get("APPDATA", ""),
        r"Microsoft\Windows\Start Menu\Programs\Startup"
    )
    shortcut_path = os.path.join(startup_folder, "TalkRefine.lnk")

    # Clean up old registry entry if present
    try:
        import winreg
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                             r"Software\Microsoft\Windows\CurrentVersion\Run",
                             0, winreg.KEY_SET_VALUE)
        try:
            winreg.DeleteValue(key, "TalkRefine")
        except FileNotFoundError:
            pass
        winreg.CloseKey(key)
    except Exception:
        pass

    if enable:
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            sc = shell.CreateShortCut(shortcut_path)
            sc.TargetPath = "wscript.exe"
            sc.Arguments = f'"{vbs_path}"'
            sc.WorkingDirectory = project_root
            sc.Description = "TalkRefine"
            sc.WindowStyle = 7
            if os.path.exists(ico_path):
                sc.IconLocation = ico_path
            sc.Save()
        except ImportError:
            # Fallback: use PowerShell to create shortcut
            _create_shortcut_ps(shortcut_path, "wscript.exe",
                                f'"{vbs_path}"', project_root,
                                "TalkRefine", ico_path)
        except Exception as e:
            print(f"⚠️  Startup shortcut: {e}")
    else:
        if os.path.exists(shortcut_path):
            os.remove(shortcut_path)


def create_start_menu_shortcut():
    """Create a Start Menu shortcut."""
    start_menu = os.path.join(
        os.environ.get("APPDATA", ""),
        r"Microsoft\Windows\Start Menu\Programs"
    )
    shortcut_path = os.path.join(start_menu, "TalkRefine.lnk")
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__))))
    vbs_path = os.path.join(project_root, "scripts", "start_hidden.vbs")
    ico_path = os.path.join(project_root, "assets", "talkrefine.ico")

    try:
        import win32com.client
        shell = win32com.client.Dispatch("WScript.Shell")
        sc = shell.CreateShortCut(shortcut_path)
        sc.TargetPath = "wscript.exe"
        sc.Arguments = f'"{vbs_path}"'
        sc.WorkingDirectory = project_root
        sc.Description = "TalkRefine - Voice to refined text"
        sc.WindowStyle = 7
        if os.path.exists(ico_path):
            sc.IconLocation = ico_path
        sc.Save()
        return shortcut_path
    except ImportError:
        _create_shortcut_ps(shortcut_path, "wscript.exe",
                            f'"{vbs_path}"', project_root,
                            "TalkRefine - Voice to refined text", ico_path)
        return shortcut_path
    except Exception as e:
        print(f"⚠️  Failed to create shortcut: {e}")
        return None


def remove_start_menu_shortcut():
    """Remove Start Menu shortcut."""
    shortcut_path = os.path.join(
        os.environ.get("APPDATA", ""),
        r"Microsoft\Windows\Start Menu\Programs",
        "TalkRefine.lnk"
    )
    if os.path.exists(shortcut_path):
        os.remove(shortcut_path)
