"""The data release as files, built from the same in-process data the API serves.

Nothing here computes a value or a score of its own. Foods and observations come
from lookup._index (what /v1/lookup returns), portions from ui_api and as_sold
(what the page shows), scores from cofid_assess.assess_cofid_food (what
/v1/lookup scores), and match decisions from the files where they are recorded.

Three uses:
- summary(): the counts on /api and on the home page (one function, so they agree);
- groups() / group(): browse by CoFID food group;
- build(directory): the CSV files and release_manifest.json, with row counts and
  SHA-256 checksums. current() builds once per process into data/releases/.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable

from . import laws
from .as_sold import sample_units
from .cofid_assess import assess_cofid_food
from .fps import import_fps, load_release as fps_release
from .lookup import DATA_RELEASE, _food_dict, _index, _observation_dict, cofid_release
from .retail_core import sale_info

ROOT = Path(__file__).resolve().parents[2]
GROUPS = ROOT / "data" / "mapping" / "cofid_groups.json"
REGISTER = ROOT / "data" / "source-register.yaml"
OVERLAY_MATCHES = ROOT / "data" / "overlays" / "matches.json"
FPS_REVIEW = ROOT / "data" / "reconciliation" / "fps-review.json"
PORTION_LINKS = ROOT / "data" / "mapping" / "portion_links.json"
RELEASE_DIR_VAR = "SHELFSCALE_RELEASE_DIR"
REPO_URL = "https://github.com/elliotkarikari/Product-nutrition-database"

FILES = ("foods.csv", "nutrient_observations.csv", "portions.csv", "scores.csv", "match_decisions.csv")
MANIFEST = "release_manifest.json"

# Drafted for Elliot's review (data-first round, 2026-11-06); not settled copy.
CITATION = (f"Karikari, E. (2026). ShelfScale Open, data release {DATA_RELEASE}. {REPO_URL}. "
            "Includes CoFID 2021 (Public Health England, OGL v3.0) and Food Portion Sizes, 3rd edition "
            "(Food Standards Agency, TSO 2002, Crown copyright). Full attribution in release_manifest.json.")

COUNT_LABELS = {
    "foods": "foods in the release",
    "foods_with_as_sold_unit": "foods with an as-sold unit weight",
    "sources_in_register": "sources in the register",
}


# ---------- counts ----------

def _register_ids() -> list[str]:
    return re.findall(r"^  - id: (\S+)$", REGISTER.read_text(encoding="utf-8"), flags=re.MULTILINE)


@lru_cache(maxsize=1)
def summary() -> dict[str, Any]:
    """The release counts. /api publishes this dict; the page shows it."""
    with_unit = sum(1 for units in sample_units().values() if any(u["applied"] for u in units))
    return {
        "data_release": DATA_RELEASE,
        "foods": len(cofid_release().foods),
        "foods_with_as_sold_unit": with_unit,
        "sources_in_register": len(_register_ids()),
        "labels": dict(COUNT_LABELS),
        "notes": {
            "foods": "CoFID 2021 foods, each with every value and its source.",
            "foods_with_as_sold_unit": ("Foods with a unit weight from weighed purchases in the sampling "
                                        "reports, linked by exact name or a reviewed link. Draft links "
                                        "are not counted until a person confirms them."),
            "sources_in_register": ("Every source the project has assessed, whatever its status: "
                                    "imported, deferred, reference only or excluded."),
        },
    }


# ---------- groups ----------

@lru_cache(maxsize=1)
def group_names() -> dict[str, str]:
    return json.loads(GROUPS.read_text(encoding="utf-8"))["names"]


def _name(code: str) -> str:
    return group_names().get(code) or f"{code} (not named in the CoFID user guide)"


def _subgroup(code: str) -> str:
    """The two-letter group a food code sits in, or its own code if the guide has no two-letter name."""
    return code[:2] if code[:2] in group_names() else code


@lru_cache(maxsize=1)
def groups() -> dict[str, Any]:
    """The 14 CoFID main groups with food counts, in the guide's order."""
    counts: dict[str, int] = {}
    for food in cofid_release().foods:
        letter = (food.group or "?")[:1]
        counts[letter] = counts.get(letter, 0) + 1
    supers = [k for k in group_names() if len(k) == 1]
    return {
        "data_release": DATA_RELEASE,
        "source": "CoFID 2021 user guide, Appendix B",
        "groups": [{"code": k, "name": group_names()[k], "foods": counts.get(k, 0)} for k in supers],
        "total": sum(counts.values()),
    }


