"""
Automatic USB port map generation for Windows builds.

UTBMap.kext ships as an empty, disabled placeholder until a user runs the
manual post-install mapping step (boot macOS, run USBToolBox, plug a device
into every port, copy the generated kext back in via USBMappingScreen).
Almost nobody does that — "USB ports are not mapped" is ~65 of ~570 hwdb
reports, the single largest failure bucket after SSL/rate-limit/diskpart.

usbdump.exe — bundled inside the official USBToolBox Windows release, which
HackMate already downloads via download_usbtoolbox_app() — dumps the raw
Windows USB hub/port topology (USB_NODE_CONNECTION_INFORMATION_EX etc.) with
no user interaction needed: every physical port a root hub reports, with
its index and PCI bus location, regardless of whether anything is plugged
into it. That's enough to build a real, bounded, per-port map — no
XhciPortLimit quirk, no blind guess at how many ports exist.

What it can't do headlessly: identify a port's physical connector shape
(Type-A vs Type-C) or confirm USB2/USB3 companion pairing — upstream's own
guess_ports() only fills those in for ports that have a device connected at
scan time, which is why the interactive "plug something into every port"
step exists. Ports with nothing plugged in fall back to a generic USB-A
type here, same as upstream does when a user skips typing one in manually.

This module reimplements (does not vendor, to avoid pulling in USBToolBox's
wmi/pyobjc/TUI dependency stack, none of which HackMate needs) the pieces of
USBToolBox/tool needed to run headlessly — MIT licensed, github.com/
USBToolBox/tool, see Scripts/usbdump.py's get_controllers()/serialize_hub()/
guess_ports() and base.py's build_kext() for the interactive originals this
mirrors. The upstream tool has no CLI/headless mode, only an interactive TUI.
"""
import itertools
import json
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Optional

MAP_BUNDLE_IDENTIFIER = "com.dhinakg.USBToolBox.map"
DRIVER_BUNDLE_IDENTIFIER = "com.dhinakg.USBToolBox.kext"
MAX_PORTS_PER_CONTROLLER = 15  # AppleUSBXHCI's hardcoded personality table size

# USBToolBox/tool Scripts/shared.py USBPhysicalPortTypes — 0 (USB-A) is the
# most common physical shape and macOS doesn't use this for anything
# functional beyond System Report cosmetics, so it's a safe unknown fallback.
TYPE_USB_A = 0
TYPE_INTERNAL = 255

_INFO_PLIST_TEMPLATE = {
    "CFBundleDevelopmentRegion": "English",
    "CFBundleGetInfoString": "v1.1",
    "CFBundleIdentifier": MAP_BUNDLE_IDENTIFIER,
    "CFBundleInfoDictionaryVersion": "6.0",
    "CFBundleName": "UTBMap",
    "CFBundlePackageType": "KEXT",
    "CFBundleShortVersionString": "1.1",
    "CFBundleSignature": "????",
    "CFBundleVersion": "1.1",
    "IOKitPersonalities": {},
    "OSBundleRequired": "Root",
}


def extract_usbdump(usbtoolbox_zip: Path, dest_dir: Path) -> Optional[Path]:
    """Pull usbdump.exe out of the downloaded USBToolBox Windows.zip."""
    try:
        with zipfile.ZipFile(str(usbtoolbox_zip)) as z:
            candidates = [n for n in z.namelist() if n.lower().replace("\\", "/").endswith("resources/usbdump.exe")]
            if not candidates:
                return None
            dest_dir.mkdir(parents=True, exist_ok=True)
            out = dest_dir / "usbdump.exe"
            with z.open(candidates[0]) as src, open(out, "wb") as dst:
                shutil.copyfileobj(src, dst)
            return out
    except Exception:
        return None


def _run_usbdump(usbdump_exe: Path) -> Optional[list]:
    try:
        result = subprocess.run([str(usbdump_exe)], capture_output=True, timeout=30)
        return json.loads(result.stdout.decode())
    except Exception:
        return None


