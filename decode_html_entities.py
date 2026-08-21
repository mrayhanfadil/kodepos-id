#!/usr/bin/env python3
"""
Decode HTML entities in all kodepos files (CSV, JSON, SQLite).

Handles:
- Numeric entities: &#039; → '   (apostrophe)
- Numeric hex:     &#x27; → '
- Named:           &amp; &lt; &gt; &quot; &apos; &nbsp; etc
- Multi-byte UTF-8 sequences preserved

Outputs new files at:
  - kodepos_parsed.csv     (9.3 MB)
  - kodepos_parsed.json    (33 MB)
  - kodepos.csv            (7 MB)
  - kodepos.json           (21 MB)
  - kodepos.db             (22 MB SQLite)
  - db_area_check_fixed.csv (72 KB)
"""
import csv
import html
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path("/home/fadil/projects/kodepos-scraper")


def decode(text: str) -> str:
    if not text:
        return text
    return html.unescape(text)


def fix_csv(in_path: Path, out_path: Path) -> tuple[int, int]:
    """Decode HTML entities in CSV. Returns (rows, fixed_cells)."""
    fixed_cells = 0
    n_rows = 0
    # Read everything into memory first so we can safely overwrite the same path.
    rows_in = list(csv.reader(in_path.open("r", encoding="utf-8", newline="")))
    with out_path.open("w", encoding="utf-8", newline="") as fout:
        writer = csv.writer(fout)
        for row in rows_in:
            new_row = []
            for cell in row:
                if cell and ("&" in cell):
                    new_cell = decode(cell)
                    if new_cell != cell:
                        fixed_cells += 1
                    new_row.append(new_cell)
                else:
                    new_row.append(cell)
            writer.writerow(new_row)
            n_rows += 1
    return n_rows, fixed_cells


