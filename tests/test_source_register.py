"""The source register and docs/DATA_SOURCES.md must name the same sources."""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def register_ids():
    text = (ROOT / "data" / "source-register.yaml").read_text(encoding="utf-8")
    return re.findall(r"^  - id: (\S+)$", text, flags=re.MULTILINE)


def doc_ids():
    text = (ROOT / "docs" / "DATA_SOURCES.md").read_text(encoding="utf-8")
    return re.findall(r"^\| `([^`]+)` \|", text, flags=re.MULTILINE)


class TestSourceRegister(unittest.TestCase):
    def test_register_and_doc_name_the_same_sources(self):
        register, doc = register_ids(), doc_ids()
        self.assertEqual(len(register), len(set(register)), "duplicate register id")
        self.assertEqual(len(doc), len(set(doc)), "duplicate doc id")
        self.assertEqual(set(register), set(doc))

    def test_every_entry_has_licence_fields(self):
        text = (ROOT / "data" / "source-register.yaml").read_text(encoding="utf-8")
        entries = re.split(r"^  - id: ", text, flags=re.MULTILINE)[1:]
        for entry in entries:
            source_id = entry.split("\n", 1)[0]
            with self.subTest(source=source_id):
                for field in ("commercial_use:", "redistribution:",
                              "attribution_required:", "status:"):
                    self.assertIn(field, entry)


if __name__ == "__main__":
    unittest.main()
