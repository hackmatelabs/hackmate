import sys
import unittest
from pathlib import Path
from unittest.mock import patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import kexts
from kexts import DB, check_kext_sources, alc_layout_is_known, get_alc_layout, fetch_opencore, OPENCORE_FALLBACK_URL
from hardware import HardwareProfile

_AIRPORTITLWM_ASSETS = [
    {"name": "AirportItlwm_v2.3.0_stable_Sonoma14.4.kext.zip"},
    {"name": "AirportItlwm_v2.3.0_stable_Ventura.kext.zip"},
    {"name": "itlwm_v2.3.0_stable.kext.zip"},
]


class CpuTopologyRebuildSelectionTests(unittest.TestCase):
    def test_amd_zen4_does_not_get_intel_topology_kext(self):
        profile = HardwareProfile(
            cpu_vendor="amd",
            cpu_generation=12,
            cpu_codename="Zen 4",
            platform="desktop",
        )
        with (
            patch.object(kexts, "_dmi", return_value=""),
            patch.object(kexts, "_has_card_reader", return_value=False),
        ):
            names = {entry.name for entry in kexts.select_kexts(profile)}

        self.assertNotIn("CpuTopologyRebuild", names)


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
        result = self._check("")

        self.assertTrue(result.startswith("ERROR"))


class AlcLayoutConfidenceTests(unittest.TestCase):
    def test_known_codec_is_confirmed(self):
        self.assertTrue(alc_layout_is_known("ALC897"))

    def test_generic_realtek_string_is_not_confirmed(self):
        self.assertFalse(alc_layout_is_known("Realtek"))
        self.assertEqual(get_alc_layout("Realtek"), 1)

    def test_unrecognized_alc_model_is_not_confirmed(self):
        self.assertFalse(alc_layout_is_known("ALC1200"))


class OpenCoreDebugBuildTests(unittest.TestCase):
    def test_fallback_url_points_at_debug_not_release(self):
        self.assertIn("DEBUG", OPENCORE_FALLBACK_URL)
        self.assertNotIn("RELEASE", OPENCORE_FALLBACK_URL)

    def test_picks_the_debug_asset_from_the_release_list(self):
        assets = [
            {"name": "OpenCore-1.0.7-RELEASE.zip", "browser_download_url": "http://x/release.zip", "size": 1000},
            {"name": "OpenCore-1.0.7-DEBUG.zip", "browser_download_url": "http://x/debug.zip", "size": 15},
        ]
        with (
            patch.object(kexts, "_github_headers", return_value={}),
            patch("kexts.http_get") as http_get,
        ):
            import json as _json
            http_get.side_effect = [
                _json.dumps({"assets": assets}).encode(),
                b"debug-zip-bytes",
            ]
            path = fetch_opencore(Path("/tmp"))

        try:
            second_call_url = http_get.call_args_list[1].args[0]
            self.assertIn("debug.zip", second_call_url)
        finally:
            path.unlink(missing_ok=True)
            cached = kexts._CACHE_ROOT / "opencore" / "OpenCore-1.0.7-DEBUG.zip"
            cached.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