def group(code: str) -> dict[str, Any]:
    """One main group: its sub-groups and every food in it, by name."""
    if code not in [g["code"] for g in groups()["groups"]]:
        raise LookupError("No CoFID main group has that code.")
    from .ui_api import portions_for  # one-tap units, as search shows them
    subs: dict[str, list[dict[str, Any]]] = {}
    for food in cofid_release().foods:
        if (food.group or "").startswith(code):
            subs.setdefault(_subgroup(food.group), []).append({
                "food_id": food.food_id, "code": food.source_code, "name": food.name,
                "portions": sum(1 for p in portions_for(food.food_id) if p["tappable"])})
    return {
        "data_release": DATA_RELEASE, "code": code, "name": group_names()[code],
        "foods": sum(len(v) for v in subs.values()),
        "subgroups": [{"code": k, "name": _name(k), "foods": sorted(v, key=lambda f: f["name"].casefold())}
                      for k, v in sorted(subs.items())],
    }


# ---------- rows ----------

OBSERVATION_COLUMNS = (
    "observation_id", "food_id", "food_code", "source_food",
    "nutrient_code", "nutrient_label", "nutrient_table", "nutrient_method", "unit",
    "value", "value_text", "value_kind", "basis", "state", "value_method",
    "source_id", "edition", "release_sha256",
    "period_start", "period_end", "analysis_period", "source_locator",
    "confidence", "status", "supersedes", "superseded_by", "data_release",
)


def observation_row(o: dict[str, Any], food_id: str) -> dict[str, Any]:
    r = o["release"]
    return {
        "observation_id": o["observation_id"], "food_id": food_id, "food_code": o["food_code"],
        "source_food": o["source_food"], "nutrient_code": o["nutrient_code"],
        "nutrient_label": o["nutrient_label"], "nutrient_table": o["table"], "nutrient_method": o["method"],
        "unit": o["unit"], "value": o["value"], "value_text": o["value_text"], "value_kind": o["value_kind"],
        "basis": o["basis"], "state": o["state"], "value_method": o["value_method"],
        "source_id": r["source_id"], "edition": r["edition"], "release_sha256": r["sha256"],
        "period_start": o["period_start"], "period_end": o["period_end"],
        "analysis_period": o["analysis_period"], "source_locator": o["source_locator"],
        "confidence": o["confidence"], "status": o["status"], "supersedes": o["supersedes"],
        "superseded_by": o["superseded_by"], "data_release": DATA_RELEASE,
    }


FOOD_COLUMNS = ("food_id", "cofid_code", "name", "description", "main_group_code", "main_group",
                "group_code", "group_name", "previous_codes", "main_data_reference", "footnote",
                "sale_format", "sold_loose", "as_sold_units", "portions_listed", "observations_current",
                "data_release")


def _foods() -> Iterable[dict[str, Any]]:
    by_food = _index()[2]
    units = sample_units()
    fps_by_food: dict[str, int] = {}
    for p in import_fps(cofid_release().foods).portions:
        if p.cofid_food_id:
            fps_by_food[p.cofid_food_id] = fps_by_food.get(p.cofid_food_id, 0) + 1
    for food in cofid_release().foods:
        sale = sale_info(food.source_code)
        code = food.group or ""
        yield {
            "food_id": food.food_id, "cofid_code": food.source_code, "name": food.name,
            "description": food.description, "main_group_code": code[:1], "main_group": _name(code[:1]),
            "group_code": code, "group_name": _name(code), "previous_codes": food.previous_codes,
            "main_data_reference": food.main_data_reference, "footnote": food.footnote,
            "sale_format": sale["sale_format"] if sale else None,
            "sold_loose": None if sale is None else ("yes" if sale["loose"] else "no"),
            "as_sold_units": sum(1 for u in units.get(food.food_id, ()) if u["applied"]),
            "portions_listed": fps_by_food.get(food.food_id, 0) + len(units.get(food.food_id, ())),
            "observations_current": sum(1 for o in by_food.get(food.food_id, []) if o.status == "current"),
            "data_release": DATA_RELEASE,
        }


def _observations() -> Iterable[dict[str, Any]]:
    by_food = _index()[2]
    for food in cofid_release().foods:
        for o in by_food.get(food.food_id, []):
            yield observation_row(_observation_dict(o), food.food_id)


