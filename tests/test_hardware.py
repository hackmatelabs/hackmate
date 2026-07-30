import sys
import unittest
import json
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import hardware


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