def fix_json(in_path: Path, out_path: Path) -> tuple[int, int]:
    """Decode HTML entities in JSON. Returns (records, fixed_fields)."""
    data = json.load(in_path.open("r", encoding="utf-8"))
    fixed = 0
    if isinstance(data, list):
        for rec in data:
            for k, v in list(rec.items()):
                if isinstance(v, str) and "&" in v:
                    new_v = decode(v)
                    if new_v != v:
                        fixed += 1
                    rec[k] = new_v
        n = len(data)
    else:
        n = 0
    # If in_path == out_path, write to temp then replace
    if in_path == out_path:
        tmp = out_path.with_suffix(out_path.suffix + ".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(out_path)
    else:
        with out_path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    return n, fixed


def fix_db(in_path: Path, out_path: Path) -> tuple[int, int]:
    """Rebuild SQLite, decoding HTML entities in text fields."""
    if in_path == out_path:
        # Write to a tmp path first, then replace, so we don't truncate the source.
        tmp_path = out_path.with_suffix(out_path.suffix + ".tmp")
        if tmp_path.exists():
            tmp_path.unlink()
        con = sqlite3.connect(str(in_path))
        cur = con.cursor()
        rows = list(cur.execute("SELECT * FROM wilayah"))
        con.close()
        out = sqlite3.connect(str(tmp_path))
        out.executescript("""
            CREATE TABLE wilayah (
                kode_wilayah TEXT PRIMARY KEY,
                kode_pos     TEXT NOT NULL,
                desa         TEXT NOT NULL,
                kecamatan    TEXT NOT NULL,
                kabupaten    TEXT NOT NULL,
                provinsi     TEXT NOT NULL,
                dt2          TEXT NOT NULL,
                is_kelurahan INTEGER NOT NULL,
                prov_code    TEXT NOT NULL,
                kab_code     TEXT NOT NULL,
                kec_code     TEXT NOT NULL,
                desa_code    TEXT NOT NULL,
                full_code    TEXT NOT NULL
            );
            CREATE INDEX idx_kode_pos      ON wilayah(kode_pos);
            CREATE INDEX idx_prov_kab      ON wilayah(prov_code, kab_code);
            CREATE INDEX idx_prov_kab_kec  ON wilayah(prov_code, kab_code, kec_code);
            CREATE INDEX idx_kecamatan     ON wilayah(kecamatan);
            CREATE INDEX idx_kabupaten     ON wilayah(kabupaten);
            CREATE INDEX idx_provinsi      ON wilayah(provinsi);
            CREATE INDEX idx_prov_name     ON wilayah(prov_code, kabupaten);
        """)
        oc = out.cursor()
        fixed = 0
        for row in rows:
            row = list(row)
            for i in range(2, 7):  # text cols 2..6 (desa, kecamatan, kabupaten, provinsi, dt2)
                v = row[i]
                if v and "&" in v:
                    new_v = decode(v)
                    if new_v != v:
                        fixed += 1
                    row[i] = new_v
            oc.execute("INSERT INTO wilayah VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
        out.commit()
        oc.execute("ANALYZE")
        out.commit()
        out.close()
        tmp_path.replace(out_path)
        return 0, fixed
    # in_path != out_path: same logic
    tmp_path = out_path
    if tmp_path.exists():
        tmp_path.unlink()
    con = sqlite3.connect(str(in_path))
    cur = con.cursor()
    out = sqlite3.connect(str(tmp_path))
    out.executescript("""
        CREATE TABLE wilayah (
            kode_wilayah TEXT PRIMARY KEY,
            kode_pos     TEXT NOT NULL,
            desa         TEXT NOT NULL,
            kecamatan    TEXT NOT NULL,
            kabupaten    TEXT NOT NULL,
            provinsi     TEXT NOT NULL,
            dt2          TEXT NOT NULL,
            is_kelurahan INTEGER NOT NULL,
            prov_code    TEXT NOT NULL,
            kab_code     TEXT NOT NULL,
            kec_code     TEXT NOT NULL,
            desa_code    TEXT NOT NULL,
            full_code    TEXT NOT NULL
        );
        CREATE INDEX idx_kode_pos      ON wilayah(kode_pos);
        CREATE INDEX idx_prov_kab      ON wilayah(prov_code, kab_code);
        CREATE INDEX idx_prov_kab_kec  ON wilayah(prov_code, kab_code, kec_code);
        CREATE INDEX idx_kecamatan     ON wilayah(kecamatan);
        CREATE INDEX idx_kabupaten     ON wilayah(kabupaten);
        CREATE INDEX idx_provinsi      ON wilayah(provinsi);
        CREATE INDEX idx_prov_name     ON wilayah(prov_code, kabupaten);
    """)
    oc = out.cursor()
    fixed = 0
    for row in cur.execute("SELECT * FROM wilayah"):
        row = list(row)
        for i in range(2, 7):
            v = row[i]
            if v and "&" in v:
                new_v = decode(v)
                if new_v != v:
                    fixed += 1
                row[i] = new_v
        oc.execute("INSERT INTO wilayah VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", row)
    out.commit()
    oc.execute("ANALYZE")
    out.commit()
    con.close()
    out.close()
    return 0, fixed


def fix_jsonl(in_path: Path, out_path: Path) -> tuple[int, int]:
    """Decode HTML entities in JSONL (one JSON per line)."""
    if not in_path.exists():
        return 0, 0
    fixed = 0
    n = 0
    # Read all lines, then write back, to safely overwrite same path
    lines = in_path.read_text(encoding="utf-8").splitlines()
    new_lines = []
    for line in lines:
        if not line.strip():
            new_lines.append(line)
            continue
        try:
            rec = json.loads(line)
        except Exception:
            new_lines.append(line)
            continue
        for k, v in list(rec.items()):
            if isinstance(v, str) and "&" in v:
                new_v = decode(v)
                if new_v != v:
                    fixed += 1
                rec[k] = new_v
        new_lines.append(json.dumps(rec, ensure_ascii=False))
        n += 1
    if in_path == out_path:
        tmp = out_path.with_suffix(out_path.suffix + ".tmp")
        tmp.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
        tmp.replace(out_path)
    else:
        out_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")
    return n, fixed


def main():
    pairs = [
        ("kodepos_parsed.csv", "kodepos_parsed.csv"),
        ("kodepos.csv",        "kodepos.csv"),
        ("db_area_check_fixed.csv", "db_area_check_fixed.csv"),
    ]
    print("=== Decoding HTML entities ===\n")

    for fname, _ in pairs:
        p = ROOT / fname
        if not p.exists():
            print(f"SKIP {fname} (not found)")
            continue
        bak = p.with_suffix(p.suffix + ".pre_html")
        if not bak.exists():
            bak.write_bytes(p.read_bytes())
            print(f"Backup: {bak.name}")
        rows, fixed = fix_csv(p, p)
        print(f"  {fname:35s} rows={rows:>6}  fixed_cells={fixed:>5}")

    # JSON files
    for fname in ["kodepos.json", "kodepos_parsed.json"]:
        p = ROOT / fname
        if not p.exists():
            print(f"SKIP {fname} (not found)")
            continue
        bak = p.with_suffix(p.suffix + ".pre_html")
        if not bak.exists():
            bak.write_bytes(p.read_bytes())
            print(f"Backup: {bak.name}")
        rows, fixed = fix_json(p, p)
        print(f"  {fname:35s} records={rows:>6}  fixed_fields={fixed:>5}")

    # JSONL files (Papua per-provinsi scrape)
    for fname in ["wilayah_desa_papua.jsonl", "kodepos_raw.jsonl"]:
        p = ROOT / fname
        if not p.exists():
            print(f"SKIP {fname} (not found)")
            continue
        bak = p.with_suffix(p.suffix + ".pre_html")
        if not bak.exists():
            bak.write_bytes(p.read_bytes())
            print(f"Backup: {bak.name}")
        rows, fixed = fix_jsonl(p, p)
        print(f"  {fname:35s} lines={rows:>6}  fixed_fields={fixed:>5}")

    # SQLite
    db = ROOT / "kodepos.db"
    if db.exists():
        bak = db.with_suffix(db.suffix + ".pre_html")
        if not bak.exists():
            bak.write_bytes(db.read_bytes())
            print(f"Backup: {bak.name}")
        _, fixed = fix_db(db, db)
        # Verify
        con = sqlite3.connect(str(db))
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM wilayah")
        n = cur.fetchone()[0]
        cur.execute("SELECT COUNT(*) FROM wilayah WHERE desa LIKE '%&%' OR kecamatan LIKE '%&%'")
        remaining = cur.fetchone()[0]
        con.close()
        print(f"  kodepos.db        rows={n:>6}  fixed_fields={fixed:>5}  remaining_entities={remaining}")

    print("\nDone. Verify with:")
    print("  grep -c '&' kodepos_parsed.csv   # should be 0 in non-header cells")
    print("  grep -c '&#039;' kodepos_parsed.csv   # should be 0")


if __name__ == "__main__":
    main()