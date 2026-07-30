import sys
import unittest
import json
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import hardware


class DiscreteGpuPromptTests(unittest.TestCase):
    def test_optimus_laptop_gets_disable_choice(self):
        profile = hardware.HardwareProfile(
            gpu_vendor="intel",
            dgpu_vendor="nvidia",
            platform="laptop",
        )

        self.assertTrue(hardware.needs_dgpu_disable_prompt(profile))

    def test_desktop_nvidia_gets_disable_choice(self):
        profile = hardware.HardwareProfile(
            gpu_vendor="intel",
            dgpu_vendor="nvidia",
            platform="desktop",
        )

        self.assertTrue(hardware.needs_dgpu_disable_prompt(profile))

    def test_desktop_amd_stays_enabled_for_display_output(self):
        profile = hardware.HardwareProfile(
            gpu_vendor="intel",
            dgpu_vendor="amd",
            platform="desktop",
        )

        self.assertFalse(hardware.needs_dgpu_disable_prompt(profile))

class HardwareWarningTests(unittest.TestCase):
    def test_tiger_lake_laptop_warns_that_internal_graphics_are_unusable(self):
        profile = hardware.HardwareProfile(
            cpu_vendor="intel",
            cpu_generation=11,
            gpu_vendor="intel",
            gpu_name="Intel Iris Xe Graphics",
            platform="laptop",
        )

        warnings = hardware.hardware_warnings(profile)

        self.assertTrue(any("no macOS driver" in warning for warning in warnings))
        self.assertTrue(any("laptop internal displays" in warning for warning in warnings))

    def test_alder_lake_desktop_requires_supported_amd_graphics(self):
        profile = hardware.HardwareProfile(
            cpu_vendor="intel",
            cpu_generation=12,
            gpu_vendor="intel",
            gpu_name="Intel UHD Graphics 770",
            platform="desktop",
        )

        warnings = hardware.hardware_warnings(profile)

        self.assertTrue(any("supported AMD discrete GPU is required" in warning for warning in warnings))

    def test_newer_intel_desktop_with_amd_dgpu_gets_disable_igpu_guidance(self):
        profile = hardware.HardwareProfile(
            cpu_vendor="intel",
            cpu_generation=13,
            gpu_vendor="intel",
            gpu_name="Intel UHD Graphics 770",
            dgpu_vendor="amd",
            dgpu_name="AMD Radeon RX 6600",
            platform="desktop",
        )

        warnings = hardware.hardware_warnings(profile)

        self.assertTrue(any("disable it in BIOS" in warning for warning in warnings))


class IntelWifiWarningTests(unittest.TestCase):
    def test_intel_wifi_gets_broadcom_native_wifi_recommendation(self):
        profile = hardware.HardwareProfile(wifi_chipset="intel")

        warnings = hardware.hardware_warnings(profile)

        self.assertTrue(any("BCM94360CD" in warning for warning in warnings))

    def test_broadcom_wifi_does_not_get_the_recommendation(self):
        profile = hardware.HardwareProfile(wifi_chipset="broadcom")

        warnings = hardware.hardware_warnings(profile)

        self.assertFalse(any("BCM94360CD" in warning for warning in warnings))


_REAL_SP_AIRPORT_NO_CARD = """Wi-Fi:

      Software Versions:
          CoreWLAN: 16.0 (1657)
          CoreWLANKit: 16.0 (1657)
          Menu Extra: 1.0 (19150.2)
          System Information: 15.0 (1502)
          IO80211 Family: 12.0 (1200.13.1)
          Diagnostics: 11.0 (1163)
          AirPort Utility: 6.3.9 (639.29)
"""

_REAL_SP_ETHERNET_I219 = """Ethernet:

    Intel I219-V Ethernet Connection:

      Bus: PCI
      Vendor ID: 0x8086
      Device ID: 0x15d7
      Subsystem Vendor ID: 0x17aa
      Subsystem ID: 0x2258
      Revision ID: 0x0021
      Driver: com.insanelymac.IntelMausiEthernet
      BSD Device Name: en0
      MAC Address: 98:fa:9b:23:b0:b6
      AVB Support: No
      Maximum Link Speed: 1 Gb/s
"""


