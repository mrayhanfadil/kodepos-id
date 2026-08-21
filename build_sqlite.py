#!/usr/bin/env python3
"""
Build SQLite database from kodepos.json with decomposed Kemendagri fields.

Schema:
  wilayah(
    kode_wilayah TEXT PRIMARY KEY,   -- 13-digit Kemendagri, e.g. '95.04.32.2009'
    kode_pos     TEXT NOT NULL,      -- 5-digit postal code
    desa         TEXT NOT NULL,      -- village/kelurahan name
    kecamatan    TEXT NOT NULL,      -- district name
    kabupaten    TEXT NOT NULL,      -- regency/city name
    provinsi     TEXT NOT NULL,      -- province name
    dt2          TEXT NOT NULL,      -- 'Kabupaten' or 'Kota'
    is_kelurahan INTEGER NOT NULL,   -- 1 if last 4 digits start with 1 (urban), 0 if 2 (rural)
    prov_code    TEXT NOT NULL,      -- first 2 digits of kode_wilayah
    kab_code     TEXT NOT NULL,      -- digits 4-5
    kec_code     TEXT NOT NULL,      -- digits 7-8
    desa_code    TEXT NOT NULL,      -- digits 10-13
    full_code    TEXT NOT NULL,      -- all 13 digits no dots
  )

Indexes:
  - kode_pos
  - (prov_code, kab_code)
  - (prov_code, kab_code, kec_code)
  - kecamatan
  - kabupaten
  - provinsi
  - (prov_code, kabupaten)
"""
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path("/home/fadil/projects/kodepos-scraper")
JSON_PATH = ROOT / "kodepos.json"
DB_PATH = ROOT / "kodepos.db"


def build():
    rows = json.load(open(JSON_PATH))
    print(f"Loaded {len(rows)} rows from {JSON_PATH.name}")

    if DB_PATH.exists():
        DB_PATH.unlink()

    con = sqlite3.connect(DB_PATH)
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

    bad = 0
    for r in rows:
        kw = r["kode_wilayah"] or ""
        try:
            # '95.04.32.2006' -> ('95','04','32','2006')
            parts = kw.split(".")
            if len(parts) != 4:
                bad += 1
                continue
            prov, kab, kec, desa = parts
            full = "".join(parts)
            is_kelurahan = 1 if desa.startswith("1") else 0
            cur.execute("""
                INSERT OR IGNORE INTO wilayah
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                kw, r["kode_pos"], r["desa"], r["kecamatan"],
                r["kabupaten"], r["provinsi"], r["dt2"],
                is_kelurahan, prov, kab, kec, desa, full,
            ))
        except Exception as e:
            bad += 1
            if bad < 5:
                print(f"BAD: {r} -> {e}")

    con.commit()

    # ANALYZE so query planner uses indexes
    cur.execute("ANALYZE;")
    con.commit()

    # Verify counts
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

    print(f"\n--- wilayah table ---")
    print(f"total rows           : {total}")
    print(f"unique kode_pos      : {kp}")
    print(f"unique provinsi      : {pv}")
    print(f"unique kab/kota      : {kb}")
    print(f"unique kecamatan     : {kc}")
    print(f"kelurahan            : {kel}")
    print(f"desa                 : {desa_}")
    print(f"bad rows skipped     : {bad}")
    print(f"DB size              : {DB_PATH.stat().st_size/1024/1024:.2f} MB")

    con.close()


if __name__ == "__main__":
    build()