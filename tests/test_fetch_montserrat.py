import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.fetch_montserrat import DownloadSpec, fetch_source


class FetchMontserratTests(unittest.TestCase):
    def test_fetches_and_verifies_source(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            source_path = root / "source.ttf"
            source_path.write_bytes(b"pinned font data")
            expected = hashlib.sha256(source_path.read_bytes()).hexdigest()
            source = DownloadSpec("font.ttf", source_path.as_uri(), expected)

            self.assertTrue(fetch_source(source, root / "output"))
            self.assertEqual(
                (root / "output" / "font.ttf").read_bytes(),
                b"pinned font data",
            )

    def test_reuses_verified_cached_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_dir = root / "output"
            output_dir.mkdir()
            destination = output_dir / "font.ttf"
            destination.write_bytes(b"verified")
            expected = hashlib.sha256(destination.read_bytes()).hexdigest()
            source = DownloadSpec("font.ttf", "file:///does-not-exist", expected)

            self.assertFalse(fetch_source(source, output_dir))

    def test_checksum_failure_preserves_existing_file(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory)
            output_dir = root / "output"
            output_dir.mkdir()
            destination = output_dir / "font.ttf"
            destination.write_bytes(b"old cache")
            source_path = root / "source.ttf"
            source_path.write_bytes(b"unexpected data")
            source = DownloadSpec("font.ttf", source_path.as_uri(), "0" * 64)

            with self.assertRaisesRegex(RuntimeError, "Checksum mismatch"):
                fetch_source(source, output_dir)
            self.assertEqual(destination.read_bytes(), b"old cache")


if __name__ == "__main__":
    unittest.main()
