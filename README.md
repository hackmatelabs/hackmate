# HackMate
Automates the entire process of creating a bootable OpenCore hackintosh USB. No manual config.plist editing, no hunting down kexts, no macrecovery commands.

## Requirements
- Linux (any distro)
- Python 3.10+
- Root access

## Install & Run

```bash
git clone https://github.com/riftaway7-code/hackmate.git
cd hackmate
pip install textual
sudo python3 hackmate.py
```

That's it. Everything else (macrecovery, SSDTTime, kexts, OpenCore) is downloaded automatically at
runtime.

## What it does
1. Scans your hardware (CPU, GPU, audio, ethernet, WiFi, touchpad, NVMe, Thunderbolt)
2. Shows compatible macOS versions
3. You pick a USB drive (internal disks are hidden)
4. Fully automated from there:
   - Formats USB as FAT32 and creates EFI structure
   - Downloads macOS recovery direc
   - Generates SMBIOS (serial, MLB, UUID, ROM)
   - Generates config.plist with core
   - Downloads kexts from GitHub releases (104 kexts in database)
   - Downloads latest OpenCore rele
   - Generates SSDTs using SSDTTime from your actual DSDT

## After install
- Run USBToolBox inside macOS to ma
- Replace the placeholder USBMap.kext with your generated one

## Notes
- macOS is sourced directly from Ap installer
- Uses the same tools recommended by the Dortania guide (macrecovery, SSDTTime)
- Tested on ThinkPad T480s (i5-83509, Intel 8265 WiFi)
