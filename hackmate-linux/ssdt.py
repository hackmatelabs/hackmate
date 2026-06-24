"""
Automated SSDT generation via SSDTTime (corpnewt/SSDTTime).

Flow:
  1. Download SSDTTime repo ZIP (includes bundled iasl for Linux)
  2. Copy DSDT from /sys/firmware/acpi/tables/DSDT
  3. Probe run (DSDT path + Q) to capture and parse the menu
  4. Generation run (DSDT path + choices + Q) to produce .aml files
  5. Copy Results/*.aml to acpi_dir
"""

import os
import re
import shutil
import subprocess
import sys
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

SSDTTIME_ZIP_URL = "https://github.com/corpnewt/SSDTTime/archive/refs/heads/master.zip"
SSDTTIME_DIR = Path(__file__).parent / "_ssdttime"

# Map our SSDT names → keywords to search for in SSDTTime's menu output
SSDT_MENU_KEYWORDS: dict[str, list[str]] = {
    "SSDT-PLUG":    ["plugintype", "plugin-type", "plugin type"],
    "SSDT-EC-USBX": ["fakeec laptop", "fake ec laptop"],
    "SSDT-EC":      ["fakeec", "fake ec"],
    "SSDT-PNLF":    ["pnlf", "backlight"],
    "SSDT-AWAC":    ["awac"],
    "SSDT-GPI0":    ["gpi0", "gpio"],
    "SSDT-XOSI":    ["xosi"],
    "SSDT-HPET":    ["fixhpet", "hpet", "irq conflict"],
    "SSDT-PMC":     ["pmc", "pmcr"],
    "SSDT-USBX":    ["usbx"],
}

# SSDTs SSDTTime has no equivalent for (none currently — THINK/TBHP removed from pipeline)
MANUAL_SSDTS: set[str] = set()


def _ensure_ssdttime() -> Path:
    """Download and extract SSDTTime if not present. Returns path to SSDTTime.py."""
    script = SSDTTIME_DIR / "SSDTTime.py"
    if script.exists():
        return script

    SSDTTIME_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = SSDTTIME_DIR / "ssdttime.zip"
    urllib.request.urlretrieve(SSDTTIME_ZIP_URL, str(zip_path))

    with zipfile.ZipFile(str(zip_path)) as z:
        z.extractall(str(SSDTTIME_DIR))
    zip_path.unlink()

    # SSDTTime-master/ contains SSDTTime.py and Scripts/
    extracted = SSDTTIME_DIR / "SSDTTime-master"
    for item in extracted.iterdir():
        dest = SSDTTIME_DIR / item.name
        if dest.exists():
            if dest.is_dir():
                shutil.rmtree(str(dest))
            else:
                dest.unlink()
        shutil.move(str(item), str(dest))
    extracted.rmdir()

    # Make bundled iasl executable
    for iasl in (SSDTTIME_DIR / "Scripts").rglob("iasl*"):
        iasl.chmod(iasl.stat().st_mode | 0o111)

    return script


def _get_dsdt(tmp: Path) -> Optional[Path]:
    """Copy DSDT binary from the running kernel's ACPI tables."""
    src = Path("/sys/firmware/acpi/tables/DSDT")
    if not src.exists():
        return None
    dst = tmp / "DSDT.aml"
    shutil.copy2(str(src), str(dst))
    return dst


def _parse_menu(output: str) -> dict[str, str]:
    """Parse SSDTTime stdout into {ssdt_name: menu_choice_number}."""
    mapping: dict[str, str] = {}
    for line in output.splitlines():
        m = re.match(r"\s*(\d+)\.\s+(.+)", line)
        if not m:
            continue
        num, label = m.group(1), m.group(2).lower()
        for ssdt, keywords in SSDT_MENU_KEYWORDS.items():
            if ssdt in mapping:
                continue
            if any(kw in label for kw in keywords):
                mapping[ssdt] = num
    return mapping


def _run(script: Path, input_text: str, timeout: int = 60) -> str:
    """Run SSDTTime.py with piped stdin; return stdout."""
    result = subprocess.run(
        [sys.executable, "-u", str(script.name)],
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=str(script.parent),
        env={**os.environ, "PYTHONUNBUFFERED": "1"},
    )
    return result.stdout + result.stderr


