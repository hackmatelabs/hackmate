import json
import time
import uuid
from pathlib import Path
from typing import Optional

from compat import real_home

HISTORY_DIR = real_home() / ".hackmate" / "history"

_SCALAR_TYPES = (str, int, float, bool, type(None))


def _profile_to_dict(profile) -> dict:
    if profile is None:
        return {}
    try:
        fields = vars(profile)
    except TypeError:
        return {}
    return {k: v for k, v in fields.items() if isinstance(v, _SCALAR_TYPES)}


def save_build(
    *,
    profile=None,
    macos_version: str = "",
    config_path: Optional[Path] = None,
    efi_output_path: Optional[Path] = None,
    wifi_kext_mode: str = "",
    dual_boot: str = "",
) -> Path:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    entry_id = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    record = {
        "id": entry_id,
        "timestamp": time.time(),
        "macos_version": macos_version,
        "config_path": str(config_path) if config_path else "",
        "efi_output_path": str(efi_output_path) if efi_output_path else "",
        "wifi_kext_mode": wifi_kext_mode,
        "dual_boot": dual_boot,
        "hardware": _profile_to_dict(profile),
    }
    dest = HISTORY_DIR / f"{entry_id}.json"
    dest.write_text(json.dumps(record, indent=2))
    return dest


def list_builds() -> list[dict]:
    if not HISTORY_DIR.exists():
        return []
    records = []
    for f in HISTORY_DIR.glob("*.json"):
        try:
            records.append(json.loads(f.read_text()))
        except Exception:
            continue
    records.sort(key=lambda r: r.get("timestamp", 0), reverse=True)
    return records


def get_build(entry_id: str) -> Optional[dict]:
    dest = HISTORY_DIR / f"{entry_id}.json"
    if not dest.exists():
        return None
    try:
        return json.loads(dest.read_text())
    except Exception:
        return None


def delete_build(entry_id: str) -> bool:
    dest = HISTORY_DIR / f"{entry_id}.json"
    if not dest.exists():
        return False
    dest.unlink()
    return True
