"""Official, checksum-verified milk/beef overlays with explicit food matches.

Every source value remains inspectable. Unmatched foods are source-only;
[x] is not measured and never replaces an observation. Below-limit values
are retained as bounds with no invented point value. CoFID is immutable.
"""
from dataclasses import dataclass, replace
import hashlib
import json
from pathlib import Path
import re

from .model import DatasetRelease, Food, NutrientDefinition, NutrientObservation
from .source_tables import html_tables, ods_tables
from .validation import number

ROOT = Path(__file__).resolve().parents[2] / 'data'
SOURCES = ('uk-milk-2022-23', 'uk-beef-2024')


@dataclass
class OverlayImport:
    observations: list[NutrientObservation]
    source_only: list[NutrientObservation]
    not_measured: list[dict]
    matches: dict


def verified_source(source: str, root: Path = ROOT):
    folder = root / 'raw' / source
    manifest = json.loads((folder / 'MANIFEST.json').read_text())
    for entry in manifest['files']:
        if hashlib.sha256((folder / entry['name']).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError(f"Refusing to import changed overlay file: {source}/{entry['name']}")
    name = 'report.html' if source == SOURCES[0] else 'results.ods'
    entry = next(f for f in manifest['files'] if f['name'] == name)
    release = DatasetRelease(**{k: manifest[k] for k in ('source_id','dataset','edition','publisher','retrieved','licence','attribution')},
                             url=entry['url'], sha256=entry['sha256'])
    return folder, release


def milk_values(folder):
    table = html_tables(folder / 'report.html')[3]
    if len(table) != 19 or '2022 to 2023 riboflavin' not in table[0][2]:
        raise ValueError('Unexpected milk analytical Table 4')
    for row_no, row in enumerate(table[1:], 2):
        for col, code, unit in ((2,'RIBO','mg'),(4,'VITB12','µg'),(6,'I','µg')):
            yield dict(sample=row[0], name=row[0], code=code, label=table[0][col], unit=unit,
                       basis='per_100g', text=row[col], table='Table 4', row=row_no, column=col+1,
                       method='published_seasonal_mean' if row[0].endswith('average') else 'laboratory_analysis',
                       period_start='2022-08-10' if not row[0].endswith('winter') else '2023-02-21',
                       period_end='2022-09-02' if row[0].endswith('summer') else '2023-02-21')


def beef_values(folder, root):
    columns = json.loads((root / 'overlays' / 'beef-columns.json').read_text())
    for table, rows in ods_tables(folder / 'results.ods').items():
        header = next((r for r in rows if r and r[0] == 'Composite sample number'), None)
        if header is None: continue
        for row_no, row in enumerate(rows, 1):
            if not row or not re.fullmatch(r'\d+\.\d+', row[0]): continue
            for key, col in columns.items():
                sheet, index = key.rsplit(':', 1)
                if sheet != table: continue
                index = int(index) - 1
                if header[index] != col['label'] or index >= len(row):
                    raise ValueError(f'Unexpected beef column at {key}')
                derived = table not in ('Inorganics','Vitamins') or col['code'] in ('BEEF:VITD_activity_2.5','VITE','TRYP60','NIACEQU')
                # Fat/water/nitrogen/cholesterol are direct analyses; source tables document derived values.
                if col['code'] in ('WATER','TOTNIT','FAT','CHOL'): derived = False
                yield dict(sample=row[0], name=row[1], **col, text=row[index], table=table,
                           row=row_no, column=index+1,
                           method='calculated_from_laboratory_analysis' if derived else 'laboratory_analysis',
                           period_start='2024', period_end='2024')


def import_overlays(cofid, root: Path = ROOT) -> OverlayImport:
    matches = json.loads((root / 'overlays' / 'matches.json').read_text())
    foods = {f.food_id: f for f in cofid.foods}
    definitions = {d.code: d for d in cofid.definitions}
    current, source_only, not_measured = [], [], []
    seen = set()
    for source in SOURCES:
        folder, release = verified_source(source, root)
        values = milk_values(folder) if source == SOURCES[0] else beef_values(folder, root)
        for v in values:
            match = matches[source+':'+v['sample']]
            if match['source_name'] != v['name']:
                raise ValueError('Overlay source name changed')
            if v['text'] == '[x]':
                not_measured.append({'source':source,'sample':v['sample'],'code':v['code']})
                continue
            below = re.fullmatch(r'<\s*([\d.]+)(?: \(LOQ\))?', v['text'])
            value = None if below else number(float(v['text']), v['code'])
            if below: number(float(below.group(1)), v['code'])
            target = match['food_id']
            if target:
                food = foods[target]
                if food.name != match['food_name']:
                    raise ValueError('Overlay target name changed')
            else:
                food = Food(v['sample'], v['sample'], v['name'], None, None, None,
                            None, None, v['row'], release)
            canonical = definitions.get(v['code'])
            if canonical and canonical.unit != v['unit']:
                raise ValueError(f"Overlay unit mismatch: {v['code']}")
            definition = NutrientDefinition(v['code'], v['label'], v['unit'], v['table'],
                                            canonical.method if canonical else None)
            obs = NutrientObservation(food, definition, value, v['text'],
                'below_limit' if below else 'number', v['basis'], 'as_described_in_food_name',
                v['method'], 'current', release, period_start=v['period_start'], period_end=v['period_end'],
                analysis_period=('2025-11 to 2026-02' if v['code'] in ('I','BEEF:VITD_activity_2.5','25OHD3','VITD3') else '2024-06 to 2024-10') if source == SOURCES[1] else '2022-2023',
                source_locator=f"{v['table']} row {v['row']} column {v['column']}", source_food=v['name'],
                confidence='official_composite_analysis')
            key = obs.observation_id
            if key in seen: raise ValueError(f'Duplicate overlay observation: {key}')
            seen.add(key)
            (current if target else source_only).append(obs)
    return OverlayImport(current, source_only, not_measured, matches)


def apply_overlays(original, additions):
    """Return history plus current values, with reversible per-nutrient links."""
    by_key = {(o.food.food_id, o.definition.code): o for o in original}
    history = []
    for new in additions:
        key = (new.food.food_id, new.definition.code)
        old = by_key.get(key)
        if old:
            if old.basis != new.basis or old.definition.unit != new.definition.unit:
                raise ValueError(f'Overlay basis/unit mismatch at {key}')
            history.append(replace(old, status='superseded', superseded_by=new.observation_id))
            new = replace(new, supersedes=old.observation_id)
        by_key[key] = new
    return history + list(by_key.values())
