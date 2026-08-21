#!/usr/bin/env python3
"""
Merge the new scrape (wilayah_desa_papua.jsonl) into the master
kodepos_parsed.csv + kodepos.json + kodepos.db.

Dedupe by kode_wilayah (primary key). New rows go in, existing rows updated
with fresh nama/desa from the per-provinsi scrape (since it has full names
without truncation). Reassign source_page to track origin.

After merge:
- kodepos_parsed.csv (regenerated with all parsed fields)
- kodepos.json
- kodepos.db
- Backup of old master to kodepos_parsed.csv.bak
"""
import csv
import json
import re
import sqlite3
from pathlib import Path
from datetime import datetime

ROOT = Path("/home/fadil/projects/kodepos-scraper")
MASTER_CSV = ROOT / "kodepos_parsed.csv"
MASTER_JSON = ROOT / "kodepos.json"
MASTER_DB = ROOT / "kodepos.db"
NEW_JSONL = ROOT / "wilayah_desa_papua.jsonl"
OUT_CSV = ROOT / "kodepos_parsed.csv"
OUT_JSON = ROOT / "kodepos.json"
OUT_DB = ROOT / "kodepos.db"

# Backup
def backup():
    for p in [MASTER_CSV, MASTER_JSON, MASTER_DB]:
        bak = p.with_suffix(p.suffix + ".bak")
        if p.exists() and not bak.exists():
            bak.write_bytes(p.read_bytes())
            print(f"Backup: {bak}")


def parse_kode(kw: str) -> dict:
    if not kw or kw.count(".") != 3:
        return {"prov_code": "", "kab_code": "", "kec_code": "",
                "desa_code": "", "full_code": "",
                "is_kelurahan": None, "is_desa": None}
    p, k, c, d = kw.split(".")
    full = p + k + c + d
    is_kel = d.startswith("1")
    return {
        "prov_code": p, "kab_code": k, "kec_code": c, "desa_code": d,
        "full_code": full,
        "is_kelurahan": 1 if is_kel else 0,
        "is_desa": 0 if is_kel else 1,
    }


