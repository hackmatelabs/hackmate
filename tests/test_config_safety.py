import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import config_gen
import kexts
import log_checker
from hardware import HardwareProfile


class InstallerAudioSafetyTests(unittest.TestCase):
    def _selected_names(self, codec: str) -> set[str]:
        profile = HardwareProfile(
            cpu_vendor="intel",
            cpu_generation=8,
            platform="desktop",
            audio_codec=codec,
        )
        with (
            patch.object(kexts, "_dmi", return_value=""),
            patch.object(kexts, "_has_card_reader", return_value=False),
        ):
            return {entry.name for entry in kexts.select_kexts(profile)}

    def test_supported_codec_uses_applealc(self):
        names = self._selected_names("Realtek ALC257")

        self.assertIn("AppleALC", names)
        self.assertNotIn("VoodooHDA", names)

    def test_unknown_codec_does_not_inject_voodoohda(self):
        names = self._selected_names("Conexant CX20751")

        self.assertNotIn("AppleALC", names)
        self.assertNotIn("VoodooHDA", names)

    def test_missing_codec_keeps_safe_applealc_default(self):
        names = self._selected_names("")

        self.assertIn("AppleALC", names)
        self.assertNotIn("VoodooHDA", names)

    def test_disabled_installer_audio_omits_layout_and_boot_arg(self):
        profile = HardwareProfile(cpu_vendor="intel", platform="desktop")

        properties = config_gen._device_properties(profile, 1, audio_enabled=False)
        nvram = config_gen._nvram_section(profile, 1, audio_enabled=False)
        boot_args = nvram["Add"]["7C436110-AB2A-4BBB-A880-FE41995C9F82"]["boot-args"]

        self.assertNotIn("PciRoot(0x0)/Pci(0x1f,0x3)", properties["Add"])
        self.assertNotIn("alcid=", boot_args)

    def test_log_checker_recognizes_voodoohda_prelink_failure(self):
        log = (
            "OpenCore 1.0.7\n"
            "OC: Prelinked injection VoodooHDA.kext "
            "(fallback audio for unsupported codecs) - Invalid Parameter\n"
            "[EB|#LOG:EXITBS:START]\n"
        )

        titles = {finding.title for finding in log_checker.analyze(log)}

        self.assertIn("VoodooHDA cannot be injected from this installer EFI", titles)


class BooterQuirkSafetyTests(unittest.TestCase):
    def _quirks(self, profile: HardwareProfile, board: str = "") -> dict:
        with patch.object(config_gen, "dmi_field", return_value=board):
            return config_gen._booter_section(profile)["Quirks"]

    def test_skylake_keeps_old_firmware_memory_map_combo(self):
        profile = HardwareProfile(
            cpu_vendor="intel",
            cpu_generation=6,
            cpu_codename="Skylake",
            platform="desktop",
        )

        quirks = self._quirks(profile)

        self.assertTrue(quirks["EnableWriteUnprotector"])
        self.assertFalse(quirks["RebuildAppleMemoryMap"])
        self.assertFalse(quirks["SyncRuntimePermissions"])
        self.assertTrue(quirks["SetupVirtualMap"])
        self.assertFalse(quirks["DevirtualiseMmio"])
        self.assertFalse(quirks["ProtectUefiServices"])

    def test_comet_lake_uses_its_required_memory_map_quirks(self):
        profile = HardwareProfile(
            cpu_vendor="intel",
            cpu_generation=10,
            cpu_codename="Comet Lake",
            oc_platform="Comet Lake",
            platform="desktop",
        )

        quirks = self._quirks(profile)

        self.assertFalse(quirks["EnableWriteUnprotector"])
        self.assertTrue(quirks["RebuildAppleMemoryMap"])
        self.assertTrue(quirks["SyncRuntimePermissions"])
        self.assertFalse(quirks["SetupVirtualMap"])
        self.assertTrue(quirks["DevirtualiseMmio"])
        self.assertTrue(quirks["ProtectUefiServices"])

    def test_ryzen_uses_modern_memory_map_without_broad_mmio_quirks(self):
        profile = HardwareProfile(
            cpu_vendor="amd",
            cpu_generation=11,
            cpu_codename="Zen 3",
            oc_platform="Ryzen",
            platform="desktop",
        )

        quirks = self._quirks(profile, board="B450 TOMAHAWK")

        self.assertFalse(quirks["EnableWriteUnprotector"])
        self.assertTrue(quirks["RebuildAppleMemoryMap"])
        self.assertTrue(quirks["SyncRuntimePermissions"])
        self.assertTrue(quirks["SetupVirtualMap"])
        self.assertFalse(quirks["DevirtualiseMmio"])
        self.assertFalse(quirks["ProtectUefiServices"])

    def test_b550_disables_setup_virtual_map(self):
        profile = HardwareProfile(
            cpu_vendor="amd",
            cpu_generation=11,
            cpu_codename="Zen 3",
            platform="desktop",
        )

        quirks = self._quirks(profile, board="MAG B550 TOMAHAWK")

        self.assertFalse(quirks["SetupVirtualMap"])


if __name__ == "__main__":
    unittest.main()