def generate(
    needed: list[str],
    acpi_dir: Path,
    tmp: Path,
    progress_cb=None,
) -> dict[str, str]:
    """
    Generate SSDTs for every name in `needed`, copy .aml files to `acpi_dir`.
    Returns {ssdt_name: "OK" | "SKIP: ..." | "ERROR: ..."}.
    """
    results: dict[str, str] = {}
    cb = progress_cb or (lambda m: None)

    # Split into what SSDTTime can handle vs what needs manual install
    doable   = [n for n in needed if n not in MANUAL_SSDTS]
    manual   = [n for n in needed if n in MANUAL_SSDTS]
    for n in manual:
        results[n] = "SKIP: no SSDTTime equivalent — install manually"

    if not doable:
        return results

    # ── 1. Get SSDTTime ──────────────────────────────────────────────────────
    cb("Downloading SSDTTime...")
    try:
        script = _ensure_ssdttime()
        cb(f"  SSDTTime ready at {script}")
    except Exception as e:
        for n in doable:
            results[n] = f"ERROR: could not download SSDTTime: {e}"
        return results

    # ── 2. Copy DSDT ─────────────────────────────────────────────────────────
    cb("Copying DSDT from /sys/firmware/acpi/tables/DSDT...")
    dsdt = _get_dsdt(tmp)
    if not dsdt:
        for n in doable:
            results[n] = "ERROR: DSDT not found — is this a UEFI system?"
        return results
    cb(f"  DSDT: {dsdt.stat().st_size:,} bytes")

    # ── 3. Probe run — just load DSDT and quit to capture the menu ───────────
    cb("Probing SSDTTime menu...")
    try:
        probe_out = _run(script, f"{dsdt}\nQ\n", timeout=30)
    except subprocess.TimeoutExpired:
        for n in doable:
            results[n] = "ERROR: SSDTTime timed out during probe"
        return results
    except Exception as e:
        for n in doable:
            results[n] = f"ERROR: SSDTTime probe failed: {e}"
        return results

    menu_map = _parse_menu(probe_out)
    if not menu_map:
        # Try once more — some versions output the DSDT prompt differently
        cb("  Re-probing (alternate path)...")
        try:
            probe_out2 = _run(script, f"\n{dsdt}\nQ\n", timeout=30)
            menu_map = _parse_menu(probe_out2)
        except Exception:
            pass

    if not menu_map:
        for n in doable:
            results[n] = "ERROR: could not parse SSDTTime menu output"
        return results

    cb(f"  {len(menu_map)} menu options detected: {', '.join(menu_map.keys())}")

    # ── 4. Run SSDTTime once per SSDT ────────────────────────────────────────
    # SSDTTime flow per run: ask DSDT path → show menu → pick choice → generate → show menu → Q
    acpi_dir.mkdir(parents=True, exist_ok=True)
    results_dir = script.parent / "Results"

    for ssdt in doable:
        choice = menu_map.get(ssdt)
        if not choice:
            results[ssdt] = f"SKIP: '{ssdt}' not found in this SSDTTime version"
            continue

        cb(f"Generating {ssdt}...")
        if results_dir.exists():
            shutil.rmtree(str(results_dir))

        stdin = f"{dsdt}\n{choice}\n"
        if "EC" in ssdt:
            stdin += "1\n"
        stdin += "\nQ\n"  # blank Enter for "Press [enter] to return to main menu..."

        try:
            _run(script, stdin, timeout=60)
        except subprocess.TimeoutExpired:
            results[ssdt] = "ERROR: SSDTTime timed out"
            continue
        except Exception as e:
            results[ssdt] = f"ERROR: {e}"
            continue

        found_amls = []
        if results_dir.exists():
            for aml in sorted(results_dir.rglob("*.aml")):
                dst = acpi_dir / aml.name
                shutil.copy2(str(aml), str(dst))
                found_amls.append(aml.stem.upper())
                cb(f"  {aml.name}")
            shutil.rmtree(str(results_dir))

        stem = ssdt.upper()
        matched = any(stem in a or ssdt.split("-")[1] in a for a in found_amls)
        results[ssdt] = "OK" if matched else "ERROR: SSDTTime ran but .aml not produced"

    return results