PORTION_COLUMNS = ("source_kind", "food_id", "cofid_code", "food_name_in_source", "brand", "portion",
                   "weight_text", "grams", "low_g", "high_g", "sample_size", "sd_g", "spread",
                   "weight_basis", "link_to_cofid", "applied", "source_id", "source_row", "citation",
                   "rights", "data_release")

FPS_SPREAD = "Not given by the source: one printed typical weight."


def _portions() -> Iterable[dict[str, Any]]:
    foods = cofid_release().foods
    codes = {f.food_id: f.source_code for f in foods}
    fps = import_fps(foods)
    for p in fps.portions:
        yield {
            "source_kind": "Food Portion Sizes (typical portion)", "food_id": p.cofid_food_id,
            "cofid_code": codes.get(p.cofid_food_id), "food_name_in_source": p.food_name, "brand": p.brand,
            "portion": p.portion_description, "weight_text": p.weight_text, "grams": p.grams,
            "low_g": min(p.amounts) if p.value_kind == "range" else None,
            "high_g": max(p.amounts) if p.value_kind == "range" else None,
            "sample_size": None, "sd_g": None, "spread": FPS_SPREAD,
            "weight_basis": f"{p.basis}, {p.value_kind}", "link_to_cofid": p.cofid_match,
            "applied": "yes" if p.cofid_food_id and p.grams is not None else "no",
            "source_id": p.release.source_id, "source_row": p.source_row,
            "citation": p.release.attribution, "rights": p.release.licence, "data_release": DATA_RELEASE,
        }
    for food_id, units in sorted(sample_units().items()):
        for u in units:
            yield {
                "source_kind": "Sampling report (weighed purchases)", "food_id": food_id,
                "cofid_code": codes.get(food_id), "food_name_in_source": u["source"]["detail"],
                "brand": None, "portion": u["label"], "weight_text": None,
                "grams": round(u["typical_g"], 3), "low_g": round(u["low_g"], 3), "high_g": round(u["high_g"], 3),
                "sample_size": u["n"], "sd_g": None if u["sd_g"] is None else round(u["sd_g"], 3),
                "spread": u["spread"], "weight_basis": u["basis"], "link_to_cofid": u["link"],
                "applied": "yes" if u["applied"] else "no (draft link: a person must confirm it)",
                "source_id": u["key"].split(":")[0], "source_row": None,
                "citation": u["source"]["citation"], "rights": u["source"]["rights"], "data_release": DATA_RELEASE,
            }


