from __future__ import annotations
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PartEntry:
    number: int
    start_bytes: int
    end_bytes: int
    size_bytes: int
    fs_type: str
    label: str
    disk: str

    @property
    def device(self) -> str:
        if re.match(r"/dev/(?:nvme|mmcblk)", self.disk):
            return f"{self.disk}p{self.number}"
        return f"{self.disk}{self.number}"

    @property
    def size_gb(self) -> float:
        return self.size_bytes / (1024 ** 3)


def list_partitions(disk: str) -> list[PartEntry]:
    """List partitions on a disk with byte-accurate sizes via parted."""
    try:
        out = subprocess.run(
            ["parted", "-m", disk, "unit", "B", "print"],
            capture_output=True, text=True, timeout=10
        ).stdout
    except Exception:
        return []
    entries = []
    for line in out.splitlines():
        # parted -m format: number:startB:endB:sizeB:fs:label:flags;
        m = re.match(r"^(\d+):(\d+)B:(\d+)B:(\d+)B:([^:]*):([^:]*):([^;]*);", line)
        if m:
            num, start, end, size, fs, label = (
                int(m.group(1)), int(m.group(2)), int(m.group(3)),
                int(m.group(4)), m.group(5).lower(), m.group(6)
            )
            entries.append(PartEntry(
                number=num,
                start_bytes=start,
                end_bytes=end,
                size_bytes=size,
                fs_type=fs,
                label=label,
                disk=disk,
            ))
    return entries


def check_tools() -> dict[str, bool]:
    tools = ["parted", "ntfsresize", "resize2fs", "e2fsck", "btrfs", "partprobe"]
    return {t: shutil.which(t) is not None for t in tools}


def parse_size_input(s: str) -> int | None:
    """Parse user input like '50 GB', '100G', '500M' into bytes. Returns None on error."""
    s = s.strip().upper().replace(" ", "")
    m = re.match(r"^(\d+(?:\.\d+)?)\s*(GB?|MB?|TB?|B?)$", s)
    if not m:
        return None
    val = float(m.group(1))
    unit = m.group(2).rstrip("B") or "B"
    multipliers = {"": 1, "B": 1, "K": 1024, "M": 1024**2, "G": 1024**3, "T": 1024**4}
    return int(val * multipliers.get(unit, 0))


def get_min_ntfs_size(device: str) -> int | None:
    """Return minimum NTFS size in bytes, or None if can't determine."""
    try:
        out = subprocess.run(
            ["ntfsresize", "--info", "--force", device],
            capture_output=True, text=True, timeout=20
        )
        text = out.stdout + out.stderr
        m = re.search(r"You might resize.*?(\d+)\s+bytes", text)
        if m:
            return int(m.group(1))
        m = re.search(r"minimum.*?size.*?:\s*(\d+)", text, re.IGNORECASE)
        if m:
            return int(m.group(1))
    except Exception:
        pass
    return None


def resize_partition(entry: PartEntry, new_size_bytes: int,
                     log_cb=None) -> str:
    """
    Shrink filesystem + update partition table for entry.
    new_size_bytes = desired partition size.
    Returns 'OK' or 'ERROR: ...'.
    """
    def log(msg: str):
        if log_cb:
            log_cb(msg)

    device = entry.device
    disk   = entry.disk
    fs     = entry.fs_type
    new_end = entry.start_bytes + new_size_bytes - 1

    if new_size_bytes >= entry.size_bytes:
        return "ERROR: new size must be smaller than current size"

    if fs == "ntfs":
        return _resize_ntfs(device, disk, entry.number, new_size_bytes, new_end, log)
    elif fs in ("ext4", "ext3", "ext2"):
        return _resize_ext4(device, disk, entry.number, new_size_bytes, new_end, log)
    elif fs == "btrfs":
        return _resize_btrfs(device, disk, entry.number, new_size_bytes, new_end, log)
    else:
        return f"ERROR: '{fs}' resize is not supported (only NTFS, ext4, btrfs)"


def _resize_ntfs(device, disk, partnum, new_size_bytes, new_end, log):
    if not shutil.which("ntfsresize"):
        return "ERROR: ntfsresize not found — install ntfs-3g-progs"

    log("  ntfsresize dry-run…")
    r = subprocess.run(
        ["ntfsresize", "-n", "--force", "-s", str(new_size_bytes), device],
        capture_output=True, text=True, timeout=60
    )
    if r.returncode != 0:
        return f"ERROR: dry-run failed:\n{(r.stdout + r.stderr).strip()[-400:]}"
    log("  Dry-run OK — resizing NTFS filesystem…")

    r = subprocess.run(
        ["ntfsresize", "--force", "-s", str(new_size_bytes), device],
        input="y\n", capture_output=True, text=True, timeout=600
    )
    if r.returncode != 0:
        return f"ERROR: ntfsresize failed:\n{(r.stdout + r.stderr).strip()[-400:]}"
    log("  NTFS filesystem resized")

    return _parted_resize(disk, partnum, new_end, log)


def _resize_ext4(device, disk, partnum, new_size_bytes, new_end, log):
    mounts = Path("/proc/mounts").read_text()
    if device in mounts:
        return f"ERROR: {device} is currently mounted — unmount it first"

    log("  Running e2fsck…")
    r = subprocess.run(
        ["e2fsck", "-f", "-y", device],
        capture_output=True, text=True, timeout=300
    )
    if r.returncode > 1:
        return f"ERROR: e2fsck failed (code {r.returncode}):\n{(r.stdout + r.stderr).strip()[-400:]}"
    log("  e2fsck passed — resizing ext4…")

    new_kb = new_size_bytes // 1024
    r = subprocess.run(
        ["resize2fs", device, f"{new_kb}K"],
        capture_output=True, text=True, timeout=300
    )
    if r.returncode != 0:
        return f"ERROR: resize2fs failed:\n{(r.stdout + r.stderr).strip()[-400:]}"
    log("  ext4 filesystem resized")

    return _parted_resize(disk, partnum, new_end, log)


def _resize_btrfs(device, disk, partnum, new_size_bytes, new_end, log):
    mounts = Path("/proc/mounts").read_text()
    mount_point = None
    for line in mounts.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0] == device:
            mount_point = parts[1]
            break
    if not mount_point:
        return f"ERROR: {device} is not mounted — btrfs resize requires it to be mounted"

    new_mb = new_size_bytes // (1024 * 1024)
    log(f"  Resizing btrfs at {mount_point}…")
    r = subprocess.run(
        ["btrfs", "filesystem", "resize", f"{new_mb}m", mount_point],
        capture_output=True, text=True, timeout=120
    )
    if r.returncode != 0:
        return f"ERROR: btrfs resize failed:\n{(r.stdout + r.stderr).strip()[-400:]}"
    log("  btrfs filesystem resized")

    return _parted_resize(disk, partnum, new_end, log)


def _parted_resize(disk, partnum, new_end_bytes, log):
    log("  Updating partition table…")
    r = subprocess.run(
        ["parted", "-s", disk, "resizepart", str(partnum), f"{new_end_bytes}B"],
        capture_output=True, text=True, timeout=30
    )
    if r.returncode != 0:
        return f"ERROR: parted resizepart failed:\n{(r.stdout + r.stderr).strip()[-400:]}"
    subprocess.run(["partprobe", disk], capture_output=True, timeout=10)
    log("  Partition table updated — kernel notified")
    return "OK"
