import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import pci_disable


def _device(name: str, adr: int | None = None, children: bytes = b"") -> bytes:
    name_b = name.encode("ascii")
    assert len(name_b) == 4
    body = b""
    if adr is not None:
        body += b"\x08_ADR" + b"\x0c" + adr.to_bytes(4, "little")
    body += children
    after_pkglen = name_b + body
    pkg_len = 1 + len(after_pkglen)
    assert pkg_len <= 0x3F
    return b"\x5b\x82" + bytes([pkg_len]) + after_pkglen


class PkgLengthAndIntegerDecodeTests(unittest.TestCase):
    def test_single_byte_pkglen(self):
        self.assertEqual(pci_disable._decode_pkglen(bytes([0x0A]), 0), (0x0A, 1))

    def test_two_byte_pkglen(self):
        data = bytes([0b01000101, 0x02])
        self.assertEqual(pci_disable._decode_pkglen(data, 0), (0x25, 2))

    def test_zero_op_integer(self):
        self.assertEqual(pci_disable._decode_integer(b"\x00", 0), (0, 1))

    def test_dword_prefix_integer(self):
        data = b"\x0c" + (0x001C0000).to_bytes(4, "little")
        self.assertEqual(pci_disable._decode_integer(data, 0), (0x001C0000, 5))

    def test_invalid_nameseg_rejected(self):
        self.assertFalse(pci_disable._is_valid_nameseg(b"1BAD"))
        self.assertTrue(pci_disable._is_valid_nameseg(b"PCI0"))
        self.assertTrue(pci_disable._is_valid_nameseg(b"_SB_"))


class FindDevicePathTests(unittest.TestCase):
    def test_finds_top_level_device_by_adr(self):
        adr = (0x1C << 16) | 0
        data = _device("WIFI", adr=adr)

        path = pci_disable.find_device_path_by_pci_address(data, 0x1C, 0)
        self.assertEqual(path, "_SB.WIFI")

    def test_finds_nested_device_with_full_hierarchical_path(self):
        pxsx = _device("PXSX", adr=0)
        rp05 = _device("RP05", adr=(0x1C << 16), children=pxsx)
        pci0 = _device("PCI0", adr=0, children=rp05)

        path = pci_disable.find_device_path_by_pci_address(pci0, 0, 0)
        self.assertIsNone(path)

    def test_finds_unambiguous_nested_device(self):
        pxsx = _device("PXSX", adr=0)
        rp05 = _device("RP05", adr=(0x1C << 16), children=pxsx)
        pci0 = _device("PCI0", children=rp05)

        path = pci_disable.find_device_path_by_pci_address(pci0, 0x1C, 0)
        self.assertEqual(path, "_SB.PCI0.RP05")

        path2 = pci_disable.find_device_path_by_pci_address(pci0, 0, 0)
        self.assertEqual(path2, "_SB.PCI0.RP05.PXSX")

    def test_ambiguous_match_refuses_to_guess(self):
        dev_a = _device("DEVA", adr=0x99)
        dev_b = _device("DEVB", adr=0x99)
        data = dev_a + dev_b

        path = pci_disable.find_device_path_by_pci_address(data, 0, 0x99)
        self.assertIsNone(path)

    def test_no_match_returns_none(self):
        data = _device("WIFI", adr=0x001C0000)
        path = pci_disable.find_device_path_by_pci_address(data, 0x1D, 0)
        self.assertIsNone(path)

    def test_empty_data_returns_none_not_a_crash(self):
        self.assertIsNone(pci_disable.find_device_path_by_pci_address(b"", 0x1C, 0))


class BuildDisableSsdtTests(unittest.TestCase):
    def test_generated_dsl_targets_the_right_device_and_forces_sta_zero(self):
        dsl = pci_disable.build_disable_ssdt("_SB.PCI0.RP05.PXSX", table_id="WIFI")

        self.assertIn("External (_SB.PCI0.RP05.PXSX, DeviceObj)", dsl)
        self.assertIn("Scope (_SB.PCI0.RP05.PXSX)", dsl)
        self.assertIn("Method (_STA, 0, NotSerialized)", dsl)
        self.assertIn("Return (Zero)", dsl)
        self.assertIn('"WIFI"', dsl)


if __name__ == "__main__":
    unittest.main()
