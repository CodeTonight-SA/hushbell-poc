"""Platform-specific notification facade.

macOS: osascript notification banners
Linux: notify-send
"""
import platform
import subprocess


def notify(title: str = "HushBell", message: str = "Someone is at the door") -> bool:
    """Send a system notification. Returns True if sent."""
    system = platform.system()
    if system == "Darwin":
        return _notify_macos(title, message)
    if system == "Linux":
        return _notify_linux(title, message)
    return False


def _notify_macos(title: str, message: str) -> bool:
    script = f'display notification "{message}" with title "{title}" sound name "Submarine"'
    try:
        subprocess.run(["osascript", "-e", script], capture_output=True, timeout=5)
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def _notify_linux(title: str, message: str) -> bool:
    try:
        subprocess.run(["notify-send", title, message], capture_output=True, timeout=5)
        return True
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
