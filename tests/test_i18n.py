import sys
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import i18n


class I18nTests(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path(tempfile.mkdtemp(prefix="hackmate-test-i18n-"))
        self.config_path = self.tmp_dir / "settings.json"
        self.patcher = patch.object(i18n, "_CONFIG_PATH", self.config_path)
        self.patcher.start()
        i18n._current_language = None

    def tearDown(self):
        self.patcher.stop()
        i18n._current_language = None
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_default_language_is_english(self):
        self.assertEqual(i18n.get_language(), "en")

    def test_set_language_persists_across_cache_reset(self):
        i18n.set_language("es")
        i18n._current_language = None
        self.assertEqual(i18n.get_language(), "es")

    def test_set_invalid_language_falls_back_to_english(self):
        i18n.set_language("klingon")
        self.assertEqual(i18n.get_language(), "en")

    def test_translation_lookup_matches_selected_language(self):
        i18n.set_language("es")
        self.assertEqual(i18n.t("welcome.quit"), "Salir")

    def test_missing_key_falls_back_to_key_itself(self):
        self.assertEqual(i18n.t("does.not.exist"), "does.not.exist")

    def test_every_english_key_has_a_translation_in_every_language(self):
        en_keys = set(i18n._STRINGS["en"].keys())
        for lang in i18n._LANGUAGES:
            if lang == "en":
                continue
            missing = en_keys - set(i18n._STRINGS[lang].keys())
            self.assertEqual(missing, set(), f"{lang} is missing keys: {missing}")

    def test_corrupt_settings_file_falls_back_to_english_not_a_crash(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text("{not valid json")
        self.assertEqual(i18n.get_language(), "en")

    def test_available_languages_includes_all_supported(self):
        codes = {code for code, _ in i18n.available_languages()}
        self.assertEqual(codes, set(i18n._LANGUAGES))


if __name__ == "__main__":
    unittest.main()
