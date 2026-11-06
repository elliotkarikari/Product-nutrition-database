"""Small readers for the official overlay formats; no spreadsheet dependency."""
from html.parser import HTMLParser
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile


class HTMLTables(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tables = []
        self.table = self.row = self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == 'table': self.table = []
        elif tag == 'tr': self.row = []
        elif tag in ('td', 'th'): self.cell = ''

    def handle_data(self, data):
        if self.cell is not None: self.cell += data

    def handle_endtag(self, tag):
        if tag in ('td', 'th') and self.cell is not None:
            self.row.append(' '.join(self.cell.split()))
            self.cell = None
        elif tag == 'tr' and self.table is not None:
            self.table.append(self.row)
            self.row = None
        elif tag == 'table':
            self.tables.append(self.table)
            self.table = None


def html_tables(path: Path) -> list:
    parser = HTMLTables()
    parser.feed(path.read_text(encoding='utf-8'))
    return parser.tables


def ods_tables(path: Path) -> dict[str, list[list[str]]]:
    ns = {'t': 'urn:oasis:names:tc:opendocument:xmlns:table:1.0',
          'x': 'urn:oasis:names:tc:opendocument:xmlns:text:1.0'}
    with ZipFile(path) as archive:
        root = ET.fromstring(archive.read('content.xml'))
    tables = {}
    for table in root.findall('.//t:table', ns):
        rows = []
        for row in table.findall('.//t:table-row', ns):
            values = []
            for cell in row:
                text = ' '.join(''.join(p.itertext()) for p in cell.findall('x:p', ns))
                repeat = int(cell.get('{'+ns['t']+'}number-columns-repeated', '1'))
                if repeat > 1000 and text:
                    raise ValueError('Unexpected repeated populated ODS cells')
                # Empty padding is irrelevant, but never silently truncate data.
                values.extend([text] * min(repeat, 1000))
            while values and not values[-1]: values.pop()
            repeat = int(row.get('{'+ns['t']+'}number-rows-repeated', '1'))
            if repeat > 1000 and values:
                raise ValueError('Unexpected repeated populated ODS rows')
            rows.extend([values] * repeat if values else [[]])
        tables[table.get('{'+ns['t']+'}name')] = rows
    return tables
