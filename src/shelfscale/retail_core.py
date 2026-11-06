"""The author's retail-shaped CoFID list (2023): which foods are sold, and how.

Read from data/raw/legacy-retail-core-2023 after a checksum check. Only the
CoFID food code and the sale format are used; names and values come from
CoFID 2021. Rows without a code that resolves to one CoFID food are skipped
and counted.

Loose rule: a sale format that names a loose or counter sale ("loose",
"counter", "bunch", "fresh produce", "fresh bakery") means the food is sold
without a pack and without a declared weight.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

SNAPSHOT = Path(__file__).resolve().parents[2] / "data" / "raw" / "legacy-retail-core-2023"
LOOSE = re.compile(r"\b(loose|counter|bunch|bunched|fresh produce|fresh bakery)\b", re.IGNORECASE)


def _release() -> tuple[dict[str, Any], bytes]:
    manifest = json.loads((SNAPSHOT / "MANIFEST.json").read_text(encoding="utf-8"))
    entry = manifest["files"][0]
    raw = (SNAPSHOT / entry["name"]).read_bytes()
    if hashlib.sha256(raw).hexdigest() != entry["sha256"]:
        raise ValueError(f"{entry['name']} does not match MANIFEST.json. Refusing to read it.")
    return manifest, raw


@lru_cache(maxsize=1)
def retail_core() -> dict[str, Any]:
    """{food_code: {sale_format, loose}} plus counts and provenance."""
    from .lookup import _index
    manifest, raw = _release()
    by_code = _index()[0]
    foods: dict[str, dict[str, Any]] = {}
    skipped = 0
    for row in csv.DictReader(io.StringIO(raw.decode("utf-8"))):
        code = (row.get("Food Code") or "").strip()
        if len(by_code.get(code, [])) != 1:
            skipped += 1
            continue
        fmt = " ".join((row.get("Sale format(s)") or "").split())
        foods[code] = {"sale_format": fmt or None, "loose": bool(LOOSE.search(fmt))}
    return {
        "foods": foods,
        "skipped_rows": skipped,
        "source": {"label": "Author's retail list, 2023", "dataset": manifest["dataset"],
                   "citation": manifest["citation"], "rights": manifest["rights"],
                   "url": manifest["url"], "use": manifest["use"]},
    }


def sale_info(food_code: str) -> dict[str, Any] | None:
    core = retail_core()
    entry = core["foods"].get(food_code)
    if entry is None:
        return None
    return {**entry, "source": core["source"]}
