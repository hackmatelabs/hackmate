"""
OpenCore log reader — finds the OC boot log on the USB and translates
common errors into plain English.
"""

from pathlib import Path
import re


# Known error patterns and their plain-english explanations
ERROR_PATTERNS = [
    (r"Err\(0xE\).*root_hash",
     "Boot failed: macOS could not verify the recovery image's root hash. "
     "Try setting SecureBootModel to Disabled in config.plist."),

    (r"Err\(0xE\).*EB\.LD",
     "Boot failed: OpenCore could not load a required file from the EFI partition. "
     "The file may be missing or corrupt — run Repair EFI."),

    (r"OCABC.*MMIO.*stall",
     "Memory map issue detected. Try enabling DevirtualiseMmio and adding MMIO whitelist entries."),

    (r"panic.*prior to initialization",
     "Kernel panic before macOS even started. Usually a booter/memory map issue. "
     "Make sure RebuildAppleMemoryMap, SignalAppleOS, and ProvideCurrentCpuInfo are enabled."),

    (r"Could not load.*\.kext",
     "A kext failed to load. Run Repair EFI to redownload all kexts."),

    (r"Lilu.*not found|requires Lilu",
     "A kext that depends on Lilu failed because Lilu is missing or loads after it. "
     "Make sure Lilu.kext is present and listed first in Kernel > Add."),

    (r"Failed to inject.*kext",
     "Kext injection failed. Check that the kext bundle structure is intact "
     "and the ExecutablePath in config.plist is correct."),

    (r"OC: Failed to load.*efi",
     "A driver (.efi) failed to load. It may be missing or corrupt. "
     "Run Repair EFI to redownload drivers."),

    (r"board-id.*not supported|board id.*mismatch",
     "Board ID mismatch — boot.efi rejected your hardware. "
     "Make sure -no_compat_check is in your boot-args."),

    (r"Blocked by.*security policy|apfs.*security",
     "Blocked by security policy. Set SecureBootModel to Disabled and DmgLoading to Any in config.plist."),

    (r"HideAuxiliary.*recovery.*hidden|auxiliary.*not.*show",
     "Recovery entry is hidden. Press Space in the OpenCore picker to show auxiliary entries, "
     "or set HideAuxiliary to False in config.plist."),

    (r"malloc.*failed|alloc.*failed",
     "Memory allocation failed. This can indicate a memory map problem — "
     "try enabling ProtectUefiServices and RebuildAppleMemoryMap."),

    (r"VoodooI2C.*gpio.*timeout|GPIO.*timeout",
     "VoodooI2C GPIO timeout — touchpad not initializing. "
     "Make sure SSDT-GPIO.aml is present in your ACPI folder."),

    (r"AppleALC.*layout.*not found|layout.*id.*invalid",
     "Audio layout ID not found for your codec. "
     "Try a different alcid value in boot-args (e.g. alcid=1, alcid=2, alcid=11)."),

    (r"WhateverGreen.*failed|WEG.*patch.*failed",
     "WhateverGreen could not patch your GPU framebuffer. "
     "Check that your ig-platform-id is correct for your GPU generation."),

    (r"NVMeFix.*not.*supported|nvme.*power.*management.*failed",
     "NVMeFix could not apply power management patches to your NVMe drive. "
     "This is usually harmless — the drive will still work."),

    (r"SMC.*key.*not found|VirtualSMC.*failed",
     "VirtualSMC could not emulate a required SMC key. "
     "Make sure VirtualSMC.kext and its plugins (SMCBatteryManager, SMCProcessor) are loaded."),
]


def find_oc_log(mount: Path) -> Path | None:
    """Find the most recent OpenCore log file on the mounted USB."""
    log_dir = mount / "EFI" / "OC"
    if not log_dir.exists():
        return None
    logs = sorted(log_dir.glob("opencore-*.txt"), reverse=True)
    if logs:
        return logs[0]
    # Some OC versions write to EFI root
    logs = sorted(mount.glob("opencore-*.txt"), reverse=True)
    return logs[0] if logs else None


def enable_oc_logging(config_path: Path) -> bool:
    """Enable OpenCore logging in config.plist so it writes a log file."""
    import plistlib
    try:
        with open(config_path, "rb") as f:
            cfg = plistlib.load(f)
        misc = cfg.setdefault("Misc", {})
        debug = misc.setdefault("Debug", {})
        debug["AppleDebug"]    = True
        debug["ApplePanic"]    = True
        debug["DisableWatchDog"] = True
        debug["Target"]        = 67   # file + serial logging
        debug["DisplayLevel"]  = 2147483650
        with open(config_path, "wb") as f:
            plistlib.dump(cfg, f)
        return True
    except Exception:
        return False


def parse_log(log_path: Path) -> list[tuple[str, str]]:
    """
    Parse an OpenCore log file and return a list of (level, message) tuples.
    level is "error", "warn", or "info".
    """
    try:
        text = log_path.read_text(errors="replace")
    except Exception:
        return [("error", f"Could not read log file: {log_path}")]

    findings = []
    seen = set()

    for pattern, explanation in ERROR_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            if explanation not in seen:
                seen.add(explanation)
                findings.append(("error", explanation))

    # Extract raw OC error lines for context
    raw_errors = []
    for line in text.splitlines():
        if "Err(" in line or "FAIL" in line.upper() or "panic" in line.lower():
            raw_errors.append(line.strip())

    if not findings and raw_errors:
        findings.append(("warn", "Errors found in log but no known pattern matched. Raw lines:"))
        for line in raw_errors[:10]:
            findings.append(("info", f"  {line}"))
    elif not findings:
        findings.append(("info", "No known errors found in the OpenCore log."))

    return findings
