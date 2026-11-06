"""Which scoring law is in force: configuration, not code.

data/laws.json names each model's status. The engines (npm.py, npm2018.py)
never read it, so changing a status can change labels and the page's
"today / coming" framing but never a score. Adoption procedure:
docs/LAW_CHANGE.md.

Statuses:
- in_force: the law that applies today;
- shadow: computed beside it, not in force (a proposed or coming law);
- retired: no longer in force; still computed so past results reproduce.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

CONFIG = Path(__file__).resolve().parents[2] / "data" / "laws.json"
STATUS_TEXT = {
    "in_force": "in force",
    "shadow": "shadow model, not in force",
    "retired": "retired, no longer in force",
}
ROLE = {"in_force": "today", "shadow": "coming", "retired": "past"}


def load(path: Path = CONFIG) -> dict[str, dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    models = data.get("models")
    if not isinstance(models, dict) or not models:
        raise ValueError(f"{path}: 'models' must be a non-empty object.")
    for model_id, entry in models.items():
        if entry.get("status") not in STATUS_TEXT:
            raise ValueError(f"{path}: {model_id} status must be one of {sorted(STATUS_TEXT)}.")
        for field in ("name", "version", "guidance"):
            if not isinstance(entry.get(field), str) or not entry[field]:
                raise ValueError(f"{path}: {model_id} needs a '{field}'.")
    if sum(1 for e in models.values() if e["status"] == "in_force") > 1:
        raise ValueError(f"{path}: at most one model can be in force.")
    return models


@lru_cache(maxsize=1)
def models() -> dict[str, dict[str, Any]]:
    return load()


def status_text(model_id: str) -> str:
    return STATUS_TEXT[models()[model_id]["status"]]


def label(model_id: str) -> dict[str, Any]:
    """The law a score was given under, quotable on its own."""
    entry = models()[model_id]
    return {
        "model": model_id,
        "name": entry["name"],
        "version": entry["version"],
        "status": entry["status"],
        "status_text": STATUS_TEXT[entry["status"]],
        "role": ROLE[entry["status"]],
        "guidance": entry["guidance"],
        **({"note": entry["note"]} if entry.get("note") else {}),
    }


def summary() -> dict[str, str]:
    return {model_id: status_text(model_id) for model_id in models()}
