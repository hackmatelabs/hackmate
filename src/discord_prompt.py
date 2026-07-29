"""
One-time "join our Discord" prompt, shown once on first launch across every
frontend (Textual TUI, Tkinter GUI). Mirrors hwdb_submit.py's storage pattern
so both use the same ~/.hackmate/ directory and SUDO_USER-aware home
resolution (HackMate runs under sudo on Linux, where Path.home() would
otherwise point at /root instead of the actual user).
"""

import json
from pathlib import Path

INVITE_URL = "https://discord.gg/cmGqYFheMk"
WAIT_SECONDS = 3


def _real_home() -> Path:
    import os
    sudo_user = os.environ.get("SUDO_USER")
    if sudo_user:
        import pwd
        return Path(pwd.getpwnam(sudo_user).pw_dir)
    return Path.home()


_PROMPT_PATH = _real_home() / ".hackmate" / "discord_prompt.json"


def already_shown() -> bool:
    return _PROMPT_PATH.exists()


def mark_shown() -> None:
    _PROMPT_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PROMPT_PATH.write_text(json.dumps({"shown": True}))
