import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pci_ids


class PciIdsParsingTests(unittest.TestCase):
    def test_bundled_pci_ids_file_exists(self):
        self.assertTrue((pci_ids._DATA / "pci.ids").exists())

    def test_bundled_usb_ids_file_exists(self):
        self.assertTrue((pci_ids._DATA / "usb.ids").exists())

    def test_intel_vendor_name_resolves(self):
        self.assertEqual(pci_ids.pci_vendor_name("8086"), "Intel Corporation")

    def test_amd_vendor_name_resolves(self):
        name = pci_ids.pci_vendor_name("1002")
        self.assertIn("Advanced Micro Devices", name)

    def test_vendor_lookup_is_case_insensitive(self):
        self.assertEqual(pci_ids.pci_vendor_name("8086"), pci_ids.pci_vendor_name("8086".upper()))

    def test_unknown_vendor_returns_none_not_a_crash(self):
        with open(pci_ids._DATA / "pci.ids", encoding="utf-8", errors="replace") as f:
            known_ids = {line[:4].lower() for line in f if line[:1].isalnum()}
        # 0000 is reserved/never assigned in the PCI-SIG database.
        self.assertNotIn("0000", known_ids)
        self.assertIsNone(pci_ids.pci_vendor_name("0000"))

    def test_unknown_device_returns_none_not_a_crash(self):
        self.assertIsNone(pci_ids.pci_device_name("8086", "0000"))

    def test_usb_intel_vendor_name_resolves(self):
        self.assertEqual(pci_ids.usb_vendor_name("8086"), "Intel Corp.")

    def test_device_lookup_needs_matching_vendor(self):
        # a real device id under the wrong vendor id must not match
        self.assertIsNone(pci_ids.pci_device_name("1002", "1234abcd"))


class ParseIdsFileUnitTests(unittest.TestCase):
    def test_parses_minimal_synthetic_file(self):
        import tempfile
        content = (
            "# comment\n"
            "0001  Vendor One\n"
            "\tabcd  Device A\n"
            "\t\t0001 abcd  Subsystem — ignored\n"
            "0002  Vendor Two\n"
            "\tdead  Device B\n"
            "C 00  Unclassified device\n"
            "\t00  Non-VGA\n"
        )
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ids", delete=False) as f:
            f.write(content)
            path = Path(f.name)
        try:
            parsed = pci_ids._parse_ids_file(path)
            self.assertEqual(parsed["0001"][0], "Vendor One")
            self.assertEqual(parsed["0001"][1]["abcd"], "Device A")
            self.assertEqual(parsed["0002"][0], "Vendor Two")
            self.assertEqual(parsed["0002"][1]["dead"], "Device B")
            # class section lines must not leak into vendor data
            self.assertNotIn("c 00", parsed)
        finally:
            path.unlink()

    def test_missing_file_returns_empty_dict_not_a_crash(self):
        self.assertEqual(pci_ids._parse_ids_file(Path("/nonexistent/path.ids")), {})


if __name__ == "__main__":
    unittest.main()
