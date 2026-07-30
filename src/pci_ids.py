"""
Real PCI-SIG / USB-IF vendor+device name lookup, from the bundled pci.ids
and usb.ids databases (src/assets/data/), instead of the narrower
hardcoded/heuristic vendor-name guesses scattered through hardware.py.

Same frozen-path pattern as ssdt.py's _assets_dir() — Path(__file__).parent
resolves inside PyInstaller's _MEIPASS bootloader in a compiled build, not
the extracted bundle.
"""

import sys
from pathlib import Path
from typing import Optional


def _data_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS) / "assets" / "data"
    return Path(__file__).parent / "assets" / "data"


_DATA = _data_dir()

# vendor_id (lowercase 4-hex) -> (vendor_name, {device_id: device_name})
_pci_cache: Optional[dict[str, tuple[str, dict[str, str]]]] = None
_usb_cache: Optional[dict[str, tuple[str, dict[str, str]]]] = None


def _parse_ids_file(path: Path) -> dict[str, tuple[str, dict[str, str]]]:
    """Parse a *.ids file (pci.ids / usb.ids share the same syntax).

    Only vendor and device lines are kept — subvendor/subdevice lines (two
    tabs) and the trailing device-class sections (lines starting with 'C ')
    aren't needed for vendor/device name lookup and are skipped.
    """
    vendors: dict[str, tuple[str, dict[str, str]]] = {}
    if not path.exists():
        return vendors

    current_vendor_id = None
    current_devices: dict[str, str] = {}

    def _flush():
        if current_vendor_id is not None:
            vendors[current_vendor_id] = (current_vendor_name, current_devices)

    current_vendor_name = ""
    try:
        with path.open("r", encoding="utf-8", errors="replace") as f:
            for line in f:
                if not line.strip() or line.startswith("#"):
                    continue
                if line.startswith("C "):
                    # Device-class section — everything after this point in
                    # the file isn't vendor/device data.
                    break
                if line.startswith("\t\t"):
                    continue  # subvendor/subdevice — not needed
                if line.startswith("\t"):
                    if current_vendor_id is None:
                        continue
                    parts = line[1:].rstrip("\n").split("  ", 1)
                    if len(parts) == 2:
                        current_devices[parts[0].strip().lower()] = parts[1].strip()
                    continue
                # vendor line
                _flush()
                parts = line.rstrip("\n").split("  ", 1)
                if len(parts) != 2:
                    current_vendor_id = None
                    continue
                current_vendor_id = parts[0].strip().lower()
                current_vendor_name = parts[1].strip()
                current_devices = {}
        _flush()
    except Exception:
        return {}
    return vendors


def _pci() -> dict[str, tuple[str, dict[str, str]]]:
    global _pci_cache
    if _pci_cache is None:
        _pci_cache = _parse_ids_file(_DATA / "pci.ids")
    return _pci_cache


def _usb() -> dict[str, tuple[str, dict[str, str]]]:
    global _usb_cache
    if _usb_cache is None:
        _usb_cache = _parse_ids_file(_DATA / "usb.ids")
    return _usb_cache


def pci_vendor_name(vendor_id: str) -> Optional[str]:
    entry = _pci().get(vendor_id.strip().lower())
    return entry[0] if entry else None


def pci_device_name(vendor_id: str, device_id: str) -> Optional[str]:
    entry = _pci().get(vendor_id.strip().lower())
    if not entry:
        return None
    return entry[1].get(device_id.strip().lower())


def usb_vendor_name(vendor_id: str) -> Optional[str]:
    entry = _usb().get(vendor_id.strip().lower())
    return entry[0] if entry else None


def usb_device_name(vendor_id: str, device_id: str) -> Optional[str]:
    entry = _usb().get(vendor_id.strip().lower())
    if not entry:
        return None
    return entry[1].get(device_id.strip().lower())
