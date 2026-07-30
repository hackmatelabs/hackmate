import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import ssdt

_ACPI0007_DSDT = (
    b"DSDT\x00\x00\x00\x00...Device (C000)\n"
    b"{\n    Name (_HID, \"ACPI0007\")\n}\n"
)
_LEGACY_DSDT = b"DSDT\x00\x00\x00\x00...Processor (PR00, 0x00, 0x00000410, 0x06)\n"


class Acpi0007DetectionTests(unittest.TestCase):
    def _inspect(self, raw: bytes) -> dict:
        with tempfile.NamedTemporaryFile(suffix=".aml") as f:
            f.write(raw)
            f.flush()
            return ssdt._inspect_dsdt(Path(f.name))

    def test_detects_acpi0007_cpu_objects(self):
        self.assertTrue(self._inspect(_ACPI0007_DSDT)["has_acpi0007"])

    def test_legacy_dsdt_without_acpi0007_is_not_flagged(self):
        self.assertFalse(self._inspect(_LEGACY_DSDT)["has_acpi0007"])


class Acpi0007PlugFallbackTests(unittest.TestCase):
    def setUp(self):
        self.acpi_dir = Path(tempfile.mkdtemp(prefix="hackmate-test-acpi-"))
        self.dsdt_file = Path(tempfile.mkdtemp(prefix="hackmate-test-dsdt-")) / "DSDT.aml"

    def tearDown(self):
        shutil.rmtree(self.acpi_dir, ignore_errors=True)
        shutil.rmtree(self.dsdt_file.parent, ignore_errors=True)

    def _generate(self, dsdt_bytes: bytes) -> dict:
        self.dsdt_file.write_bytes(dsdt_bytes)
        with (
            patch.object(ssdt, "_ensure_ssdttime", side_effect=Exception("SSDTTime unavailable")),
            patch.object(ssdt, "get_dsdt", return_value=self.dsdt_file),
        ):
            return ssdt.generate(
                needed=["SSDT-PLUG"],
                acpi_dir=self.acpi_dir,
                tmp=self.dsdt_file.parent,
                cpu_generation=8,
            )

    def test_acpi0007_with_no_ssdttime_reports_error_not_a_silent_wrong_ssdt(self):
        results = self._generate(_ACPI0007_DSDT)

        self.assertTrue(results["SSDT-PLUG"].startswith("ERROR"))
        self.assertIn("ACPI0007", results["SSDT-PLUG"])
        self.assertFalse((self.acpi_dir / "SSDT-PLUG.aml").exists())

    def test_legacy_dsdt_still_gets_a_template_generated_ssdt_plug(self):
        results = self._generate(_LEGACY_DSDT)

        self.assertFalse(results["SSDT-PLUG"].startswith("ERROR"))


class UnknownDsdtPlugSafetyTests(unittest.TestCase):
    def setUp(self):
        self.acpi_dir = Path(tempfile.mkdtemp(prefix="hackmate-test-acpi-"))
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="hackmate-test-tmp-"))

    def tearDown(self):
        shutil.rmtree(self.acpi_dir, ignore_errors=True)
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_no_dsdt_at_all_reports_error_instead_of_guessing_ssdt_plug(self):
        with (
            patch.object(ssdt, "_ensure_ssdttime", side_effect=Exception("SSDTTime unavailable")),
            patch.object(ssdt, "get_dsdt", return_value=None),
        ):
            results = ssdt.generate(
                needed=["SSDT-PLUG"],
                acpi_dir=self.acpi_dir,
                tmp=self.tmp_dir,
                cpu_generation=8,
            )

        self.assertTrue(results["SSDT-PLUG"].startswith("ERROR"))
        self.assertFalse((self.acpi_dir / "SSDT-PLUG.aml").exists())


class FrozenAssetsPathTests(unittest.TestCase):
    def test_source_checkout_uses_the_real_assets_directory(self):
        with patch.object(sys, "frozen", False, create=True):
            path = ssdt._assets_dir()

        self.assertEqual(path, Path(ssdt.__file__).parent / "assets" / "acpi")
        self.assertTrue(path.exists(), "src/assets/acpi should exist in the repo")

    def test_frozen_exe_uses_meipass_not_file_parent(self):
        with (
            patch.object(sys, "frozen", True, create=True),
            patch.object(sys, "_MEIPASS", "/fake/meipass/dir", create=True),
        ):
            path = ssdt._assets_dir()

        self.assertEqual(path, Path("/fake/meipass/dir") / "assets" / "acpi")


if __name__ == "__main__":
    unittest.main()