def _slug(model_id: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", model_id.casefold()).strip("_")


def score_columns() -> tuple[str, ...]:
    cols = ["food_id", "cofid_code", "name"]
    for model in laws.models():
        s = _slug(model)
        cols += [f"{s}_law", f"{s}_law_status", f"{s}_score", f"{s}_verdict", f"{s}_not_scorable_reason"]
    return (*cols, "verdict_changes", "figures_used", "data_release")


def score_row(food_id: str, code: str, name: str, assessment: dict[str, Any],
              figures_used: str) -> dict[str, Any]:
    row: dict[str, Any] = {"food_id": food_id, "cofid_code": code, "name": name}
    for model_id in laws.models():
        s, m = _slug(model_id), assessment["models"][model_id]
        law = m["law"]
        row[f"{s}_law"] = f"{law['name']} {law['version']}"
        row[f"{s}_law_status"] = law["status_text"]
        if m.get("scorable"):
            row[f"{s}_score"] = m["score"]
            row[f"{s}_verdict"] = "less healthy" if m["less_healthy"] else "not less healthy"
            row[f"{s}_not_scorable_reason"] = None
        else:
            row[f"{s}_score"] = None
            row[f"{s}_verdict"] = "not scored"
            row[f"{s}_not_scorable_reason"] = (m.get("reason") if m.get("applicable") is False
                                               else "needs " + "; ".join(m.get("missing_inputs") or []))
    change = assessment.get("verdict_changes_under_2018")
    row["verdict_changes"] = "unknown" if change is None else ("yes" if change else "no")
    row["figures_used"] = figures_used
    row["data_release"] = DATA_RELEASE
    return row


def _scores() -> Iterable[dict[str, Any]]:
    by_food = _index()[2]
    for food in cofid_release().foods:
        a = assess_cofid_food(_food_dict(food, by_food.get(food.food_id, [])), fvn_percent=None, portion_g=None)
        yield score_row(food.food_id, food.source_code, food.name, a,
                        "CoFID values only; no figures supplied by anyone")


DECISION_COLUMNS = ("category", "subject", "source_id", "food_id", "cofid_code", "cofid_name",
                    "decision", "basis", "decided_by", "recorded_in", "data_release")

DECISION_CATEGORIES = {
    "fps_portion_to_cofid": "Food Portion Sizes rows linked to CoFID foods by the exact-name rule",
    "sampling_unit_to_cofid": "Sampling-report unit weights linked to CoFID foods (exact name, reviewed or draft link)",
    "overlay_to_cofid": "Official milk and beef overlay samples matched to CoFID foods",
    "fps_reconciliation_review": "Reviewed disagreements between the FPS transcription and the book extraction",
    "visitor_confirmation": "Matches confirmed by visitors on the page",
}
EMPTY_REASONS = {
    "visitor_confirmation": ("None published. Visitor confirmations stay in the visitor's browser, or in a "
                             "service file when one is configured, and are not published until reviewed. "
                             "None have been reviewed."),
}


def _decisions() -> Iterable[dict[str, Any]]:
    foods = cofid_release().foods
    by_id = {f.food_id: f for f in foods}
    for p in import_fps(foods).portions:
        f = by_id.get(p.cofid_food_id)
        yield {"category": "fps_portion_to_cofid",
               "subject": f"row {p.source_row}: {p.food_name}" + (f", {p.portion_description}" if p.portion_description else ""),
               "source_id": p.release.source_id, "food_id": p.cofid_food_id, "cofid_code": f.source_code if f else None,
               "cofid_name": f.name if f else None,
               "decision": "linked" if f else "not linked",
               "basis": "exact food name, one CoFID food" if f else "no single CoFID food with the exact name",
               "decided_by": "rule (src/shelfscale/fps.py)", "recorded_in": "src/shelfscale/fps.py"}
    links = {(l["report"], l["composite"], l["cofid_code"]): l
             for l in json.loads(PORTION_LINKS.read_text(encoding="utf-8"))["links"]}
    for food_id, units in sorted(sample_units().items()):
        f = by_id[food_id]
        for u in units:
            source = u["key"].split(":")[0]
            composite = u["source"]["detail"].split(". ")[0].replace("Composite: ", "")
            link = links.get((source, composite, f.source_code))
            yield {"category": "sampling_unit_to_cofid", "subject": f"{composite} ({u['weight']} weight)",
                   "source_id": source, "food_id": food_id, "cofid_code": f.source_code, "cofid_name": f.name,
                   "decision": "linked" if u["applied"] else "proposed, not applied until a person confirms it",
                   "basis": "exact food name" if u["link"] == "exact_name" else f"{u['link']} link",
                   "decided_by": ("rule (src/shelfscale/as_sold.py)" if link is None else
                                  (link.get("reviewed_by") or link.get("drafted_by"))),
                   "recorded_in": "src/shelfscale/as_sold.py" if link is None else "data/mapping/portion_links.json"}
    for key, m in json.loads(OVERLAY_MATCHES.read_text(encoding="utf-8")).items():
        source, _, sample = key.partition(":")
        f = by_id.get(m["food_id"]) if m["food_id"] else None
        yield {"category": "overlay_to_cofid", "subject": sample, "source_id": source, "food_id": m["food_id"],
               "cofid_code": f.source_code if f else None, "cofid_name": m["food_name"],
               "decision": "matched" if m["food_id"] else "not matched; kept as a source-only observation",
               "basis": m["reason"], "decided_by": "recorded match file", "recorded_in": "data/overlays/matches.json"}
    for key, r in json.loads(FPS_REVIEW.read_text(encoding="utf-8")).items():
        yield {"category": "fps_reconciliation_review", "subject": " / ".join(x for x in json.loads(key) if x),
               "source_id": "uk-food-portion-sizes-2002", "food_id": None, "cofid_code": None, "cofid_name": None,
               "decision": (f"extraction row {r['extraction_row']}" if r.get("extraction_row")
                            else "no matching extraction row established"),
               "basis": r["reason"], "decided_by": "review recorded in the repository",
               "recorded_in": "data/reconciliation/fps-review.json"}


# ---------- files ----------

def _write_csv(path: Path, columns: tuple[str, ...], rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Write the CSV and a gzip copy in chunks; return its row count, size and SHA-256 (of the CSV)."""
    digest, count, size = hashlib.sha256(), 0, 0
    with open(path, "wb") as plain, open(f"{path}.gz", "wb") as raw_gz, \
            gzip.GzipFile(fileobj=raw_gz, mode="wb", compresslevel=6, mtime=0) as packed:
        buffer = io.StringIO(newline="")
        writer = csv.DictWriter(buffer, fieldnames=columns, lineterminator="\n", extrasaction="raise")
        writer.writeheader()

        def flush() -> None:
            nonlocal size
            chunk = buffer.getvalue().encode("utf-8")
            plain.write(chunk)
            packed.write(chunk)
            digest.update(chunk)
            size += len(chunk)
            buffer.seek(0)
            buffer.truncate()

        for row in rows:
            writer.writerow({k: "" if row.get(k) is None else row[k] for k in columns})
            count += 1
            if count % 2000 == 0:
                flush()
        flush()
    return {"rows": count, "bytes": size, "sha256": digest.hexdigest()}


def _attribution() -> list[dict[str, Any]]:
    seen: dict[str, dict[str, Any]] = {}
    for obs in _index()[2].values():
        for o in obs:
            r = o.release
            seen.setdefault(r.source_id, {"source_id": r.source_id, "dataset": r.dataset, "edition": r.edition,
                                          "publisher": r.publisher, "licence": r.licence,
                                          "attribution": r.attribution, "url": r.url, "used_in": ["nutrient_observations.csv"]})
    fps, _ = fps_release()
    manifest = json.loads((ROOT / "data" / "raw" / "uk-food-portion-sizes-2002" / "MANIFEST.json").read_text(encoding="utf-8"))
    seen[fps.source_id] = {
        "source_id": fps.source_id, "dataset": fps.dataset, "edition": fps.edition, "publisher": fps.publisher,
        "licence": fps.licence, "attribution": fps.attribution, "url": fps.url,
        "extraction": "hand-corrected extraction of the book (see the snapshot MANIFEST.json)",
        "decision": manifest["decision"], "used_in": ["portions.csv", "match_decisions.csv"],
    }
    for units in sample_units().values():
        for u in units:
            source = u["key"].split(":")[0]
            seen.setdefault(source, {"source_id": source, "dataset": u["source"]["citation"], "licence": u["source"]["rights"],
                                     "url": u["source"]["url"], "used_in": ["portions.csv", "match_decisions.csv"]})
    return [seen[k] for k in sorted(seen)]


def build(directory: Path) -> dict[str, Any]:
    """Write the release files and their manifest. Deterministic for a given repository state."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    tables = {
        "foods.csv": (FOOD_COLUMNS, _foods, "One row per CoFID 2021 food: identity, group, how it is sold."),
        "nutrient_observations.csv": (OBSERVATION_COLUMNS, _observations,
                                      "Long format: one row per value, with its source, release, method, state, "
                                      "period, confidence and status (SPEC section 5). Superseded values are kept."),
        "portions.csv": (PORTION_COLUMNS, _portions, "Portion and unit weights with sample sizes, spreads and a "
                                                     "citation on every row."),
        "scores.csv": (score_columns(), _scores, "Both models for every food from CoFID values alone; where a "
                                                 "model cannot score a food, the reason is given instead of a number."),
        "match_decisions.csv": (DECISION_COLUMNS, _decisions, "Every recorded decision linking a source record "
                                                              "to a CoFID food."),
    }
    files = []
    per_category = {k: 0 for k in DECISION_CATEGORIES}
    for name in FILES:
        columns, rows, description = tables[name]
        records = rows()
        if name == "match_decisions.csv":
            records = list(records)
            for row in records:
                per_category[row["category"]] += 1
        # A gzip copy sits beside each file for browsers that accept it; checksums are of the CSV.
        written = _write_csv(directory / name, columns, records)
        files.append({"name": name, **written, "description": description})
    manifest = {
        "data_release": DATA_RELEASE,
        "citation": CITATION,
        "counts": {k: summary()[k] for k in COUNT_LABELS},
        "files": files,
        "match_decision_categories": [
            {"category": k, "description": v, "rows": per_category[k],
             "statement": EMPTY_REASONS.get(k) if per_category[k] == 0 else None}
            for k, v in DECISION_CATEGORIES.items()],
        "laws": [laws.label(m) for m in laws.models()],
        "attribution": _attribution(),
        "columns_note": ("nutrient_observations.csv names each value's source by source_id, edition and the "
                         "SHA-256 of the source file; the attribution block below gives each source's dataset, "
                         "publisher, licence and attribution text. The nutrient definition is the source's own "
                         "code, label, table and method for that edition."),
        "not_included": ["Overlay observations that match no CoFID food (source-only) are not in this release.",
                         "Free sugars are not in CoFID, so no food has a 2018 score from CoFID values alone."],
        "repository": REPO_URL,
    }
    (directory / MANIFEST).write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def default_directory() -> Path:
    return Path(os.environ.get(RELEASE_DIR_VAR) or ROOT / "data" / "releases" / re.sub(r"[^A-Za-z0-9.+-]", "_", DATA_RELEASE))


@lru_cache(maxsize=1)
def current() -> tuple[Path, dict[str, Any]]:
    """Build the release once per process (fresh, so it always matches the running code)."""
    directory = default_directory()
    return directory, build(directory)


# ---------- one food, as its page shows it ----------

FOOD_CSV_COLUMNS = ("section", "item", "value", "unit", "basis", "detail", "source", "citation",
                    "observation_id", "data_release")


def food_csv(page: dict[str, Any]) -> bytes:
    """One food's record as CSV, built from the payload ui_api.food returns for its page."""
    release_id = page["data_release"]
    rows: list[dict[str, Any]] = []

    def add(section, item, value=None, unit=None, basis=None, detail=None, source=None, citation=None, obs=None):
        rows.append({"section": section, "item": item, "value": value, "unit": unit, "basis": basis,
                     "detail": detail, "source": source, "citation": citation, "observation_id": obs,
                     "data_release": release_id})

    for item in ("food_id", "code", "name", "group", "description"):
        add("identity", "cofid_code" if item == "code" else item, page[item])
    add("identity", "group_name", _name(page["group"] or ""))
    sold = page["as_sold"]
    sale = sold.get("sale")
    add("as_sold", "sold_as", sold["kind"], detail=sale["sale_format"] if sale else None,
        source=sale["source"]["label"] if sale else None, citation=sale["source"]["citation"] if sale else None)
    unit = sold.get("unit")
    if unit:
        src = unit.get("source") or {}
        for end in ("low_g", "typical_g", "high_g"):
            add("as_sold", f"unit_{end[:-2]}", round(unit[end], 3), "g", unit.get("basis"),
                f"{unit['label']}. {unit.get('spread', '')}".strip(), src.get("label"), src.get("citation"))
        add("as_sold", "unit_sample_size", unit.get("n"), detail=unit.get("spread"), source=src.get("label"))
    elif sold.get("note"):
        add("as_sold", "unit", None, detail=sold["note"])
    for p in page["portions"]:
        src = p["source"]
        add("portion", p["label"], p["grams"], "g" if p["grams"] is not None else None, p["basis"],
            "; ".join(x for x in (p["weight_text"], src.get("detail"), src.get("note")) if x),
            src.get("label"), src.get("citation"))
    for row in page["panel"]:
        s = row["source"] or {}
        add("composition", row["label"], row["value"] if row["value"] is not None else row["value_text"],
            row["unit"], row["basis"], f"CoFID code {row['code']}; {row['value_kind']}",
            s.get("label"), s.get("citation"), s.get("observation_id"))
    for row in page["overlay_values"]:
        s = row["source"]
        add("composition", row["label"], row["value"] if row["value"] is not None else row["value_text"],
            row["unit"], row["basis"], f"code {row['code']}; {row['value_kind']}",
            s.get("label"), s.get("citation"), s.get("observation_id"))
    for name, value in (page.get("caller_supplied") or {}).items():
        add("your_figures", name, value, detail="entered by you; ShelfScale has not checked it")
    figures = "your figures and ShelfScale reference data" if page.get("caller_supplied") else "ShelfScale reference data only"
    scored = score_row(page["food_id"], page["code"], page["name"], page["assessment"], figures)
    for model_id in laws.models():
        s = _slug(model_id)
        add("score", scored[f"{s}_law"], scored[f"{s}_score"], basis=scored[f"{s}_verdict"],
            detail=scored[f"{s}_not_scorable_reason"] or scored["figures_used"],
            source=f"{scored[f'{s}_law']}, {scored[f'{s}_law_status']}")
    add("score", "verdict_changes", scored["verdict_changes"])
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=FOOD_CSV_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: "" if row.get(k) is None else row[k] for k in FOOD_CSV_COLUMNS})
    return buffer.getvalue().encode("utf-8")
