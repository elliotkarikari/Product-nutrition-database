"""Legacy sampling-derived tables are kept byte for byte as they are on main."""

import hashlib
import json
import unittest
from pathlib import Path

FOLDER = Path(__file__).resolve().parent.parent / "data" / "raw" / "legacy-main-fv-sampling-tables"


class TestLegacySnapshot(unittest.TestCase):
    def test_every_file_matches_its_manifest(self):
        manifest = json.loads((FOLDER / "MANIFEST.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["commit"], "cfadc8a3f5eff7cae890ea8031d8de3ae600165f")
        listed = set()
        for entry in manifest["files"]:
            with self.subTest(path=entry["path_on_main"]):
                data = (FOLDER / entry["snapshot_path"]).read_bytes()
                self.assertEqual(hashlib.sha256(data).hexdigest(), entry["sha256"])
                blob = hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()
                self.assertEqual(blob, entry["git_blob"])
                self.assertTrue(entry["derives_from"])
                listed.add(entry["snapshot_path"])
        on_disk = {str(p.relative_to(FOLDER)) for p in FOLDER.rglob("*") if p.is_file()}
        self.assertEqual(on_disk - {"MANIFEST.json"}, listed)
        self.assertEqual(len(listed), 76)


if __name__ == "__main__":
    unittest.main()