class MacOSNetworkDetectionTests(unittest.TestCase):
    def _sp_for(self, mapping: dict) -> callable:
        return lambda data_type: mapping.get(data_type, "")

    def test_working_i219_ethernet_is_identified_not_reported_as_none(self):
        # Regression: SPNetworkDataType lists the *service* name ("Ethernet")
        # not the chip, so this exact real-world output used to leave
        # ethernet_chipset/name empty despite the NIC working and being
        # fully identifiable from SPEthernetDataType.
        profile = hardware.HardwareProfile()
        with patch.object(hardware, "_sp", side_effect=self._sp_for({
            "SPEthernetDataType": _REAL_SP_ETHERNET_I219,
            "SPAirPortDataType": _REAL_SP_AIRPORT_NO_CARD,
        })):
            hardware._detect_network_macos(profile)

        self.assertEqual(profile.ethernet_chipset, "i219")
        self.assertIn("I219", profile.ethernet_name)

    def test_no_wifi_card_present_correctly_reports_no_wifi(self):
        profile = hardware.HardwareProfile()
        with patch.object(hardware, "_sp", side_effect=self._sp_for({
            "SPEthernetDataType": _REAL_SP_ETHERNET_I219,
            "SPAirPortDataType": _REAL_SP_AIRPORT_NO_CARD,
        })):
            hardware._detect_network_macos(profile)

        self.assertEqual(profile.wifi_chipset, "")


class MacOSAudioDetectionTests(unittest.TestCase):
    def test_virtual_blackhole_device_does_not_override_real_codec(self):
        sp = (
            "Audio:\n"
            "\n"
            "    Devices:\n"
            "\n"
            "        Realtek ALC295:\n"
            "\n"
            "        BlackHole 2ch:\n"
            "\n"
            "          Manufacturer: Existential Audio Inc.\n"
        )
        profile = hardware.HardwareProfile()
        with patch.object(hardware, "_sp", return_value=sp):
            hardware._detect_audio_macos(profile)

        self.assertEqual(profile.audio_codec, "ALC295")

    def test_virtual_only_audio_falls_back_without_claiming_a_codec(self):
        # Regression: the real SPAudioDataType output wraps devices in
        # "Audio:" / "Devices:" section headers that also end with ":" —
        # "Audio:" itself used to get matched as a fallback device name
        # before ever reaching the (correctly-filtered) BlackHole entries.
        sp = (
            "Audio:\n"
            "\n"
            "    Devices:\n"
            "\n"
            "        BlackHole 16ch:\n"
            "\n"
            "          Input Channels: 16\n"
            "          Manufacturer: Existential Audio Inc.\n"
            "          Output Channels: 16\n"
            "          Transport: Virtual\n"
            "\n"
            "        BlackHole 2ch:\n"
            "\n"
            "          Default Output Device: Yes\n"
            "          Input Channels: 2\n"
            "          Manufacturer: Existential Audio Inc.\n"
            "          Output Channels: 2\n"
            "          Transport: Virtual\n"
        )
        profile = hardware.HardwareProfile()
        with patch.object(hardware, "_sp", return_value=sp):
            hardware._detect_audio_macos(profile)

        self.assertEqual(profile.audio_codec, "")
        self.assertEqual(profile.audio_name, "")


_REAL_SP_PCI_T480S = """PCI:

    Intel UHD Graphics 620:

      Name: display
      Type: VGA compatible controller
      Driver Installed: Yes
      MSI: Yes
      Bus: PCI
      Slot: Internal@0,2,0
      Vendor ID: 0x8086
      Device ID: 0x5916
      Subsystem Vendor ID: 0x17aa
      Subsystem ID: 0x2258
      Revision ID: 0x0007
      Link Width: x0
      Link Status: Link up

    Sunrise Point-LP HD Audio:

      Name: pci8086,9d71
      Type: Audio device
      Driver Installed: No
      MSI: No
      Bus: PCI
      Slot: Internal@0,31,3
      Vendor ID: 0x8086
      Device ID: 0x9d71
      Subsystem Vendor ID: 0x17aa
      Subsystem ID: 0x2258
      Revision ID: 0x0021

    ExpressCard:

      Name: pci8086,15bf
      Type: System peripheral
      Driver Installed: Yes
      MSI: Yes
      Bus: PCI
      Slot: Internal@0,28,4/0,0/0,0/0,0
      Vendor ID: 0x8086
      Device ID: 0x15bf
      Subsystem Vendor ID: 0x2222
      Subsystem ID: 0x1111
      Revision ID: 0x0001
      Link Width: x4
      Link Speed: 2.5 GT/s
      Link Status: Link up

    ExpressCard:

      Name: pci8086,15c1
      Type: USB controller
      Driver Installed: Yes
      MSI: Yes
      Bus: PCI
      Slot: Internal@0,28,4/0,0/2,0/0,0
      Vendor ID: 0x8086
      Device ID: 0x15c1
      Subsystem Vendor ID: 0x2222
      Subsystem ID: 0x1111
      Revision ID: 0x0001
      Link Width: x4
      Link Speed: 2.5 GT/s
      Link Status: Link up
"""


