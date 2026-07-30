```
██╗  ██╗ █████╗  ██████╗██╗  ██╗███╗   ███╗ █████╗ ████████╗███████╗
██║  ██║██╔══██╗██╔════╝██║ ██╔╝████╗ ████║██╔══██╗╚══██╔══╝██╔════╝
███████║███████║██║     █████╔╝ ██╔████╔██║███████║   ██║   █████╗
██╔══██║██╔══██║██║     ██╔═██╗ ██║╚██╔╝██║██╔══██║   ██║   ██╔══╝
██║  ██║██║  ██║╚██████╗██║  ██╗██║ ╚═╝ ██║██║  ██║   ██║   ███████╗
╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝╚═╝     ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝
```


# goal
bog makes youtube video using hackmate.


[![Stars](https://img.shields.io/github/stars/riftaway7-code/hackmate?style=flat&color=gold)](https://github.com/riftaway7-code/hackmate/stargazers)
[![Downloads](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Friftaway7-code.github.io%2Fhackmate%2Fstats.json&query=total_downloads&label=downloads&color=brightgreen&style=flat&cacheSeconds=3600)](https://github.com/riftaway7-code/hackmate/releases)
[![Issues](https://img.shields.io/github/issues/riftaway7-code/hackmate?style=flat&color=red)](https://github.com/riftaway7-code/hackmate/issues)
[![License](https://img.shields.io/github/license/riftaway7-code/hackmate?style=flat&color=blue)](LICENSE)
[![Version](https://img.shields.io/github/v/release/riftaway7-code/hackmate?style=flat&color=green)](https://github.com/riftaway7-code/hackmate/releases)

hackmate automates the whole process of making a bootable opencore hackintosh usb. no manual config.plist editing, no hunting down kexts urself, no macrecovery commands, none of that.

works on linux, windows, and macos as the host os — doesn't matter what ur running it from.

![HackMate demo](demo.gif)

---

## 📢 announcements

**latest update** — went thru and fixed rocket lake getting mislabeled as tiger lake (was messing up gpu/platform detection), added warnings for hardware that just straight up wont boot (amd laptop cpus, mobile atom/celeron/pentium, rocket lake w/ no dgpu = no video output, atheros wifi past high sierra). also did a full audit of the kext db against live github data — fixed like 11 kexts that were silently broken (repo got renamed/deleted or the download pattern stopped matching, e.g. FakeSMC, VoodooHDA, NullEthernet, the whole BrcmPatchRAM bluetooth family), added 6 new ones that were missing, and yanked 3 that have zero working source anywhere rn. cleaned up a buncha unnecessary comment bloat in the code too.

**v2.0.0 is out** — biggest correctness release so far ngl. went thru the whole generation pipeline and found bugs that were producing EFIs that booted but were quietly broken. all fixed now:

- **`setup.py` crashed on macos.** stock macos ships python 3.9 and setup.py had 3.10-only syntax in it, so it just died before doing anything. runs on 3.8+ now.
- **acpi renames were applied without the ssdt that made them safe.** on every desktop + every ps/2-only laptop, `_OSI` got renamed to `XOSI` while nothing actually defined `XOSI` — so every firmware `_OSI` call pointed at a method that didn't exist. a rename only happens now if the table supplying its replacement is actually there.
- **the instant-wake fix was backwards.** it renamed each device's `_PRW` and left an `XPRW` method that nothing called. fixed to the standard `GPRW` → `XGPR` w/ SSDT-GPRW supplying the replacement.
- **intel wifi just never loaded.** `itlwm.kext` was given another kext's binary name so opencore refused to inject it. `ExecutablePath` now gets read straight from each bundle's own `Info.plist` so this class of bug literally can't happen again.
- **usb port maps were doing nothing.** the map's `ExecutablePath` pointed at a binary that plist-only bundles don't even have, and applying a map was disabling `USBToolBox.kext` — the thing that actually reads the map.
- **laptops were loading two acpi tables that both defined `_SB.USBX`.**

also fixed: recovery downloads for 5 macos versions shared a cache dir (big sur/el capitan, monterey/sierra, etc) and could serve the wrong image; MLB board serials were 16 chars instead of 17; kexts were getting auto-added from github repos that don't exist anymore; bluetooth kexts had overlapping version windows; `iasl` was being looked up under the wrong filename which silently killed ssdt compilation on every platform; windows ethernet detection used a deprecated query that could grab a vpn/tunnel adapter instead of ur real nic.

**new — efi health check.** point hackmate at any opencore efi, even one u built by hand, and it'll tell u whats actually wrong: orphaned acpi renames, kexts that'll never inject, usb ports that aren't really mapped, sip decoded flag by flag, deprecated kexts, missing `-no_compat_check`. it's on the welcome screen, or run it from terminal:

```bash
sudo .venv/bin/python3 src/hackmate.py --doctor            # finds your mounted EFI
.venv/bin/python3 src/hackmate.py --doctor /Volumes/EFI/EFI
```

read-only, no root needed, safe to run on a booted system.

**new — kext sources get checked before your usb even gets formatted,** so a dead download source shows up as a warning u can actually do something about instead of a kext just silently going missing.

**v1.3.0** — windows users can just download one `HackMate.exe` from the [releases page](https://github.com/riftaway7-code/hackmate/releases), no python, no venv, no setup.py needed. also fixed the amd config.plist crash, windows ssl error, macos lspci error. config.plist editor added to welcome screen too.

**if u cloned before june 25th (running from `hackmate-linux/`):**
just run ur usual command, hackmate auto-migrates itself to the new `src/` layout and relaunches. no manual steps.

**if ur on macos and got a `lspci not found` error:**
macos is fully supported now. pull latest and rerun.

**if usb formatting fails on windows:**
fixed in latest update, pull and try again. still failing? use the new **already formatted** button — format the usb as fat32 (gpt) in disk management urself first, then pick that option in hackmate.

**if u got `sudo: uv: command not found`:**
don't use `sudo uv run`. always run w/ `sudo .venv/bin/python3 src/hackmate.py` after setup.

**kaby lake (7th gen) users:**
tahoe shows up as an option for ur hardware now. pull latest and rerun.

---

## install

### linux / macos

```bash
git clone https://github.com/riftaway7-code/hackmate.git
cd hackmate
python3 setup.py
sudo .venv/bin/python3 src/hackmate.py
```

> always use the full path to the venv python (`.venv/bin/python3`) w/ `sudo` — not `python3` or `uv run`. sudo doesn't inherit ur PATH so it won't find uv or ur user-installed packages.

### windows (exe)

download `HackMate.exe` from the [latest release](https://github.com/riftaway7-code/hackmate/releases/latest) and run it as administrator.

> **antivirus false positives:** some avs (bkav, gridinsoft, zillya) flag the exe as malware. it's a known false positive w/ pyinstaller-built executables — every major av (defender, kaspersky, eset, crowdstrike, sophos) reports it clean. the exe is built transparently from source on github actions if u wanna check: [build logs](https://github.com/riftaway7-code/hackmate/actions/workflows/build-exe.yml).

### windows (from source)

> **has to be run as administrator.** right-click powershell → run as administrator before any of this.

```powershell
git clone https://github.com/riftaway7-code/hackmate.git
cd hackmate
python setup.py
.venv\Scripts\python.exe src\hackmate.py
```

> always use `.venv\Scripts\python.exe` to run hackmate — not `python` or `uv run`. the venv is what makes sure all the deps are actually there.

### gui (tkinter, no terminal needed)

prefer a windowed app over the terminal ui? `hackmate_gui.py` is the exact same backend just w/ a tkinter frontend instead of textual — no extra deps, tkinter ships w/ python already.

```bash
sudo .venv/bin/python3 src/hackmate_gui.py      # linux / macos
.venv\Scripts\python.exe src\hackmate_gui.py    # windows, run powershell as administrator
```

---

## what it actually does
1. scans ur hardware (cpu, gpu, audio, ethernet, wifi, touchpad, nvme, thunderbolt)
2. shows u which macos versions are compatible w/ ur exact hardware
3. u pick a usb drive (internal disks are hidden so u can't nuke urself)
4. fully automated from there:
   - formats usb as fat32 + creates the efi structure
   - downloads macos recovery straight from apple
   - generates smbios (serial, mlb, uuid, rom)
   - generates config.plist w/ the correct quirks for ur exact hardware
   - downloads kexts from github releases
   - downloads the latest opencore release
   - generates ssdts from ur actual dsdt using ssdttime

## supported hardware

**cpu generations:** sandy bridge · ivy bridge · haswell · broadwell · skylake · kaby lake · coffee lake · comet lake / ice lake · rocket lake and newer desktops with a supported amd dgpu · amd ryzen / threadripper desktops

**laptops tested:** thinkpad t480s, t480, t470, x1 carbon · dell xps 13/15 · hp elitebook · asus zenbook · acer aspire

**platforms:** laptops, desktops, mini-pcs

**macos versions:** ventura · sonoma · sequoia · tahoe (macos 16)

## after install
- run usbtoolbox (saved to `EFI/HackMate-Extras/`) inside macos to map ur usb ports
- swap out the placeholder `USBMap.kext` w/ the one u generate — or just use hackmate's usb mapping screen

## faq

**do i need a mac to use hackmate?**
nah. hackmate runs on linux, windows, and macos. u can make the usb from any computer u have lying around.

**will this work on my laptop/desktop?**
intel 2nd–10th gen is the normal range. 11th gen and newer intel xe graphics have no macos driver, so those desktops need a supported amd dgpu and those laptops usually arent viable. amd ryzen desktops work w/ the amd vanilla patches. run hackmate and it'll flag dead ends before it builds.

**is this the same as following the dortania opencore guide by hand?**
hackmate uses the exact same tools (macrecovery, ssdttime, opencore) that dortania recommends, just automates every single step of it. the output efi is equivalent to what u'd build by hand — minus the hours of pain.

**can i hackintosh a thinkpad?**
yeah — hackmate was literally built and tested on a thinkpad t480s. intel wifi (itlwm + heliport), trackpad (voodooi2c), all the common thinkpad hardware is supported.

**does it work on windows without python?**
yep. grab `HackMate.exe` from the releases page, no python or deps needed at all.

**my antivirus is flagging hackmate.exe**
known false positive w/ pyinstaller-built exes. every major av (defender, kaspersky, eset) reports it clean. built from source on github actions if u wanna verify — [build logs](https://github.com/riftaway7-code/hackmate/actions/workflows/build-exe.yml).

## support

hackmate is free and open source. if it saved u hours of config.plist hell, consider sponsoring:

[![GitHub Sponsors](https://img.shields.io/github/sponsors/riftaway7-code?style=flat&color=ea4aaa)](https://github.com/sponsors/riftaway7-code)

## notes
- macos is sourced directly from apple's servers
- uses the same tools the dortania guide recommends (macrecovery, ssdttime, opencore)
- tested on thinkpad t480s (i5-8350u, intel 8265 wifi, kaby lake-r)
- auto-updates itself on launch via github




### oh right my tiktok is @hackmatetech
- also heres proof @theghostrdr