def _hex_int(value) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _port_speed_class(port: dict) -> str:
    """Mirrors usbdump.py's get_port_type(): SuperSpeed/HighSpeed/FullSpeed/
    Unknown from ConnectionInfoV2's negotiated protocol flags."""
    v2 = port.get("ConnectionInfoV2")
    if not v2 or not v2.get("SupportedUsbProtocols"):
        return "Unknown"
    protocols = v2["SupportedUsbProtocols"]
    if protocols.get("Usb300"):
        return "SuperSpeed"
    if protocols.get("Usb200") and protocols.get("Usb110"):
        return "HighSpeed"
    if protocols.get("Usb110"):
        return "FullSpeed"
    return "Unknown"


def _serialize_hub(hub: dict) -> dict:
    """Mirrors usbdump.py's serialize_hub(): raw HubPorts -> our port list.
    Only walks the hub passed in (the root hub) — downstream/external hubs
    are out of scope here, same as UTBMap's typical coverage of chassis
    connectors rather than internal hub-chip fan-out."""
    hub_info = {"ports": []}
    hub_ports = hub.get("HubPorts") or []
    for i, port in enumerate(hub_ports):
        if not port:
            continue
        conn = port.get("ConnectionInfo") or {}
        index = (
            (port.get("PortConnectorProps") or {}).get("ConnectionIndex")
            or conn.get("ConnectionIndex")
            or (port.get("ConnectionInfoV2") or {}).get("ConnectionIndex")
            or i + 1
        )
        status = conn.get("ConnectionStatus") or ""
        port_info = {
            "index": _hex_int(index),
            "status": status,
            "class": "Unknown",
            "type": None,
            "guessed": None,
            "type_c": False,
            "user_connectable": True,
        }
        # Exact match, not the upstream endswith() check — Windows'
        # USB_CONNECTION_STATUS enum has "NoDeviceConnected" as a distinct
        # member, and "NoDeviceConnected".endswith("DeviceConnected") is
        # True, which would misclassify every empty port as occupied.
        if str(status) != "DeviceConnected":
            hub_info["ports"].append(port_info)
            continue

        port_info["class"] = _port_speed_class(port)
        connector_props = port.get("PortConnectorProps") or {}
        usb_port_properties = connector_props.get("UsbPortProperties") or {}
        port_info["type_c"] = bool(usb_port_properties.get("PortConnectorIsTypeC", False))
        port_info["user_connectable"] = bool(usb_port_properties.get("PortIsUserConnectable", True))
        hub_info["ports"].append(port_info)

    hub_info["ports"].sort(key=lambda p: p["index"])
    return hub_info


def _guess_port_type(port: dict) -> Optional[int]:
    """Mirrors usbdump.py's guess_ports() — without the companion-port
    binding upstream does (needs two hubs cross-referenced, out of scope
    here), so SuperSpeed ports without a companion just guess USB-A."""
    if not str(port["status"]).endswith("DeviceConnected"):
        return None
    if port["type_c"]:
        return 9  # USB3TypeC_WithSwitch
    if not port["user_connectable"]:
        return TYPE_INTERNAL
    if port["class"] == "SuperSpeed":
        return 3  # USB3TypeA
    return TYPE_USB_A


def dump_controllers(usbdump_exe: Path) -> list:
    """Mirrors usbdump.py's get_controllers(): raw usbdump.exe JSON -> our
    controller/port list, each with a real bus location and every physical
    port the root hub reports."""
    raw = _run_usbdump(usbdump_exe)
    if not raw:
        return []

    controllers = []
    for controller in raw:
        root_hub = controller.get("RootHub")
        if not root_hub:
            continue

        identifiers = {}
        if controller.get("BusDeviceFunctionValid"):
            identifiers["bdf"] = [
                _hex_int(controller.get("BusNumber")),
                _hex_int(controller.get("BusDevice")),
                _hex_int(controller.get("BusFunction")),
            ]

        hub_info = _serialize_hub(root_hub)
        for port in hub_info["ports"]:
            port["guessed"] = _guess_port_type(port)

        controllers.append({"identifiers": identifiers, "ports": hub_info["ports"]})

    return controllers


def _controller_match(controller: dict) -> Optional[tuple[str, dict]]:
    """(personality_name, IOPropertyMatch) — pcidebug only, since that's
    what usbdump.exe gives us directly with no WMI/ACPI lookup needed."""
    bdf = controller["identifiers"].get("bdf")
    if not bdf or len(bdf) != 3:
        return None
    name = "-".join(str(i) for i in bdf)
    return name, {"pcidebug": ":".join(str(i) for i in bdf)}


