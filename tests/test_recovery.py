import sys
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from recovery import compatible_versions


class RecoveryCompatibilityTests(unittest.TestCase):
    def _versions(
        self,
        cpu_gen: int,
        cpu_vendor: str = "intel",
        cpu_codename: str = "",
        gpu_vendor: str = "amd",
        gpu_name: str = "",
    ) -> list[str]:
        return [
            version.version
            for version in compatible_versions(
                cpu_gen,
                gpu_vendor,
                cpu_vendor,
                cpu_codename,
                gpu_name,
            )
        ]

    def test_skylake_is_not_offered_pre_skylake_installers(self):
        versions = self._versions(6)

        self.assertIn("10.11", versions)
        self.assertNotIn("10.10", versions)

    def test_coffee_lake_starts_with_high_sierra(self):
        versions = self._versions(8)

        self.assertIn("10.13", versions)
        self.assertNotIn("10.12", versions)

    def test_comet_lake_starts_with_catalina(self):
        versions = self._versions(10)

        self.assertIn("10.15", versions)
        self.assertNotIn("10.14", versions)

    def test_spoofed_newer_intel_starts_with_big_sur(self):
        versions = self._versions(13)

        self.assertIn("11", versions)
        self.assertNotIn("10.15", versions)

    def test_zen_4_starts_with_ventura(self):
        versions = self._versions(12, "amd", "Zen 4")

        self.assertIn("13", versions)
        self.assertNotIn("12", versions)

    def test_unknown_modern_amd_uses_generation_fallback(self):
        versions = self._versions(12, "amd")

        self.assertIn("13", versions)
        self.assertNotIn("12", versions)

    def test_zen_5_starts_with_sequoia(self):
        versions = self._versions(12, "amd", "Zen 5")

        self.assertIn("15", versions)
        self.assertNotIn("14", versions)

    def test_pascal_nvidia_stops_at_high_sierra(self):
        versions = self._versions(
            8,
            gpu_vendor="nvidia",
            gpu_name="NVIDIA GeForce GTX 1080",
        )

        self.assertEqual(["10.13"], versions)

    def test_kepler_nvidia_stops_at_big_sur(self):
        versions = self._versions(
            4,
            gpu_vendor="nvidia",
            gpu_name="NVIDIA GeForce GTX 770",
        )

        self.assertIn("11", versions)
        self.assertNotIn("12", versions)

    def test_unknown_nvidia_stops_at_high_sierra(self):
        versions = self._versions(6, gpu_vendor="nvidia")

        self.assertIn("10.13", versions)
        self.assertNotIn("10.14", versions)

    def test_modern_nvidia_has_no_accelerated_macos_release(self):
        versions = self._versions(
            12,
            gpu_vendor="nvidia",
            gpu_name="NVIDIA GeForce RTX 3060",
        )

        self.assertEqual([], versions)
