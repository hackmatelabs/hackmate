"""
Automatic USB port map generation.

UTBMap.kext ships as an empty, disabled placeholder until a user runs the
manual post-install mapping step (boot macOS, run USBToolBox, plug a device
into every port, copy the generated kext back in via USBMappingScreen).
Almost nobody does that — "USB ports are not mapped" is ~65 of ~570 hwdb
reports, the single largest failure bucket after SSL/rate-limit/diskpart.

Two independent sources feed the map, tried in this order:

1. DSDT-derived (all platforms). Every physical USB port is declared
   statically in the machine's own ACPI firmware tables — each port device
   under the XHCI controller's scope carries an _ADR (its hardware port
   index) and a _UPC method (connectable flag + connector type), written by
   the motherboard vendor and present whether or not anything is plugged in
   or which OS is booted. HackMate already dumps+decompiles the DSDT for
   SSDT generation (see ssdt.py); this reuses that same DSDT.aml and the
   already-downloaded iasl compiler to decompile it to DSL text and scan the
   controller scope. No live device needed, no OS-specific API, no runtime
   guessing — genuinely real per-port data on Windows, Linux, and macOS
   alike. Falls back to nothing if DSDT extraction or decompilation fails
   (same failure mode ssdt.py's own SSDT generation already tolerates).

2. usbdump.exe (Windows only) — bundled inside the official USBToolBox
   Windows release, which HackMate already downloads via
   download_usbtoolbox_app(). Dumps the raw Windows USB hub/port topology
   with no user interaction needed. Used only when DSDT parsing found
   nothing usable, since it needs a device plugged in to identify a port's
   connector type/speed class — DSDT's _UPC gives that for free when it's
   present.

This module reimplements (does not vendor, to avoid pulling in USBToolBox's
wmi/pyobjc/TUI dependency stack, none of which HackMate needs) the pieces of
USBToolBox/tool needed to run headlessly — MIT licensed, github.com/
USBToolBox/tool, see Scripts/usbdump.py's get_controllers()/serialize_hub()/
guess_ports() and base.py's build_kext() for the interactive originals the
usbdump.exe path mirrors. The upstream tool has no CLI/headless mode, only
an interactive TUI, and no ACPI-only backend at all.
"""
import json
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Optional

MAP_BUNDLE_IDENTIFIER = "com.dhinakg.USBToolBox.map"
DRIVER_BUNDLE_IDENTIFIER = "com.dhinakg.USBToolBox.kext"
MAX_PORTS_PER_CONTROLLER = 15  # AppleUSBXHCI's hardcoded personality table size

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


_DEVICE_OPEN_RE = re.compile(r"Device\s*\(([A-Za-z0-9_^\\.]{1,10})\)\s*\{")
_ADR_NAME_RE = re.compile(r"Name\s*\(_ADR,\s*([^,\)]+)\)")
_ADR_METHOD_RETURN_RE = re.compile(r"Method\s*\(_ADR\b.*?Return\s*\(([^)]+)\)", re.DOTALL)
_UPC_PRESENT_RE = re.compile(r"(?:Name|Method)\s*\(_UPC\b")
_UPC_NAME_PKG_RE = re.compile(r"Name\s*\(_UPC,\s*Package\s*\([^)]*\)\s*\{(.*?)\}", re.DOTALL)

_HUB_WRAPPER_NAMES = {"RHUB", "RHB", "HUBN", "HUB0", "HUB1", "HUBP"}


def _acpi_int(raw: str) -> Optional[int]:
    raw = raw.strip().rstrip(",").strip()
    low = raw.lower()
    if low == "zero":
        return 0
    if low == "one":
        return 1
    try:
        return int(raw, 0)
    except ValueError:
        return None


def _iter_device_blocks(text: str) -> list:
    """Every `Device (NAME) { ... }` block in decompiled ASL text, as dicts
    with the device's path (tuple of ancestor names down to itself) and its
    own body text (including any nested blocks' text — callers needing just
    a block's own declarations should use leaf blocks, see below)."""
    device_starts = {m.end() - 1: m.group(1) for m in _DEVICE_OPEN_RE.finditer(text)}
    open_stack = []   # (char_index_of_open_brace, name_or_None)
    path_stack = []
    blocks = []
    for i, ch in enumerate(text):
        if ch == "{":
            name = device_starts.get(i)
            open_stack.append((i, name))
            if name:
                path_stack.append(name)
        elif ch == "}":
            if not open_stack:
                continue
            start_i, name = open_stack.pop()
            if name:
                blocks.append({"name": name, "path": tuple(path_stack), "body": text[start_i + 1:i]})
                path_stack.pop()
    return blocks


def _leaf_port_blocks(blocks: list) -> list:
    """Blocks with no nested Device children (so a controller/hub wrapper's
    own _ADR — its PCI address, not a port index — never gets misread as a
    port) that declare _UPC — the ACPI-spec USB port capability method,
    which in practice is used for nothing but USB ports, so requiring it
    filters out unrelated _ADR-bearing devices (PCI slots, GPIO, ...)."""
    container_paths = {b["path"][:-1] for b in blocks if len(b["path"]) > 1}
    return [b for b in blocks if b["path"] not in container_paths and _UPC_PRESENT_RE.search(b["body"])]


def _port_index(body: str) -> Optional[int]:
    m = _ADR_NAME_RE.search(body)
    if m:
        return _acpi_int(m.group(1))
    m = _ADR_METHOD_RETURN_RE.search(body)
    if m:
        return _acpi_int(m.group(1))
    return None


