"""Generate representative configs for the official OpenCore validator."""

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from config_gen import generate, write_plist
from hardware import HardwareProfile
from smbios import SMBIOSData


PROFILES = {
    "coffee-desktop": HardwareProfile(
        cpu_vendor="intel",
        cpu_generation=8,
        cpu_codename="Coffee Lake",
        oc_platform="Coffee Lake",
        gpu_vendor="intel",
        gpu_name="Intel UHD Graphics 630",
        platform="desktop",
        audio_codec="ALC1220",
        ethernet_chipset="i219",
        smbios_model="iMac19,1",
    ),
    "kaby-laptop": HardwareProfile(
        cpu_vendor="intel",
        cpu_generation=7,
        cpu_codename="Kaby Lake",
        oc_platform="Kaby Lake",
        gpu_vendor="intel",
        gpu_name="Intel HD Graphics 630",
        dgpu_vendor="nvidia",
        platform="laptop",
        audio_codec="ALC257",
        smbios_model="MacBookPro14,1",
    ),
    "comet-amd-dgpu": HardwareProfile(
        cpu_vendor="intel",
        cpu_generation=10,
        cpu_codename="Comet Lake",
        oc_platform="Comet Lake",
        gpu_vendor="intel",
        gpu_name="Intel UHD Graphics 630",
        dgpu_vendor="amd",
        platform="desktop",
        smbios_model="iMac20,1",
    ),
    "ryzen-desktop": HardwareProfile(
        cpu_vendor="amd",
        cpu_generation=11,
        cpu_codename="Zen 3",
        oc_platform="Ryzen",
        core_count=8,
        gpu_vendor="amd",
        gpu_name="AMD Radeon RX 6600",
        platform="desktop",
        smbios_model="MacPro7,1",
    ),
    "sandy-laptop": HardwareProfile(
        cpu_vendor="intel",
        cpu_generation=2,
        cpu_codename="Sandy Bridge",
        oc_platform="Sandy Bridge",
        gpu_vendor="intel",
        gpu_name="Intel HD Graphics 3000",
        platform="laptop",
        smbios_model="MacBookPro8,1",
    ),
}


def main(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for index, (name, profile) in enumerate(PROFILES.items(), start=1):
        smbios = SMBIOSData(
            model=profile.smbios_model,
            serial=f"C02TEST{index:05d}",
            board_serial=f"C02TESTMLB{index:06d}",
            system_uuid=f"00000000-0000-4000-8000-{index:012d}",
            rom=f"00112233{index:04x}",
        )
        write_plist(generate(profile, smbios, macos_major=15), output_dir / f"{name}.plist")


if __name__ == "__main__":
    main(Path(sys.argv[1]))
