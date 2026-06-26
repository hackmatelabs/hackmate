"""
Config.plist editor logic — parse, read, write OpenCore config.plist entries.
"""

import plistlib
import re
from pathlib import Path
from typing import Any


# ─── Boot-args helpers ────────────────────────────────────────────────────────

def parse_boot_args(args_str: str) -> dict[str, str | bool]:
    result: dict[str, str | bool] = {}
    for token in args_str.split():
        if "=" in token:
            key, val = token.split("=", 1)
            result[key] = val
        else:
            result[token] = True
    return result


def serialize_boot_args(args: dict[str, str | bool]) -> str:
    parts = []
    for key, val in args.items():
        if val is True:
            parts.append(key)
        elif val is not False and val != "":
            parts.append(f"{key}={val}")
    return " ".join(parts)


# ─── Plist path access ────────────────────────────────────────────────────────

# The long NVRAM UUID key
_NVRAM_KEY = "7C436110-AB2A-4BBB-A880-FE41995C9F82"
_NVRAM_UI  = "4D1EDE05-38C7-4A6A-9CC6-4BCCA8B38C14"

def _resolve_path(cfg: dict, path: str) -> tuple[dict, str]:
    """Walk dot-separated path, return (parent_dict, final_key)."""
    parts = path.split(".")
    node = cfg
    for part in parts[:-1]:
        if part not in node:
            raise KeyError(f"Key '{part}' not found")
        node = node[part]
    return node, parts[-1]


def get_value(cfg: dict, path: str) -> Any:
    node, key = _resolve_path(cfg, path)
    return node[key]


def set_value(cfg: dict, path: str, value: Any) -> None:
    node, key = _resolve_path(cfg, path)
    node[key] = value


# ─── High-level getters ───────────────────────────────────────────────────────

def get_boot_args(cfg: dict) -> dict[str, str | bool]:
    try:
        raw = cfg["NVRAM"]["Add"][_NVRAM_KEY]["boot-args"]
        return parse_boot_args(raw)
    except (KeyError, TypeError):
        return {}


def set_boot_args(cfg: dict, args: dict[str, str | bool]) -> None:
    cfg.setdefault("NVRAM", {}).setdefault("Add", {}).setdefault(_NVRAM_KEY, {})
    cfg["NVRAM"]["Add"][_NVRAM_KEY]["boot-args"] = serialize_boot_args(args)


def get_sip_enabled(cfg: dict) -> bool:
    """SIP enabled = csr-active-config is all zeros."""
    try:
        val = cfg["NVRAM"]["Add"][_NVRAM_KEY]["csr-active-config"]
        return all(b == 0 for b in val)
    except (KeyError, TypeError):
        return True


def set_sip(cfg: dict, enabled: bool) -> None:
    cfg.setdefault("NVRAM", {}).setdefault("Add", {}).setdefault(_NVRAM_KEY, {})
    cfg["NVRAM"]["Add"][_NVRAM_KEY]["csr-active-config"] = (
        bytes(4) if enabled else bytes([0x03, 0x00, 0x00, 0x00])
    )


def get_hide_auxiliary(cfg: dict) -> bool:
    try:
        return cfg["Misc"]["Boot"]["HideAuxiliary"]
    except (KeyError, TypeError):
        return True


def set_hide_auxiliary(cfg: dict, val: bool) -> None:
    cfg.setdefault("Misc", {}).setdefault("Boot", {})["HideAuxiliary"] = val


def get_timeout(cfg: dict) -> int:
    try:
        return int(cfg["Misc"]["Boot"]["Timeout"])
    except (KeyError, TypeError, ValueError):
        return 5


def set_timeout(cfg: dict, val: int) -> None:
    cfg.setdefault("Misc", {}).setdefault("Boot", {})["Timeout"] = val


def get_oc_logging(cfg: dict) -> bool:
    """OC file logging = Target 67."""
    try:
        return int(cfg["Misc"]["Debug"]["Target"]) > 0
    except (KeyError, TypeError, ValueError):
        return False


def set_oc_logging(cfg: dict, enabled: bool) -> None:
    cfg.setdefault("Misc", {}).setdefault("Debug", {})
    cfg["Misc"]["Debug"]["Target"] = 67 if enabled else 0
    cfg["Misc"]["Debug"]["AppleDebug"] = enabled
    cfg["Misc"]["Debug"]["ApplePanic"] = enabled
    cfg["Misc"]["Debug"]["DisableWatchDog"] = enabled


def get_secure_boot_model(cfg: dict) -> str:
    try:
        return cfg["Misc"]["Security"]["SecureBootModel"]
    except (KeyError, TypeError):
        return "Disabled"


def set_secure_boot_model(cfg: dict, val: str) -> None:
    cfg.setdefault("Misc", {}).setdefault("Security", {})["SecureBootModel"] = val


def get_smbios(cfg: dict) -> str:
    try:
        return cfg["PlatformInfo"]["Generic"]["SystemProductName"]
    except (KeyError, TypeError):
        return ""


def set_smbios(cfg: dict, val: str) -> None:
    cfg.setdefault("PlatformInfo", {}).setdefault("Generic", {})["SystemProductName"] = val


# ─── Load / Save ──────────────────────────────────────────────────────────────

def load_config(path: Path) -> dict:
    with open(path, "rb") as f:
        return plistlib.load(f)


def save_config(path: Path, cfg: dict) -> None:
    with open(path, "wb") as f:
        plistlib.dump(cfg, f)


# ─── USB discovery ────────────────────────────────────────────────────────────

def find_configs() -> list[Path]:
    """Find config.plist files on mounted volumes."""
    candidates = []

    import platform
    system = platform.system()

    if system == "Linux":
        search_roots = list(Path("/run/media").glob("*/*")) + \
                       list(Path("/media").glob("*/*")) + \
                       list(Path("/mnt").glob("*"))
    elif system == "Darwin":
        search_roots = list(Path("/Volumes").iterdir())
    else:
        # Windows: check drive letters E–Z
        search_roots = [Path(f"{c}:\\") for c in "EFGHIJKLMNOPQRSTUVWXYZ"
                        if Path(f"{c}:\\").exists()]

    for root in search_roots:
        cfg = root / "EFI" / "OC" / "config.plist"
        if cfg.exists():
            candidates.append(cfg)

    return candidates


# ─── Advanced mode type coercion ──────────────────────────────────────────────

def coerce_value(raw: str, type_hint: str) -> Any:
    if type_hint == "bool":
        return raw.lower() in ("true", "yes", "1", "on")
    if type_hint == "int":
        return int(raw)
    if type_hint == "data":
        return bytes.fromhex(raw.replace(" ", ""))
    return raw  # string
