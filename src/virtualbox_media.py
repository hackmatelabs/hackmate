"""Create an attachable VirtualBox boot disk from an EFI + Recovery tree."""

import ctypes
import shutil
import subprocess
import tempfile
from pathlib import Path


def _free_drive_letter() -> str:
    """Return an unused drive letter without relying on PowerShell."""
    mask = ctypes.windll.kernel32.GetLogicalDrives()
    for letter in "ZYXWVUTSRQPONMLKJIHGFED":
        if not mask & (1 << (ord(letter) - ord("A"))):
            return letter
    raise RuntimeError("no free Windows drive letter is available for the VirtualBox disk")


def _next_path(folder: Path) -> Path:
    base = folder / "HackMate-Monterey-VirtualBox-Boot.vhd"
    if not base.exists():
        return base
    for n in range(2, 100):
        candidate = folder / f"HackMate-Monterey-VirtualBox-Boot-{n}.vhd"
        if not candidate.exists():
            return candidate
    raise RuntimeError("too many existing HackMate VirtualBox boot disks in output folder")


def create_boot_vhd(source: Path, log=None) -> Path:
    """Package source/EFI and source/com.apple.recovery.boot in a 2 GiB VHD."""
    source = Path(source)
    efi = source / "EFI"
    recovery = source / "com.apple.recovery.boot"
    if not (efi / "BOOT" / "BOOTx64.efi").exists():
        raise RuntimeError("OpenCore BOOTx64.efi is missing from the generated EFI")
    if not recovery.exists():
        raise RuntimeError("macOS Recovery is missing; build/download recovery before packaging VirtualBox media")

    out = _next_path(source)
    letter = _free_drive_letter()
    script = "\n".join((
        f'create vdisk file="{out}" maximum=2048 type=expandable',
        f'select vdisk file="{out}"',
        "attach vdisk",
        "create partition primary",
        "format fs=fat32 quick label=HACKMATE",
        f"assign letter={letter}",
    ))
    script_path = Path(tempfile.gettempdir()) / f"hackmate_vbox_{letter}.txt"
    script_path.write_text(script, encoding="ascii")
    mounted = False
    try:
        result = subprocess.run(["diskpart", "/s", str(script_path)], capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f"DiskPart could not create the boot disk: {result.stderr or result.stdout}")
        mounted = True
        target = Path(f"{letter}:\\")
        if log:
            log(f"  Copying EFI and Monterey Recovery to {out.name}...")
        shutil.copytree(efi, target / "EFI")
        shutil.copytree(recovery, target / "com.apple.recovery.boot")
        return out
    finally:
        script_path.unlink(missing_ok=True)
        if mounted:
            detach = Path(tempfile.gettempdir()) / f"hackmate_vbox_detach_{letter}.txt"
            detach.write_text(f'select vdisk file="{out}"\ndetach vdisk\n', encoding="ascii")
            try:
                subprocess.run(["diskpart", "/s", str(detach)], capture_output=True, text=True)
            finally:
                detach.unlink(missing_ok=True)