def _port_connector_type(body: str) -> Optional[int]:
    """Only the static `Name (_UPC, Package {...})` form is evaluated — a
    `Method (_UPC, ...)` can compute its return value at runtime (rare, but
    real), which isn't something worth a hand-rolled AML interpreter for.
    Those ports still get mapped, just with the generic USB-A fallback."""
    m = _UPC_NAME_PKG_RE.search(body)
    if not m:
        return None
    parts = [p.strip() for p in m.group(1).split(",") if p.strip()]
    if len(parts) < 2:
        return None
    return _acpi_int(parts[1])


def parse_dsdt_ports(dsl_text: str) -> dict:
    """decompiled DSDT DSL text -> {controller_name: [port dict, ...]}."""
    blocks = _iter_device_blocks(dsl_text)
    ports_by_parent: dict = {}

    for block in _leaf_port_blocks(blocks):
        index = _port_index(block["body"])
        if index is None or index <= 0:
            continue
        parent_path = block["path"][:-1]
        if not parent_path:
            continue
        controller_name = parent_path[-1]
        if controller_name in _HUB_WRAPPER_NAMES and len(parent_path) > 1:
            controller_name = parent_path[-2]
        ports_by_parent.setdefault(controller_name, []).append({
            "index": index,
            "class": "Unknown",
            "type": _port_connector_type(block["body"]),
            "guessed": None,
        })

    return ports_by_parent


def decompile_dsdt(tmp: Path, log=None) -> Optional[str]:
    """Reuses ssdt.py's already-downloaded iasl + the same DSDT dump/decompile
    path SSDT generation relies on, so this piggybacks on setup that has
    already happened by the time it's called in the build flow instead of
    fetching iasl a second time."""
    def _log(msg, level="info"):
        if log:
            log(msg, level)

    from compat import get_dsdt, find_iasl, chmod_iasl
    from ssdt import SSDTTIME_DIR

    dsdt_path = get_dsdt(tmp)
    if not dsdt_path:
        _log("  Auto USB mapping: DSDT unavailable — skipping ACPI-derived map", "warn")
        return None

    chmod_iasl(SSDTTIME_DIR)
    iasl = find_iasl(SSDTTIME_DIR)
    if not iasl:
        _log("  Auto USB mapping: iasl unavailable — skipping ACPI-derived map", "warn")
        return None

    try:
        subprocess.run([str(iasl), "-d", str(dsdt_path)], capture_output=True, timeout=30)
        dsl_path = dsdt_path.with_suffix(".dsl")
        if not dsl_path.exists():
            return None
        return dsl_path.read_text(errors="replace")
    except Exception:
        return None


def generate_dsdt_map(tmp: Path, log=None) -> Optional[dict]:
    def _log(msg, level="info"):
        if log:
            log(msg, level)

    dsl_text = decompile_dsdt(tmp, log=log)
    if not dsl_text:
        return None

    ports_by_controller = parse_dsdt_ports(dsl_text)
    if not ports_by_controller:
        _log("  Auto USB mapping: no USB ports found in DSDT — skipping", "warn")
        return None

    personalities = {}
    for controller_name, ports in ports_by_controller.items():
        selected = sorted(ports, key=lambda p: p["index"])[:MAX_PORTS_PER_CONTROLLER]
        prefix = _speed_prefix(selected)
        entry_ports = {}
        highest_index = 0
        for i, port in enumerate(selected, start=1):
            highest_index = max(highest_index, port["index"])
            connector = port["type"] if port["type"] is not None else TYPE_USB_A
            port_name = f"{prefix}{str(i).zfill(max(1, 4 - len(prefix)))}"
            entry_ports[port_name] = {
                "port": port["index"].to_bytes(4, byteorder="little"),
                "UsbConnector": connector,
            }
        if not entry_ports:
            continue
        personalities[controller_name] = {
            "CFBundleIdentifier": DRIVER_BUNDLE_IDENTIFIER,
            "IOClass": "USBToolBox",
            "IOProviderClass": "IOPCIDevice",
            "IOMatchCategory": "USBToolBox",
            "IONameMatch": controller_name,
            "IOProviderMergeProperties": {
                "ports": entry_ports,
                "port-count": highest_index.to_bytes(4, byteorder="little"),
            },
        }

    if not personalities:
        return None

    total_ports = sum(len(p["IOProviderMergeProperties"]["ports"]) for p in personalities.values())
    _log(f"  Auto USB mapping (ACPI): mapped {total_ports} port(s) across "
         f"{len(personalities)} controller(s) from the DSDT", "ok")

    template = dict(_INFO_PLIST_TEMPLATE)
    template["IOKitPersonalities"] = personalities
    return template


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


def generate_auto_map(usbtoolbox_zip: Optional[Path], tmp_dir: Path, log=None) -> Optional[dict]:
    """Full pipeline, tried in order: DSDT-derived (works on every platform,
    real per-port data straight from firmware) → usbdump.exe (Windows only,
    needs usbtoolbox_zip). Returns None (never raises) on total failure —
    callers should fall back to the existing manual-mapping flow rather than
    ship a partial/broken map."""
    def _log(msg, level="info"):
        if log:
            log(msg, level)

    dsdt_plist = generate_dsdt_map(tmp_dir, log=log)
    if dsdt_plist:
        return dsdt_plist

    if not usbtoolbox_zip:
        return None

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
    _log(f"  Auto USB mapping (usbdump): mapped {total_ports} port(s) across "
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