def main():
    backup()

    # Load master
    print("Loading master...")
    master = list(csv.DictReader(open(MASTER_CSV)))
    print(f"  master rows: {len(master)}")
    by_kw = {r["kode_wilayah"]: r for r in master}

    # Load new
    print("Loading new scrape...")
    new_rows = [json.loads(l) for l in open(NEW_JSONL)]
    print(f"  new rows: {len(new_rows)}")

    added = 0
    updated = 0
    unchanged = 0
    new_kw_seen = set()
    for r in new_rows:
        kw = r["kode_wilayah"]
        if not kw or kw.count(".") != 3:
            continue
        new_kw_seen.add(kw)
        meta = parse_kode(kw)
        if kw in by_kw:
            # Update nama_desa if it's currently truncated (ends with apostrophe)
            cur = by_kw[kw]
            if cur["desa"].endswith("'") and len(cur["desa"]) < 5:
                cur["desa"] = r["desa"]
                cur["source_page"] = r["source_page"]
                updated += 1
            else:
                unchanged += 1
        else:
            # Add new row
            by_kw[kw] = {
                "no": str(len(by_kw) + 1),  # will renumber later
                "kode_pos": r["kode_pos"],
                "kode_wilayah": kw,
                "prov_code": meta["prov_code"],
                "kab_code": meta["kab_code"],
                "kec_code": meta["kec_code"],
                "desa_code": meta["desa_code"],
                "full_code": meta["full_code"],
                "is_kelurahan": str(meta["is_kelurahan"]),
                "is_desa": str(meta["is_desa"]),
                "desa": r["desa"],
                "kecamatan": r["kecamatan"],
                "dt2": r["dt2"],
                "kabupaten": r["kabupaten"],
                "provinsi": r["provinsi"],
                "source_page": str(r["source_page"]),
            }
            added += 1

    # Re-number 'no' to be sequential (1..N) by provinsi order
    print(f"  added: {added}")
    print(f"  updated: {updated}")
    print(f"  unchanged: {unchanged}")
    print(f"  total unique kw: {len(by_kw)}")

    # Reorder by source_page (page=1..418 from original scrape) then by no within
    # Use original source_page where available, otherwise set to 9999 (placeholder)
    # Actually: rows with no source_page = new; assign to page based on province + sort

    # Build a sortable index: (prov_code, no_within_prov) by re-running the
    # original scrape's page-by-page ordering. Easier: just sort by
    # (prov_code, full_code) to keep deterministic order.
    rows_out = sorted(by_kw.values(),
                       key=lambda r: (r["prov_code"], r["full_code"]))
    # Reassign 'no' sequentially
    for i, r in enumerate(rows_out, 1):
        r["no"] = str(i)

    fieldnames = ["no", "kode_pos", "kode_wilayah", "prov_code", "kab_code",
                  "kec_code", "desa_code", "full_code", "is_kelurahan", "is_desa",
                  "desa", "kecamatan", "dt2", "kabupaten", "provinsi", "source_page"]

    # Write CSV
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows_out)
    print(f"\nWrote {OUT_CSV.name} ({OUT_CSV.stat().st_size/1024/1024:.2f} MB)")

    # Write JSON (clean version without source_page_filter)
    json_rows = []
    for r in rows_out:
        json_rows.append({
            "no": int(r["no"]),
            "kode_pos": r["kode_pos"],
            "desa": r["desa"],
            "kode_wilayah": r["kode_wilayah"],
            "kecamatan": r["kecamatan"],
            "dt2": r["dt2"],
            "kabupaten": r["kabupaten"],
            "provinsi": r["provinsi"],
            "source_page": int(r["source_page"]) if r["source_page"].isdigit() else 0,
        })
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(json_rows, f, ensure_ascii=False, indent=2)
    print(f"Wrote {OUT_JSON.name} ({OUT_JSON.stat().st_size/1024/1024:.2f} MB)")

    # Rebuild SQLite
    print("Rebuilding SQLite...")
    if OUT_DB.exists():
        OUT_DB.unlink()
    con = sqlite3.connect(OUT_DB)
    cur = con.cursor()
    cur.executescript("""
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

        CREATE INDEX idx_kode_pos        ON wilayah(kode_pos);
        CREATE INDEX idx_prov_kab        ON wilayah(prov_code, kab_code);
        CREATE INDEX idx_prov_kab_kec    ON wilayah(prov_code, kab_code, kec_code);
        CREATE INDEX idx_kecamatan       ON wilayah(kecamatan);
        CREATE INDEX idx_kabupaten       ON wilayah(kabupaten);
        CREATE INDEX idx_provinsi        ON wilayah(provinsi);
        CREATE INDEX idx_prov_name       ON wilayah(prov_code, kabupaten);
    """)
    for r in rows_out:
        cur.execute("""
            INSERT OR REPLACE INTO wilayah
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (
            r["kode_wilayah"], r["kode_pos"], r["desa"], r["kecamatan"],
            r["kabupaten"], r["provinsi"], r["dt2"],
            int(r["is_kelurahan"]), r["prov_code"], r["kab_code"],
            r["kec_code"], r["desa_code"], r["full_code"],
        ))
    con.commit()
    cur.execute("ANALYZE;")
    con.commit()

    # Verify
    cur.execute("SELECT COUNT(*) FROM wilayah")
    total = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT kode_pos) FROM wilayah")
    kp = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT prov_code) FROM wilayah")
    pv = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT prov_code || kab_code) FROM wilayah")
    kb = cur.fetchone()[0]
    cur.execute("SELECT COUNT(DISTINCT prov_code || kab_code || kec_code) FROM wilayah")
    kc = cur.fetchone()[0]
    cur.execute("SELECT SUM(is_kelurahan), COUNT(*) - SUM(is_kelurahan) FROM wilayah")
    kel, desa_ = cur.fetchone()
    con.close()

    print(f"\n--- wilayah table ---")
    print(f"total rows           : {total}")
    print(f"unique kode_pos      : {kp}")
    print(f"unique provinsi      : {pv}")
    print(f"unique kab/kota      : {kb}")
    print(f"unique kecamatan     : {kc}")
    print(f"kelurahan            : {kel}")
    print(f"desa                 : {desa_}")
    print(f"DB size              : {OUT_DB.stat().st_size/1024/1024:.2f} MB")


if __name__ == "__main__":
    main()