def _speed_prefix(ports: list) -> str:
    """Port name prefix is cosmetic — IOKit matches by controller + port
    index, not by name — so this only needs to be *a* valid identifier.
    Picks from what was actually seen connected; PRT (USBToolBox's own
    generic fallback) covers controllers where nothing was plugged in."""
    classes = {p["class"] for p in ports}
    if "SuperSpeed" in classes:
        return "SS"
    if "HighSpeed" in classes or "FullSpeed" in classes:
        return "HS"
    return "PRT"


def build_map_plist(controllers: list) -> Optional[dict]:
    """controllers (from dump_controllers()) -> a USBToolBox map Info.plist
    dict, or None if nothing usable was found. Mirrors build_kext() in
    USBToolBox/tool's base.py."""
    personalities = {}

    for controller in controllers:
        match = _controller_match(controller)
        ports = controller.get("ports") or []
        if match is None or not ports:
            continue
        personality_name, property_match = match

        prefix = _speed_prefix(ports)
        selected = sorted(ports, key=lambda p: p["index"])[:MAX_PORTS_PER_CONTROLLER]

        entry_ports = {}
        highest_index = 0
        for i, port in enumerate(selected, start=1):
            highest_index = max(highest_index, port["index"])
            connector = port["type"] if port["type"] is not None else port["guessed"]
            if connector is None:
                connector = TYPE_USB_A
            port_name = f"{prefix}{str(i).zfill(max(1, 4 - len(prefix)))}"
            entry_ports[port_name] = {
                "port": port["index"].to_bytes(4, byteorder="little"),
                "UsbConnector": connector,
            }

        if not entry_ports:
            continue

        personalities[personality_name] = {
            "CFBundleIdentifier": DRIVER_BUNDLE_IDENTIFIER,
            "IOClass": "USBToolBox",
            "IOProviderClass": "IOPCIDevice",
            "IOMatchCategory": "USBToolBox",
            "IOPropertyMatch": property_match,
            "IOProviderMergeProperties": {
                "ports": entry_ports,
                "port-count": highest_index.to_bytes(4, byteorder="little"),
            },
        }

    if not personalities:
        return None

    template = dict(_INFO_PLIST_TEMPLATE)
    template["IOKitPersonalities"] = personalities
    return template


def generate_auto_map(usbtoolbox_zip: Path, tmp_dir: Path, log=None) -> Optional[dict]:
    """Full pipeline: extract usbdump.exe from the downloaded USBToolBox
    zip, run it against this machine, and build a map plist. Returns None
    (never raises) on any failure — callers should fall back to the
    existing manual-mapping flow rather than ship a partial/broken map."""
    def _log(msg, level="info"):
        if log:
            log(msg, level)

    usbdump_exe = extract_usbdump(usbtoolbox_zip, tmp_dir)
    if usbdump_exe is None:
        _log("  Auto USB mapping: could not extract usbdump.exe from USBToolBox — skipping", "warn")
        return None

    controllers = dump_controllers(usbdump_exe)
    if not controllers:
        _log("  Auto USB mapping: usbdump found no USB controllers — skipping", "warn")
        return None

    plist = build_map_plist(controllers)
    if plist is None:
        _log("  Auto USB mapping: no usable ports found — skipping", "warn")
        return None

    total_ports = sum(len(p["IOProviderMergeProperties"]["ports"]) for p in plist["IOKitPersonalities"].values())
    _log(f"  Auto USB mapping: mapped {total_ports} port(s) across "
         f"{len(plist['IOKitPersonalities'])} controller(s)", "ok")
    return plist


def write_map_kext(plist: dict, kexts_dir: Path) -> Path:
    """Write the generated map as EFI/OC/Kexts/UTBMap.kext (plist-only bundle)."""
    kext_dir = kexts_dir / "UTBMap.kext" / "Contents"
    kext_dir.mkdir(parents=True, exist_ok=True)
    import plistlib
    with open(kext_dir / "Info.plist", "wb") as f:
        plistlib.dump(plist, f)
    return kext_dir.parent
