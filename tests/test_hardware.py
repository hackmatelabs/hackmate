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
