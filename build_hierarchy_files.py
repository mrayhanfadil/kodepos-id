"""Demo: show the 3-level hierarchy as the user described."""
import csv
from collections import defaultdict
from pathlib import Path

ROOT = Path("/home/fadil/projects/kodepos-scraper")

# Load parsed CSV
rows = list(csv.DictReader(open(ROOT / "kodepos_parsed.csv")))
print(f"Loaded {len(rows)} rows from kodepos_parsed.csv\n")

# Level 1: PROVINSI
print("=" * 80)
print("LEVEL 1: PROVINSI (2-digit prov_code)")
print("=" * 80)
prov_set = sorted({(r["prov_code"], r["provinsi"]) for r in rows}, key=lambda x: x[0])
print(f"{'KODE':<6}  NAMA PROVINSI")
print("-" * 60)
for pc, pn in prov_set:
    print(f"{pc:<6}  {pn}")

# Sample showing the 19.71 case
print()
print("=" * 80)
print("SAMPLE: KOTA PANGKAL PINANG (kode 19.71)")
print("=" * 80)
samples = [r for r in rows if r["kode_wilayah"].startswith("19.71.")]
print(f"Total desa/kelurahan: {len(samples)}")
for r in samples[:5]:
    print(f"  {r['kode_wilayah']:<14}  {r['desa']}  /  {r['kecamatan']}  ({r['kabupaten']}, {r['provinsi']})")
# kecamatan level (drop last 2 segments) — extract distinct kec codes
kec_seen = sorted({r["kode_wilayah"][:8] for r in samples})
print(f"Distinct kecamatan in 19.71: {len(kec_seen)}")
for k in kec_seen:
    n = [r for r in samples if r["kode_wilayah"].startswith(k)][0]
    print(f"  {k}  {n['kecamatan']}")

# Level 2: KABUPATEN / KOTA (4-digit full_code)
print()
print("=" * 80)
print("LEVEL 2: KABUPATEN / KOTA (4-digit full_code = prov_code+kab_code)")
print("=" * 80)
kab_set = sorted({
    (r["prov_code"], r["kab_code"], r["prov_code"] + r["kab_code"], r["dt2"], r["kabupaten"])
    for r in rows
}, key=lambda x: (x[0], x[1]))
print(f"Total: {len(kab_set)} kab/kota")
print(f"{'PROV':<6} {'KAB':<6} {'FULL':<8} {'TIPE':<12} NAMA KABUPATEN/KOTA")
print("-" * 70)
for pc, kc, fc, tipe, nama in kab_set[:5]:
    print(f"{pc:<6} {kc:<6} {fc:<8} {tipe:<12} {nama}")
print(f"... ({len(kab_set)} total)")

# Sample showing 13.71.10 case
print()
print("=" * 80)
print("SAMPLE: KECAMATAN NANGGALO (kode 13.71.10) — KOTA PADANG, SUMBAR")
print("=" * 80)
samples = [r for r in rows if r["kode_wilayah"].startswith("13.71.10")]
print(f"Total rows under 13.71.10: {len(samples)}")
for r in samples[:5]:
    print(f"  {r['kode_wilayah']:<14}  {r['desa']}  /  {r['kecamatan']}  /  {r['kabupaten']}  /  {r['provinsi']}")

# Level 3: KECAMATAN (6-digit full_code)
print()
print("=" * 80)
print("LEVEL 3: KECAMATAN (6-digit full_code = prov_code+kab_code+kec_code)")
print("=" * 80)
kec_set = sorted({
    (r["prov_code"], r["kab_code"], r["kec_code"],
     r["prov_code"] + r["kab_code"] + r["kec_code"],
     r["kecamatan"])
    for r in rows
}, key=lambda x: (x[0], x[1], x[2]))
print(f"Total: {len(kec_set)} kecamatan")
print(f"{'PROV':<6} {'KAB':<6} {'KEC':<6} {'FULL':<10} NAMA KECAMATAN")
print("-" * 70)
for pc, kc, c, fc, nama in kec_set[:5]:
    print(f"{pc:<6} {kc:<6} {c:<6} {fc:<10} {nama}")
print(f"... ({len(kec_set)} total)")

# Sample showing the user's exact 13.71.10.1001 case
print()
print("=" * 80)
print("SAMPLE: SURAU GADANG (kode 13.71.10.1001) — KEC. NANGGALO")
print("=" * 80)
samples = [r for r in rows if r["kode_wilayah"].startswith("13.71.10")]
print(f"Total rows under 13.71.10: {len(samples)}")
for r in samples[:5]:
    print(f"  {r['kode_wilayah']:<14}  {r['desa']}  /  {r['kecamatan']}  /  {r['kabupaten']}  /  {r['provinsi']}")

# Build the 3-level hierarchy as JSONL files
print()
print("=" * 80)
print("Building 3 separate hierarchy files...")
print("=" * 80)

# 1. Provinsi (38 rows)
with open(ROOT / "wilayah_provinsi_v2.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["kode", "nama_provinsi"])
    for pc, pn in prov_set:
        w.writerow([pc, pn])
print(f"  wilayah_provinsi_v2.csv: {len(prov_set)} rows")

# 2. Kabupaten/Kota (514 rows)
with open(ROOT / "wilayah_kota_v2.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["prov_code", "kab_code", "full_code", "tipe", "nama_kab_kota"])
    for pc, kc, fc, tipe, nama in kab_set:
        w.writerow([pc, kc, fc, tipe, nama])
print(f"  wilayah_kota_v2.csv: {len(kab_set)} rows")

# 3. Kecamatan (7,277 rows)
with open(ROOT / "wilayah_kecamatan_v2.csv", "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["prov_code", "kab_code", "kec_code", "full_code", "nama_kecamatan"])
    for pc, kc, c, fc, nama in kec_set:
        w.writerow([pc, kc, c, fc, nama])
print(f"  wilayah_kecamatan_v2.csv: {len(kec_set)} rows")

print()
print("Done. Example query:")
print("  sqlite3 kodepos.db \"SELECT * FROM wilayah WHERE kode_wilayah LIKE '13.71.10%';\"")
