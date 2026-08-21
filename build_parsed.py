#!/usr/bin/env python3
"""
Generate the parsed versions of kodepos.json / kodepos.csv that include
the decomposed Kemendagri fields so consumers without SQLite can still
join by (prov_code, kab_code, kec_code, desa_code).

Outputs:
  kodepos_parsed.json
  kodepos_parsed.csv
"""
import csv
import json
from pathlib import Path

ROOT = Path("/home/fadil/projects/kodepos-scraper")
SRC = ROOT / "kodepos.json"
OUT_JSON = ROOT / "kodepos_parsed.json"
OUT_CSV = ROOT / "kodepos_parsed.csv"


def parse_kode(kw: str) -> dict:
    if not kw or kw.count(".") != 3:
        return {"prov_code": "", "kab_code": "", "kec_code": "",
                "desa_code": "", "full_code": "",
                "is_kelurahan": None, "is_desa": None}
    p, k, c, d = kw.split(".")
    full = p + k + c + d
    is_kel = d.startswith("1")
    return {
        "prov_code": p,
        "kab_code": k,
        "kec_code": c,
        "desa_code": d,
        "full_code": full,
        "is_kelurahan": 1 if is_kel else 0,
        "is_desa": 0 if is_kel else 1,
    }


def main():
    rows = json.load(open(SRC))
    print(f"Loaded {len(rows)} rows from {SRC.name}")

    parsed = []
    for r in rows:
        kw = r.get("kode_wilayah", "") or ""
        meta = parse_kode(kw)
        parsed.append({**r, **meta})

    # JSON
    with OUT_JSON.open("w", encoding="utf-8") as f:
        json.dump(parsed, f, ensure_ascii=False, indent=2)

    # CSV with consistent column order
    fieldnames = ["no", "kode_pos", "kode_wilayah", "prov_code", "kab_code",
                  "kec_code", "desa_code", "full_code", "is_kelurahan", "is_desa",
                  "desa", "kecamatan", "dt2", "kabupaten", "provinsi", "source_page"]
    with OUT_CSV.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in parsed:
            w.writerow({k: r.get(k, "") for k in fieldnames})

    print(f"Wrote {OUT_JSON.name} ({OUT_JSON.stat().st_size/1024/1024:.2f} MB)")
    print(f"Wrote {OUT_CSV.name}  ({OUT_CSV.stat().st_size/1024/1024:.2f} MB)")

    # Stats
    kel = sum(1 for r in parsed if r["is_kelurahan"] == 1)
    desa = sum(1 for r in parsed if r["is_desa"] == 1)
    print(f"kelurahan: {kel}  desa: {desa}")


if __name__ == "__main__":
    main()