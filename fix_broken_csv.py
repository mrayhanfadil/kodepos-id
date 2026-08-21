"""Fix the broken 'db Area - check.csv' by re-joining it to the master kodepos_parsed.csv
on `kode_wilayah` (column 3 in the broken CSV, column 3 in master too).

The broken CSV:
  - Only has 12 columns (missing kecamatan, dt2, kabupaten, provinsi, source_page)
  - HTML entities like &#039; need decoding
  - Some quoted fields lost their close quote, splitting kecamatan

Output: a fully restored 16-column CSV with all fields complete + HTML-decoded.
"""
import csv
import html
import re
import sys
from pathlib import Path

BROKEN = Path('/home/fadil/.hermes/cache/documents/doc_8541ba8ce761_db Area - check.csv')
MASTER = Path('/home/fadil/projects/kodepos-scraper/kodepos_parsed.csv')
OUT = Path('/home/fadil/projects/kodepos-scraper/db_area_check_fixed.csv')


def clean_cell(s: str) -> str:
    """Strip whitespace and decode HTML entities."""
    s = (s or "").strip()
    if not s:
        return ""
    # Decode common HTML entities (nomor.net uses &#039; for ', &amp; for &, etc.)
    s = html.unescape(s)
    return s


def fix_quoted_split(line: str) -> list[str]:
    """Re-merge kecamatan field when its close quote was lost.

    The broken CSV embeds kecamatan as a quoted field after desa:
       ...<desa>,"<kecamatan> (..., ...)
    When the close quote is missing, the comma INSIDE parens splits kecamatan.
    Detect this pattern and re-merge the trailing chunks into kecamatan.
    """
    # Quick heuristic: the 11th field is kecamatan (count from 0).
    # If we have >= 12 fields, the 12th..N fields (if any) all belong to kecamatan.
    cells = list(csv.reader([line]))[0] if False else _split_csv(line)
    if len(cells) >= 12:
        # Field index 10 = desa, 11+ = kecamatan that got split
        desa = cells[10]
        kec_parts = cells[11:]
        # If the first kecamatan chunk doesn't end with quote, treat all as one kecamatan
        # The original CSV should have the kecamatan in field 11 and nothing else
        merged_kec = ",".join(kec_parts)
        # Strip stray leading quote
        if merged_kec.startswith('"'):
            merged_kec = merged_kec[1:]
        # Strip trailing comma if any
        merged_kec = merged_kec.rstrip(",").rstrip()
        # If still ends without closing quote, that's OK — we truncated from source
        cells = cells[:11] + [merged_kec]
    return cells


def _split_csv(line: str) -> list[str]:
    """Robust CSV splitter that handles embedded commas inside double quotes."""
    out = []
    cur = []
    in_quote = False
    for ch in line:
        if ch == '"':
            in_quote = not in_quote
        elif ch == ',' and not in_quote:
            out.append(''.join(cur))
            cur = []
        else:
            cur.append(ch)
    out.append(''.join(cur))
    return out


def main():
    # Load master into a lookup by full_code (10-digit Kemendagri) AND by kode_wilayah
    master_idx = {}
    with MASTER.open() as f:
        r = csv.DictReader(f)
        for row in r:
            kw = row['kode_wilayah']
            master_idx[kw] = row

    print(f"Master loaded: {len(master_idx)} rows")

    fixed = []
    missing = []

    with BROKEN.open('rb') as f:
        raw = f.read().decode('utf-8', errors='replace')
    # Normalize line endings
    raw = raw.replace('\r\n', '\n').replace('\r', '\n')
    lines = raw.split('\n')

    for ln in lines:
        if not ln.strip():
            continue
        cells = fix_quoted_split(ln)
        if len(cells) < 11:
            continue
        # Decode every cell
        cells = [clean_cell(c) for c in cells]

        # Field map from broken CSV:
        # 0=no, 1=kode_pos, 2=kode_wilayah, 3=prov_code, 4=kab_code, 5=kec_code,
        # 6=desa_code, 7=full_code, 8=is_kelurahan, 9=is_desa, 10=desa, 11=kecamatan (if present)
        no = cells[0]
        kode_pos = cells[1]
        kode_wilayah = cells[2]
        desa = cells[10]
        kecamatan_partial = cells[11] if len(cells) >= 12 else ""

        # Look up in master by kode_wilayah
        ref = master_idx.get(kode_wilayah)
        if not ref:
            missing.append((no, kode_wilayah, desa, kecamatan_partial))
            continue

        # The broken CSV's `desa` and `kecamatan` fields are known-truncated
        # upstream (limited char width at export time). Always pull from
        # master as the authoritative source.
        desa = clean_cell(ref['desa'])
        kecamatan = clean_cell(ref['kecamatan'])
        dt2 = clean_cell(ref['dt2'])
        kabupaten = clean_cell(ref['kabupaten'])
        provinsi = clean_cell(ref['provinsi'])
        source_page = clean_cell(ref['source_page'])
        prov_code = clean_cell(ref['prov_code'])
        kab_code = clean_cell(ref['kab_code'])
        kec_code = clean_cell(ref['kec_code'])
        desa_code = clean_cell(ref['desa_code'])
        full_code = clean_cell(ref['full_code'])
        is_kelurahan = clean_cell(ref['is_kelurahan'])
        is_desa = clean_cell(ref['is_desa'])

        fixed.append({
            'no': no,
            'kode_pos': kode_pos,
            'kode_wilayah': kode_wilayah,
            'prov_code': prov_code,
            'kab_code': kab_code,
            'kec_code': kec_code,
            'desa_code': desa_code,
            'full_code': full_code,
            'is_kelurahan': is_kelurahan,
            'is_desa': is_desa,
            'desa': desa,
            'kecamatan': kecamatan,
            'dt2': dt2,
            'kabupaten': kabupaten,
            'provinsi': provinsi,
            'source_page': source_page,
        })

    # Write output
    fieldnames = ['no', 'kode_pos', 'kode_wilayah', 'prov_code', 'kab_code',
                  'kec_code', 'desa_code', 'full_code', 'is_kelurahan', 'is_desa',
                  'desa', 'kecamatan', 'dt2', 'kabupaten', 'provinsi', 'source_page']
    with OUT.open('w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(fixed)

    print(f"Fixed: {len(fixed)}")
    print(f"Missing (not in master): {len(missing)}")
    for m in missing[:5]:
        print(f"  {m}")
    print(f"\nOutput: {OUT}  ({OUT.stat().st_size/1024:.1f} KB)")

    # Sample verification: print first 3 and the Palengaan row
    print("\n--- Sample (first 3) ---")
    for r in fixed[:3]:
        print(f"  {r['kode_wilayah']}  {r['kode_pos']}  {r['desa']!r}  |  {r['kecamatan']!r}  |  {r['kabupaten']}")
    print("\n--- Sample (Palengaan rows) ---")
    for r in fixed:
        if r['kode_wilayah'] == '35.28.06.2004':
            print(f"  {r['kode_wilayah']}  {r['kode_pos']}  {r['desa']!r}  |  {r['kecamatan']!r}  |  {r['kabupaten']}")
            break


if __name__ == "__main__":
    main()