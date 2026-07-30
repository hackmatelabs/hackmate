import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import config_editor


def _cfg_with_kexts():
    return {
        "Kernel": {
            "Add": [
                {"BundlePath": "Lilu.kext", "Enabled": True},
                {"BundlePath": "WhateverGreen.kext", "Enabled": True},
                {"BundlePath": "UTBMap.kext", "Enabled": False},
            ]
        }
    }


def _cfg_with_acpi():
    return {
        "ACPI": {
            "Add": [
                {"Path": "SSDT-PLUG.aml", "Enabled": True},
                {"Path": "SSDT-EC.aml", "Enabled": True},
            ]
        }
    }


class KextEntryTests(unittest.TestCase):
    def test_lists_all_kexts_with_enabled_state(self):
        entries = config_editor.get_kext_entries(_cfg_with_kexts())
        self.assertIn(("Lilu", True), entries)
        self.assertIn(("UTBMap", False), entries)

    def test_set_kext_enabled_toggles_the_right_entry(self):
        cfg = _cfg_with_kexts()
        found = config_editor.set_kext_enabled(cfg, "UTBMap", True)
        self.assertTrue(found)
        entries = dict(config_editor.get_kext_entries(cfg))
        self.assertTrue(entries["UTBMap"])
        self.assertTrue(entries["Lilu"])

    def test_set_kext_enabled_unknown_name_returns_false(self):
        cfg = _cfg_with_kexts()
        self.assertFalse(config_editor.set_kext_enabled(cfg, "DoesNotExist", True))

    def test_empty_config_returns_empty_list_not_a_crash(self):
        self.assertEqual(config_editor.get_kext_entries({}), [])


class AcpiEntryTests(unittest.TestCase):
    def test_lists_all_acpi_adds_with_enabled_state(self):
        entries = config_editor.get_acpi_entries(_cfg_with_acpi())
        self.assertIn(("SSDT-PLUG", True), entries)
        self.assertIn(("SSDT-EC", True), entries)

    def test_set_acpi_entry_enabled_toggles_the_right_entry(self):
        cfg = _cfg_with_acpi()
        found = config_editor.set_acpi_entry_enabled(cfg, "SSDT-PLUG", False)
        self.assertTrue(found)
        entries = dict(config_editor.get_acpi_entries(cfg))
        self.assertFalse(entries["SSDT-PLUG"])
        self.assertTrue(entries["SSDT-EC"])

    def test_set_acpi_entry_enabled_unknown_name_returns_false(self):
        cfg = _cfg_with_acpi()
        self.assertFalse(config_editor.set_acpi_entry_enabled(cfg, "SSDT-GHOST", False))


class SerialInfoTests(unittest.TestCase):
    def test_reads_serial_mlb_uuid_rom(self):
        cfg = {
            "PlatformInfo": {
                "Generic": {
                    "SystemSerialNumber": "C02ABC123XYZ",
                    "MLB": "C02ABC123XYZ12345",
                    "SystemUUID": "12345678-1234-1234-1234-123456789012",
                    "ROM": bytes.fromhex("001122334455"),
                }
            }
        }
        info = config_editor.get_serial_info(cfg)
        self.assertEqual(info["serial"], "C02ABC123XYZ")
        self.assertEqual(info["mlb"], "C02ABC123XYZ12345")
        self.assertEqual(info["rom"], "001122334455")

    def test_missing_platform_info_returns_empty_strings_not_a_crash(self):
        info = config_editor.get_serial_info({})
        self.assertEqual(info["serial"], "")
        self.assertEqual(info["rom"], "")

    def test_set_serial_info_writes_all_fields(self):
        cfg = {}
        config_editor.set_serial_info(
            cfg, serial="NEWSERIAL123", mlb="NEWMLB123456789", uuid="ABCDEF00-0000-0000-0000-000000000000",
            rom="aabbccddeeff",
        )
        info = config_editor.get_serial_info(cfg)
        self.assertEqual(info["serial"], "NEWSERIAL123")
        self.assertEqual(info["mlb"], "NEWMLB123456789")
        self.assertEqual(info["rom"], "aabbccddeeff")

    def test_set_serial_info_partial_update_does_not_clear_other_fields(self):
        cfg = {"PlatformInfo": {"Generic": {"SystemSerialNumber": "KEEPME", "MLB": "KEEPTOO"}}}
        config_editor.set_serial_info(cfg, uuid="ABCDEF00-0000-0000-0000-000000000000")
        info = config_editor.get_serial_info(cfg)
        self.assertEqual(info["serial"], "KEEPME")
        self.assertEqual(info["mlb"], "KEEPTOO")
        self.assertEqual(info["uuid"], "ABCDEF00-0000-0000-0000-000000000000")

    def test_set_serial_info_accepts_colon_separated_rom(self):
        cfg = {}
        config_editor.set_serial_info(cfg, rom="aa:bb:cc:dd:ee:ff")
        self.assertEqual(config_editor.get_serial_info(cfg)["rom"], "aabbccddeeff")


if __name__ == "__main__":
    unittest.main()
