"""Windows platform implementation."""

import os
import sys
import time
import threading


def register_hotkey(key: str, callback):
    """Register a global hotkey."""
    import keyboard
    keyboard.add_hotkey(key, callback, suppress=False)


def wait_forever():
    """Block the current thread until interrupted."""
    import keyboard
    try:
        keyboard.wait()
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


def setup_autostart(enable: bool = True):
    """Add/remove from Windows startup via registry."""
    import winreg

    app_name = "TalkRefine"
    reg_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    vbs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))), "scripts", "start_hidden.vbs")

    if enable:
        command = f'wscript.exe "{vbs_path}"'
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0,
                             winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command)
        winreg.CloseKey(key)
    else:
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, reg_path, 0,
                                 winreg.KEY_SET_VALUE)
            winreg.DeleteValue(key, app_name)
            winreg.CloseKey(key)
        except FileNotFoundError:
            pass


def create_start_menu_shortcut():
    """Create a Start Menu shortcut."""
    try:
        import win32com.client
        start_menu = os.path.join(
            os.environ.get("APPDATA", ""),
            r"Microsoft\Windows\Start Menu\Programs"
        )
        shortcut_path = os.path.join(start_menu, "TalkRefine.lnk")
        scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__)))), "scripts")
        vbs_path = os.path.join(scripts_dir, "start_hidden.vbs")

        shell = win32com.client.Dispatch("WScript.Shell")
        sc = shell.CreateShortCut(shortcut_path)
        sc.TargetPath = "wscript.exe"
        sc.Arguments = f'"{vbs_path}"'
        sc.WorkingDirectory = scripts_dir
        sc.Description = "TalkRefine - Voice to refined text"
        sc.WindowStyle = 7
        # Set icon
        project_root = os.path.dirname(scripts_dir)
        ico_path = os.path.join(project_root, "talkrefine.ico")
        if os.path.exists(ico_path):
            sc.IconLocation = ico_path
        sc.Save()
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
