"""Minimal .xlsx reader on the standard library.

Reads one worksheet as rows of cell text, exactly as stored in the file.
No type coercion: a number comes back as the text in the file's XML, a
string as the string. Empty cells are None. That is all the CoFID importer
needs, and it keeps ShelfScale free of third-party dependencies.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

_NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
_CELL_REF = re.compile(r"([A-Z]+)(\d+)")


def _column_index(letters: str) -> int:
    index = 0
    for letter in letters:
        index = index * 26 + (ord(letter) - 64)
    return index - 1


def _text(element: ElementTree.Element) -> str:
    # Shared and inline strings may be split into rich-text runs.
    return "".join(node.text or "" for node in element.iter(f"{{{_NS['m']}}}t"))


def sheet_names(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as book:
        workbook = ElementTree.fromstring(book.read("xl/workbook.xml"))
    return [sheet.get("name") for sheet in workbook.find("m:sheets", _NS)]


def read_sheet(path: Path, name: str) -> dict[int, list[str | None]]:
    """Return {excel_row_number: [cell text or None, ...]} for one sheet."""
    with zipfile.ZipFile(path) as book:
        workbook = ElementTree.fromstring(book.read("xl/workbook.xml"))
        rels = ElementTree.fromstring(book.read("xl/_rels/workbook.xml.rels"))
        targets = {rel.get("Id"): rel.get("Target") for rel in rels}
        sheet_id = None
        for sheet in workbook.find("m:sheets", _NS):
            if sheet.get("name") == name:
                sheet_id = sheet.get(f"{{{_NS['r']}}}id")
        if sheet_id is None:
            raise KeyError(f"No worksheet named {name!r}.")
        target = targets[sheet_id].lstrip("/")
        member = target if target.startswith("xl/") else f"xl/{target}"

        shared: list[str] = []
        if "xl/sharedStrings.xml" in book.namelist():
            strings = ElementTree.fromstring(book.read("xl/sharedStrings.xml"))
            shared = [_text(item) for item in strings.findall("m:si", _NS)]

        rows: dict[int, list[str | None]] = {}
        sheet_xml = ElementTree.fromstring(book.read(member))
        for row in sheet_xml.iter(f"{{{_NS['m']}}}row"):
            cells: list[str | None] = []
            for cell in row.findall("m:c", _NS):
                match = _CELL_REF.fullmatch(cell.get("r"))
                column = _column_index(match.group(1))
                kind = cell.get("t")
                value = cell.find("m:v", _NS)
                if kind == "s":
                    text = shared[int(value.text)]
                elif kind == "inlineStr":
                    text = _text(cell.find("m:is", _NS))
                elif value is not None:
                    text = value.text
                else:
                    text = None
                while len(cells) <= column:
                    cells.append(None)
                cells[column] = text
            rows[int(row.get("r"))] = cells
        return rows
