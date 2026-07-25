"""
Z6 (2026-07-25): rebuilds static/downloads/budzet-obrazac.xlsx from the client's
docs/Budzet_obrazac.xlsx, adding sheet protection that keeps the formula cells
(column E) locked while every cell the applicant fills in stays editable.

Operates directly on the OOXML inside the .xlsx so that the embedded logo, print
settings and customXml parts survive byte-for-byte - openpyxl would drop them.

Rerun after the client sends a new version of the obrazac, then verify with:
    manage.py test apps.landing.tests.ExcelTemplateDownloadTests --keepdb

Row/column constants below describe the current layout; if the client restructures
the sheet, update them (and the test class) to match.
"""
import re
import sys
import zipfile
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
SRC = BASE / 'docs' / 'Budzet_obrazac.xlsx'
DST = BASE / 'static' / 'downloads' / 'budzet-obrazac.xlsx'

# Rows the user fills in. Column E holds the =C*D formula and stays locked.
DATA_ROWS = list(range(14, 18)) + list(range(20, 24)) + list(range(26, 31)) + list(range(33, 38))
INPUT_COLS = ['A', 'B', 'C', 'D', 'F']
# "Naziv tima:" label sits in A7; the answer goes to its right.
HEADER_ROW_CELLS = [('B', 7), ('C', 7), ('D', 7), ('E', 7), ('F', 7)]

SHEET_PROTECTION = (
    '<sheetProtection sheet="1" objects="1" scenarios="1"'
    ' formatCells="0" formatColumns="0" formatRows="0"/>'
)


def split_cellxfs(styles):
    """Return (prefix, [xf strings], suffix) for the <cellXfs> block."""
    m = re.search(r'<cellXfs count="(\d+)">(.*?)</cellXfs>', styles, re.S)
    if not m:
        sys.exit('cellXfs block not found in styles.xml')
    body = m.group(2)
    # Self-closing form first; otherwise the non-greedy match would stop at a
    # child element such as <alignment .../> and truncate the <xf>.
    xfs = re.findall(r'<xf\b[^>]*/>|<xf\b[^>]*>.*?</xf>', body, re.S)
    if len(xfs) != int(m.group(1)):
        sys.exit(f'cellXfs count mismatch: declared {m.group(1)}, parsed {len(xfs)}')
    if ''.join(xfs) != body:
        sys.exit('cellXfs parse is lossy - refusing to rewrite styles.xml')
    return m, xfs


def unlocked_variant(xf):
    """Copy an <xf> with <protection locked="0"/> added (protection follows alignment)."""
    if '<protection' in xf:
        return re.sub(r'<protection\b[^>]*/>', '<protection locked="0"/>', xf)
    if xf.endswith('/>'):
        head = xf[:-2].rstrip()
        return f'{head} applyProtection="1"><protection locked="0"/></xf>'
    head, inner = xf[:xf.index('>') + 1], xf[xf.index('>') + 1:-len('</xf>')]
    head = head[:-1].rstrip() + ' applyProtection="1">'
    return f'{head}{inner}<protection locked="0"/></xf>'


def main():
    if not SRC.exists():
        sys.exit(f'source template missing: {SRC}')

    with zipfile.ZipFile(SRC) as z:
        names = z.namelist()
        parts = {n: z.read(n) for n in names}
        infos = {i.filename: i for i in z.infolist()}

    styles = parts['xl/styles.xml'].decode('utf-8')
    sheet = parts['xl/worksheets/sheet1.xml'].decode('utf-8')

    match, xfs = split_cellxfs(styles)
    unlocked_for = {}  # original style index -> new style index

    def unlocked_index(orig):
        orig = int(orig)
        if orig not in unlocked_for:
            xfs.append(unlocked_variant(xfs[orig]))
            unlocked_for[orig] = len(xfs) - 1
        return unlocked_for[orig]

    targets = [(c, r) for r in DATA_ROWS for c in INPUT_COLS] + HEADER_ROW_CELLS
    touched, created = 0, 0

    for col, row in targets:
        ref = f'{col}{row}'
        cell_re = re.compile(r'<c r="%s"(?: s="(\d+)")?([^>]*?)(/>|>.*?</c>)' % ref, re.S)
        m = cell_re.search(sheet)
        if m:
            new_s = unlocked_index(m.group(1) or 0)
            rest, tail = m.group(2), m.group(3)
            sheet = sheet[:m.start()] + f'<c r="{ref}" s="{new_s}"{rest}{tail}' + sheet[m.end():]
            touched += 1
            continue

        # Cell absent from the XML (e.g. B7) - insert it, unlocked, in column order.
        row_re = re.compile(r'(<row[^>]*r="%d"[^>]*>)(.*?)(</row>)' % row, re.S)
        rm = row_re.search(sheet)
        if not rm:
            sys.exit(f'row {row} not found while inserting {ref}')
        new_s = unlocked_index(0)
        cells = re.findall(r'<c r="([A-Z]+)\d+".*?(?:/>|</c>)', rm.group(2), re.S)
        insert_at = len(rm.group(2))
        for existing in re.finditer(r'<c r="([A-Z]+)\d+".*?(?:/>|</c>)', rm.group(2), re.S):
            if existing.group(1) > col:
                insert_at = existing.start()
                break
        body = rm.group(2)[:insert_at] + f'<c r="{ref}" s="{new_s}"/>' + rm.group(2)[insert_at:]
        sheet = sheet[:rm.start()] + rm.group(1) + body + rm.group(3) + sheet[rm.end():]
        created += 1

    styles = (
        styles[:match.start()]
        + f'<cellXfs count="{len(xfs)}">' + ''.join(xfs) + '</cellXfs>'
        + styles[match.end():]
    )

    if '<sheetProtection' in sheet:
        sys.exit('sheet already carries a <sheetProtection> element')
    # Schema order: sheetData, sheetCalcPr, sheetProtection, ..., mergeCells
    sheet = sheet.replace('</sheetData>', '</sheetData>' + SHEET_PROTECTION, 1)

    parts['xl/styles.xml'] = styles.encode('utf-8')
    parts['xl/worksheets/sheet1.xml'] = sheet.encode('utf-8')

    with zipfile.ZipFile(DST, 'w', zipfile.ZIP_DEFLATED) as out:
        for n in names:
            info = zipfile.ZipInfo(n, date_time=infos[n].date_time)
            info.compress_type = infos[n].compress_type
            info.external_attr = infos[n].external_attr
            out.writestr(info, parts[n])

    print(f'styles: {len(unlocked_for)} unlocked variants added (cellXfs now {len(xfs)})')
    print(f'cells: {touched} restyled, {created} created')
    print(f'written: {DST}')


if __name__ == '__main__':
    main()
