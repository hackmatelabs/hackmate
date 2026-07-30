import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import compat


class PeBinaryValidationTests(unittest.TestCase):
    # Regression, reported live: HfsPlus.efi was fetched from an unpinned
    # raw-GitHub URL with no size or header check — a truncated/corrupted
    # response got written straight into EFI/OC/Drivers/, and OpenCore hung
    # loading it at boot, before the picker ever appeared.
    def test_rejects_data_smaller_than_min_size(self):
        data = b"MZ" + b"\x00" * 100
        self.assertFalse(compat.is_valid_pe_binary(data, min_size=50 * 1024))

    def test_rejects_data_without_pe_header(self):
        data = b"<html>404 not found</html>" + b"\x00" * (60 * 1024)
        self.assertFalse(compat.is_valid_pe_binary(data, min_size=50 * 1024))

    def test_accepts_large_data_with_valid_pe_header(self):
        data = b"MZ" + b"\x00" * (60 * 1024)
        self.assertTrue(compat.is_valid_pe_binary(data, min_size=50 * 1024))

    def test_empty_response_is_rejected_not_a_crash(self):
        self.assertFalse(compat.is_valid_pe_binary(b"", min_size=50 * 1024))


if __name__ == "__main__":
    unittest.main()
