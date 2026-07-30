import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from kexts import DB, check_kext_sources

_AIRPORTITLWM_ASSETS = [
    {"name": "AirportItlwm_v2.3.0_stable_Sonoma14.4.kext.zip"},
    {"name": "AirportItlwm_v2.3.0_stable_Ventura.kext.zip"},
    {"name": "itlwm_v2.3.0_stable.kext.zip"},
]


class AirportItlwmSourceCheckTests(unittest.TestCase):
    def _check(self, macos_version: str) -> str:
        with patch("kexts._get_latest_release", return_value={"assets": _AIRPORTITLWM_ASSETS}):
            results, _ = check_kext_sources([DB["AirportItlwm"]], macos_version=macos_version)
        return results["AirportItlwm"]

    def test_sonoma_build_is_available(self):
        self.assertEqual(self._check("14"), "OK")

    def test_tahoe_has_no_build_and_is_reported_as_an_error_not_ok(self):
        result = self._check("26")

        self.assertTrue(result.startswith("ERROR"))
        self.assertIn("itlwm", result)

    def test_sequoia_has_no_build_and_is_reported_as_an_error_not_ok(self):
        result = self._check("15")

        self.assertTrue(result.startswith("ERROR"))

    def test_missing_macos_version_argument_does_not_silently_pass(self):
        # Regression: without macos_version, the old generic asset_pattern
        # check found *a* AirportItlwm zip (Ventura's) and reported "OK" for
        # any target, including ones with no matching build.
        result = self._check("")

        self.assertTrue(result.startswith("ERROR"))


if __name__ == "__main__":
    unittest.main()
