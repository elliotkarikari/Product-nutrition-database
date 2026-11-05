"""No content from the _VJ files on main, or the reviewer's comments, is in this branch.

Elliot's instruction (November 5, 2026): the three _VJ files on main
(FPS_VJ.csv, FPS_VJ (version 1).csv, Processed_Food_Portion_Sizes_VJ.csv)
are not sources, and their content and the reviewer's comments are never
copied, quoted or published in this project. vj_fingerprints.json holds
sha256 hashes only, so this test publishes nothing it checks for.
"""

import csv
import hashlib
import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FINGERPRINTS = json.loads((Path(__file__).parent / "vj_fingerprints.json").read_text())
TEXT_SUFFIXES = {".csv", ".json", ".md", ".yaml", ".yml", ".txt", ".py", ".toml"}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def fragments(text: str):
    """Every CSV cell, and every piece between |, quotes and backticks, of every line."""
    for line in text.splitlines():
        yield line
        try:
            yield from next(csv.reader([line]))
        except (csv.Error, StopIteration):
            pass
        yield from re.split(r'[|"`]', line)


def matches(path: Path, cell_hashes: set[str], file_hashes: set[str]) -> set[str]:
    raw = path.read_bytes()
    found = set()
    if hashlib.sha256(raw).hexdigest() in file_hashes:
        found.add("whole file")
    if path.suffix.lower() in TEXT_SUFFIXES:
        try:
            text = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = raw.decode("cp1252", errors="replace")
        for fragment in fragments(text):
            digest = hashlib.sha256(_norm(fragment).encode()).hexdigest()
            if digest in cell_hashes:
                found.add(digest)
    return found


class TestNoVJContent(unittest.TestCase):
    def test_no_vj_content_anywhere_in_the_branch(self):
        cells = set(FINGERPRINTS["cell_sha256"])
        files = set(FINGERPRINTS["file_sha256"])
        self.assertGreater(len(cells), 0)
        hits = {}
        for path in ROOT.rglob("*"):
            if not path.is_file() or ".git" in path.parts or "__pycache__" in path.parts:
                continue
            if path.name == "vj_fingerprints.json":
                continue
            found = matches(path, cells, files)
            if found:
                hits[str(path.relative_to(ROOT))] = len(found)
        self.assertEqual(hits, {})


if __name__ == "__main__":
    unittest.main()
