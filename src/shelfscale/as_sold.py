"""Products as sold: the unit a person buys, with the evidence for its weight.

ShelfScale scores products as sold (memory/decisions/product-direction.md).
The per-100 g verdict never moves; this module adds the unit view:

- packaged: the declared pack weight, when the user gives it;
- loose: the typical unit weight from the project's own evidence, with its
  real range where the sampling reports give one, and the per-unit figures
  across that range as a band. The traffic-light engine is run at both ends
  of the band, so a band that crosses a per-portion threshold shows both
  colours rather than one.

Unit evidence for loose items comes from the sampling reports' sub-samples.
Each sub-sample weight is the average of several items bought together, so
the spread shown is the spread between purchases, and every unit says so.

Which sampling composite belongs to which CoFID food:
- exact name (the rule FPS also uses): applied;
- data/mapping/portion_links.json with status "reviewed": applied;
- the same file with status "draft": offered for a person to confirm, never
  applied on its own.
"""

from __future__ import annotations

import json
import re
import statistics
from functools import lru_cache
from pathlib import Path
from typing import Any

from .fv_samples import import_all_samples
from .lookup import _index
from .retail_core import sale_info
from .traffic_lights import traffic_lights

LINKS = Path(__file__).resolve().parents[2] / "data" / "mapping" / "portion_links.json"
LIGHT_INPUTS = ("fat", "saturates", "sugars", "salt")


def _key(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip().casefold())


def _unit(observation, basis: str, food_id: str, status: str) -> dict[str, Any] | None:
    weights = []
    for sub in observation.composite.subsamples:
        if sub.weight_g is None:
            continue
        if basis == "edible":
            if sub.edible_portion is None:
                continue
            weights.append(sub.weight_g * sub.edible_portion)
        else:
            weights.append(sub.weight_g)
    if not weights:
        return None
    n = len(weights)
    description = observation.description.replace("Average weight of ", "").replace("Average weight ", "")
    report = observation.release
    return {
        "key": f"{report.source_id}:{re.sub(r'[^a-z0-9]+', '-', observation.composite.food_name.casefold()).strip('-')}:{basis}",
        "food_id": food_id,
        "label": description,
        "weight": basis,
        "typical_g": statistics.fmean(weights),
        "low_g": min(weights),
        "high_g": max(weights),
        "n": n,
        "sd_g": statistics.stdev(weights) if n > 1 else None,
        "spread": (f"Range of {n} purchase averages (each purchase several items), bought "
                   f"{observation.period_start} to {observation.period_end}."
                   if n > 1 else "One purchase only; no range."),
        "basis": ("edible part of each purchase: weight x its edible proportion"
                  if basis == "edible" else "whole item as bought"),
        "link": status,
        "applied": status in ("exact_name", "reviewed"),
        "source": {
            "label": f"Sampling report {observation.period_start[:4]}",
            "citation": f"{report.publisher}, {report.dataset}",
            "rights": report.licence,
            "detail": f"Composite: {observation.composite.food_name}. {description}.",
            "url": report.url,
        },
    }


@lru_cache(maxsize=1)
def sample_units() -> dict[str, tuple[dict[str, Any], ...]]:
    by_name = _index()[1]
    by_code = _index()[0]
    observations = {(o.release.source_id, o.composite.food_name): o for o in import_all_samples().observations}
    out: dict[str, list[dict[str, Any]]] = {}

    def add(unit):
        if unit is not None:
            out.setdefault(unit["food_id"], []).append(unit)

    for (source, composite), o in observations.items():
        matches = [f for f in by_name.get(composite, [])] or [
            f for name, foods in by_name.items() if _key(name) == _key(composite) for f in foods]
        if len(matches) == 1:
            basis = "edible" if o.edible_portion_mean is not None else "whole"
            add(_unit(o, basis, matches[0].food_id, "exact_name"))
    for link in json.loads(LINKS.read_text(encoding="utf-8"))["links"]:
        o = observations.get((link["report"], link["composite"]))
        foods = by_code.get(link["cofid_code"], [])
        if o is None or len(foods) != 1 or link["status"] not in ("draft", "reviewed"):
            raise ValueError(f"portion_links.json: cannot resolve {link['composite']} -> {link['cofid_code']}.")
        add(_unit(o, link["weight"], foods[0].food_id, link["status"]))
    return {k: tuple(v) for k, v in out.items()}


def units_for(food_id: str) -> list[dict[str, Any]]:
    """Fresh copies: a request may relabel its own units, never the shared table."""
    return [dict(u) for u in sample_units().get(food_id, ())]


def band(per_100g: dict[str, float | None], low_g: float, high_g: float,
         typical_g: float | None = None) -> dict[str, Any]:
    """Per-unit figures across a weight range, coloured by the engine at both ends."""
    if any(per_100g.get(k) is None for k in ("saturates", "sugars", "salt")):
        return {"available": False, "reason": "Traffic lights need saturates, sugars and salt."}
    ends = {}
    for name, grams in (("low", low_g), ("typical", typical_g), ("high", high_g)):
        if grams is None:
            continue
        lights = traffic_lights(is_drink=False, per_100=dict(per_100g), portion=grams)
        ends[name] = {
            "grams": grams,
            "amounts": {k: (None if per_100g.get(k) is None else per_100g[k] * grams / 100.0)
                        for k in (*LIGHT_INPUTS, "energy_kj")},
            "colours": {k: v["colour"] for k, v in lights["colours"].items() if v},
            "portion_rule_applied": lights["portion_rule_applied"],
        }
    crosses = sorted(k for k in ends["low"]["colours"]
                     if ends["low"]["colours"][k] != ends["high"]["colours"].get(k))
    return {"available": True, "ends": ends, "crosses": crosses,
            "rule": ("Colours follow per 100 g. Above 100 g a unit is also checked against the "
                     "per-portion red limits, so a band can change colour across its range.")}


def describe(food_id: str, food_code: str, per_100g: dict[str, float | None],
             pack_g: float | None = None, confirmed: frozenset[str] = frozenset()) -> dict[str, Any]:
    """The as-sold view for one food: sale format, unit evidence, band."""
    sale = sale_info(food_code)
    units = units_for(food_id)
    applied = [u for u in units if u["applied"] or u["key"] in confirmed]
    for u in units:
        if not u["applied"] and u["key"] in confirmed:
            u["link"] = "user_confirmed"
    proposed = [u for u in units if not u["applied"] and u["key"] not in confirmed]
    result: dict[str, Any] = {
        "sale": sale,
        "kind": "loose" if sale and sale["loose"] else ("packaged" if pack_g else
                ("listed" if sale else "unknown")),
        "units": applied,
        "proposed_units": proposed,
        "unit": None,
    }
    if pack_g is not None:
        result["kind"] = "packaged"
        result["unit"] = {"label": "pack, as declared by you", "typical_g": pack_g, "low_g": pack_g,
                          "high_g": pack_g, "basis": "declared pack weight (caller-supplied)",
                          "spread": "One declared weight; no range.", "source": {"label": "Your figure"}}
    elif applied:
        result["unit"] = max(applied, key=lambda u: u["n"])
    if result["unit"] is not None:
        u = result["unit"]
        result["band"] = band(per_100g, u["low_g"], u["high_g"], u["typical_g"])
    else:
        result["note"] = ("No unit weight is on record for this food. ShelfScale does not invent one; "
                          "per 100 g still stands." + (" A possible unit is listed for you to confirm."
                                                       if proposed else ""))
    return result
