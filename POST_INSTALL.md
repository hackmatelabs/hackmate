# Post-Install Guide

You booted macOS. Here's what to do next before daily driving it.

---

## 1. Map Your USB Ports (Required)

macOS has a 15 port limit per controller. Without a USB map, random ports will stop working and sleep may break.

1. Boot into macOS from your HackMate USB
2. Download **USBToolBox** from https://github.com/USBToolBox/tool/releases
3. Run it and plug something into every USB port on your machine, one at a time
4. Select all the ports you want to keep, then export `UTBMap.kext`
5. Copy `UTBMap.kext` into your USB's `EFI/OC/Kexts/` folder
6. Add it to `config.plist` under `Kernel > Add` (or run HackMate's **Repair EFI** to regenerate config with it included)

> Until you do this, some USB ports may randomly not work.

---

## 2. Move the EFI to Your Internal Drive

Right now your EFI is on the USB. To boot without the USB plugged in:

1. Open **Terminal** in macOS
2. Find your EFI partition:
   ```bash
   diskutil list
   ```
3. Mount your internal EFI:
   ```bash
   sudo diskutil mount /dev/diskXs1   # replace X with your disk number
   ```
4. Copy the entire `EFI/` folder from your USB to your internal EFI partition

> On Windows (dual boot): use **EasyUEFI** or **OpenCore Configurator** to copy the EFI.

---

## 3. Fix iMessage and iCloud (if needed)

If iMessage says "an error occurred" or iCloud won't sign in:

1. Sign out of iMessage and iCloud
2. Run HackMate **Repair EFI** — it regenerates a fresh SMBIOS with a valid serial/MLB/UUID
3. Reboot and sign back in

> Do not share your SMBIOS serials publicly.

---

## 4. Enable SIP (Optional but Recommended)

HackMate ships with SIP disabled (`csr-active-config: 00000000`) for first boot. Once everything is working:

1. Open your `config.plist`
2. Under `NVRAM > Add > 7C436110... > csr-active-config`, change `00000000` to `03000000` (partial SIP)
3. Reboot

---

## 5. Remove Verbose Boot

Once macOS is stable, remove `-v` from your boot-args in `config.plist` for a clean boot experience.

---

## 6. Enable FileVault (Optional)

FileVault works on hackintosh with the right setup:

- Make sure `ProvideConsoleGop` is True in your config
- Set `SecureBootModel` to `Default` (not `Disabled`) once everything is stable
- Then enable FileVault normally in System Preferences > Privacy & Security

---

## 7. Sleep/Wake

If your machine doesn't sleep or wakes immediately:

1. In Terminal: `sudo pmset -a hibernatemode 0` — disables hibernation (safer on hackintosh)
2. Check that `SSDT-EC-USBX.aml` is in your ACPI folder
3. Make sure your USB ports are mapped (step 1)

---

## Common Post-Install Issues

| Issue | Fix |
|-------|-----|
| No sound | Try different alcid values: add `alcid=X` to boot-args (try 1, 2, 11, 28, 97) |
| No WiFi | Check your WiFi kext is loaded in System Info > Extensions |
| Bluetooth missing | Make sure `ExtendBTFeatureFlags` is True in Kernel Quirks |
| App Store not working | Sign out, reboot, sign back in. If persists, regenerate SMBIOS |
| Brightness keys not working | Make sure `BrightnessKeys.kext` and `SSDT-PNLF.aml` are present |
| Fan always at max | Normal on first boot — macOS needs time to calibrate power management |
| Black screen on wake | Common with Intel iGPU. Add `igfxonln=1` to boot-args |
