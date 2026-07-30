import shutil
import sys
import tempfile
import unittest
from dataclasses import dataclass, field
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import build_history


@dataclass
class _FakeProfile:
    cpu_name: str = "Intel(R) Core(TM) i7-8700K"
    cpu_vendor: str = "intel"
    core_count: int = 6
    raw_pci: list = field(default_factory=lambda: ["some", "debug", "lines"])


class BuildHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="hackmate-test-history-"))
        self.patcher = patch.object(build_history, "HISTORY_DIR", self.tmp_dir)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_save_and_list_round_trips(self):
        build_history.save_build(
            profile=_FakeProfile(),
            macos_version="Sequoia",
            config_path=Path("/tmp/config.plist"),
            wifi_kext_mode="itlwm",
            dual_boot="none",
        )

        builds = build_history.list_builds()
        self.assertEqual(len(builds), 1)
        self.assertEqual(builds[0]["macos_version"], "Sequoia")
        self.assertEqual(builds[0]["hardware"]["cpu_name"], "Intel(R) Core(TM) i7-8700K")
        # non-scalar debug fields (raw_pci) shouldn't bloat the saved record
        self.assertNotIn("raw_pci", builds[0]["hardware"])

    def test_list_is_newest_first(self):
        import time
        first = build_history.save_build(profile=_FakeProfile(), macos_version="Monterey")
        time.sleep(0.01)
        build_history.save_build(profile=_FakeProfile(), macos_version="Sequoia")

        builds = build_history.list_builds()
        self.assertEqual(builds[0]["macos_version"], "Sequoia")
        self.assertEqual(builds[1]["macos_version"], "Monterey")
        self.assertTrue(first.exists())

    def test_empty_history_dir_returns_empty_list_not_a_crash(self):
        self.assertEqual(build_history.list_builds(), [])

    def test_corrupt_entry_is_skipped_not_fatal(self):
        build_history.save_build(profile=_FakeProfile(), macos_version="Sequoia")
        (self.tmp_dir / "corrupt.json").write_text("{not valid json")

        builds = build_history.list_builds()
        self.assertEqual(len(builds), 1)

    def test_get_build_by_id(self):
        dest = build_history.save_build(profile=_FakeProfile(), macos_version="Ventura")
        entry_id = dest.stem

        record = build_history.get_build(entry_id)
        self.assertIsNotNone(record)
        self.assertEqual(record["macos_version"], "Ventura")

    def test_get_missing_build_returns_none(self):
        self.assertIsNone(build_history.get_build("does-not-exist"))

    def test_delete_build(self):
        dest = build_history.save_build(profile=_FakeProfile(), macos_version="Big Sur")
        entry_id = dest.stem

        self.assertTrue(build_history.delete_build(entry_id))
        self.assertIsNone(build_history.get_build(entry_id))

    def test_delete_missing_build_returns_false(self):
        self.assertFalse(build_history.delete_build("does-not-exist"))

    def test_save_with_no_profile_does_not_crash(self):
        dest = build_history.save_build(macos_version="Sonoma")
        record = build_history.get_build(dest.stem)
        self.assertEqual(record["hardware"], {})


if __name__ == "__main__":
    unittest.main()