class MacOSThunderboltDetectionTests(unittest.TestCase):
    def test_alpine_ridge_controller_detected_from_pci_ids_not_name(self):
        # Regression: this real ThinkPad T480s PCI dump labels the Alpine
        # Ridge Thunderbolt 3 controller "ExpressCard" (no friendly name
        # without a loaded driver) — text-matching "thunderbolt" against it
        # finds nothing, so detection has to go by Intel's known device IDs
        # (0x15bf / 0x15c1 here) instead.
        profile = hardware.HardwareProfile()
        with (
            patch.object(hardware, "_sp", side_effect=lambda dt: (
                _REAL_SP_PCI_T480S if dt == "SPPCIDataType" else ""
            )),
            patch.object(hardware, "_run", return_value=""),
        ):
            hardware._detect_platform_macos(profile)

        self.assertTrue(profile.has_thunderbolt)

    def test_machine_without_a_thunderbolt_controller_is_not_a_false_positive(self):
        profile = hardware.HardwareProfile()
        with (
            patch.object(hardware, "_sp", side_effect=lambda dt: (
                _REAL_SP_ETHERNET_I219 if dt == "SPPCIDataType" else ""
            )),
            patch.object(hardware, "_run", return_value=""),
        ):
            hardware._detect_platform_macos(profile)

        self.assertFalse(profile.has_thunderbolt)


class MacOSPCIDetectionTests(unittest.TestCase):
    def test_uses_system_profiler_instead_of_lspci(self):
        output = "Intel UHD Graphics 630:\n    Vendor ID: 0x8086"

        with (
            patch("platform.system", return_value="Darwin"),
            patch.object(hardware, "_run", return_value=output) as run,
        ):
            lines = hardware._lspci()

        run.assert_called_once_with(["system_profiler", "SPPCIDataType"])
        self.assertEqual(lines, output.splitlines())

    def test_missing_system_profiler_does_not_crash(self):
        with (
            patch("platform.system", return_value="Darwin"),
            patch.object(hardware.subprocess, "run", side_effect=FileNotFoundError),
        ):
            self.assertEqual(hardware._lspci(), [])


class WindowsNetworkDetectionTests(unittest.TestCase):
    def test_ethernet_query_selects_physical_adapter_without_name_blacklist(self):
        queries = []

        with patch.object(hardware, "_ps", side_effect=lambda query: queries.append(query) or ""):
            hardware._detect_network_windows(hardware.HardwareProfile())

        ethernet_query = queries[0]
        self.assertIn("Get-NetAdapter -Physical -ErrorAction Stop", ethernet_query)
        self.assertIn("$_.InterfaceDescription -notmatch", ethernet_query)
        self.assertNotIn("Win32_NetworkAdapter", ethernet_query)
        self.assertNotIn("$_.Name -notmatch", ethernet_query)
        for virtual_adapter_term in ("Virtual", "TAP", "VPN", "Loopback"):
            self.assertNotIn(virtual_adapter_term, ethernet_query)


class WindowsGpuDetectionTests(unittest.TestCase):
    def test_intel_device_id_follows_selected_igpu_when_dgpu_is_listed_first(self):
        controllers = [
            {
                "Name": "NVIDIA GeForce GTX 1050",
                "PNPDeviceID": r"PCI\VEN_10DE&DEV_1C8D&SUBSYS_00000000",
            },
            {
                "Name": "Intel(R) HD Graphics 630",
                "PNPDeviceID": r"PCI\VEN_8086&DEV_591B&SUBSYS_00000000",
            },
        ]
        profile = hardware.HardwareProfile()

        with patch.object(hardware, "_ps", return_value=json.dumps(controllers)):
            hardware._detect_gpu_windows(profile)

        self.assertEqual(profile.gpu_name, "Intel(R) HD Graphics 630")
        self.assertEqual(profile.gpu_vendor, "intel")
        self.assertEqual(profile.gpu_device_id, "591B")
        self.assertEqual(profile.dgpu_name, "NVIDIA GeForce GTX 1050")
        self.assertEqual(profile.dgpu_vendor, "nvidia")

    def test_gpu_names_fall_back_when_powershell_json_is_unavailable(self):
        profile = hardware.HardwareProfile()

        with patch.object(
            hardware,
            "_ps",
            side_effect=["not-json", "Intel(R) UHD Graphics 620||NVIDIA GeForce MX150"],
        ):
            hardware._detect_gpu_windows(profile)

        self.assertEqual(profile.gpu_name, "Intel(R) UHD Graphics 620")
        self.assertEqual(profile.gpu_vendor, "intel")
        self.assertEqual(profile.dgpu_name, "NVIDIA GeForce MX150")
        self.assertEqual(profile.dgpu_vendor, "nvidia")


if __name__ == "__main__":
    unittest.main()
