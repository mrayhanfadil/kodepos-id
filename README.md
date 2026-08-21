# Kode Pos Indonesia (Indonesian Postal Codes + Kemendagri Region Codes)

> **83,145 desa / kelurahan** across **38 provinsi** + **514 kabupaten/kota** + **7,257 kecamatan**, each linked to its 13-digit **kode wilayah Kemendagri** and **5-digit kode pos** — sourced from [nomor.net](https://www.nomor.net) (Kepmendagri RI No. 100.1.1-6117/2022 & Permendagri No. 58/2021).

Last scraped: 2026-08-21 (Asia/Jakarta).

---

## Files

| File | Size | Rows | Format | Purpose |
|---|---|---|---|---|
| **`kodepos.db`** | 23 MB | 83,145 | SQLite 3 | Fast queries with indexes on kode_wilayah, kode_pos, kecamatan, kabupaten, provinsi, and `(prov_code, kab_code, kec_code)` |
| `kodepos_parsed.csv` | 9.3 MB | 83,146 | CSV | Flat data with decomposed Kemendagri fields (no SQLite needed) |
| `kodepos_parsed.json` | 33 MB | 83,145 | JSON array | Same as above, JSON |
| `kodepos.csv` | 7.0 MB | 83,146 | CSV | Original scrape output (raw columns from nomor.net) |
| `kodepos.json` | 20 MB | 83,145 | JSON array | Same as `kodepos.csv` |
| `kodepos_raw.jsonl` | 17 MB | 83,145 | JSONL | Intermediate scrape log (resumeable) |
| `scrape.py` | 14 KB | — | Python | Concurrent scrape script (6 threads, resumeable) |
| `build_sqlite.py` | 4.7 KB | — | Python | Build SQLite from JSON |
| `build_parsed.py` | 2.3 KB | — | Python | Build parsed CSV/JSON from JSON |

Pick the format that fits your stack:

- **Postgres / MySQL / DuckDB / pandas** → `kodepos_parsed.csv`
- **Anything with SQLite** → `kodepos.db`
- **JS / TS / Deno / Bun** → `kodepos_parsed.json`
- **Looking at the raw scrape** → `kodepos.csv`

---

## Schema

### Original (from nomor.net)

| Column | Type | Example | Notes |
|---|---|---|---|
| `no` | int | 802 | nomor.net row number |
| `kode_pos` | string | `65161` | 5-digit postal code |
| `desa` | string | `Kluwut` | desa/kelurahan name |
| `kode_wilayah` | string | `35.07.32.2001` | 13-digit Kemendagri code (PKBPP) |
| `kecamatan` | string | `Wonosari` | district name |
| `dt2` | string | `Kabupaten` | always `Kabupaten` or `Kota` |
| `kabupaten` | string | `Malang` | regency/city name |
| `provinsi` | string | `Jawa Timur` | province name |
| `source_page` | int | 4 | which pagination page (1–418) this row came from |

### Parsed (additional columns)

| Column | Type | Example | Source |
|---|---|---|---|
| `prov_code` | string | `35` | first 2 digits of `kode_wilayah` |
| `kab_code` | string | `07` | digits 4–5 |
| `kec_code` | string | `32` | digits 7–8 |
| `desa_code` | string | `2001` | digits 10–13 |
| `full_code` | string | `3507322001` | all 13 digits, no dots |
| `is_kelurahan` | int (0/1) | `0` | 1 if `desa_code` starts with `1` (urban/kelurahan), 0 if starts with `2` (rural/desa) |
| `is_desa` | int (0/1) | `1` | inverse of `is_kelurahan` |

Per dataset:
- **Kelurahan** (urban, `desa_code` starts with `1`): **8,470**
- **Desa** (rural, `desa_code` starts with `2`): **74,675**

### SQLite (DB)

```sql
-- Table: wilayah (kode_wilayah PK)
-- Indexes: kode_pos, prov_code, (prov_code, kab_code),
--          (prov_code, kab_code, kec_code), kecamatan, kabupaten,
--          provinsi, (prov_code, kabupaten)
```

---

## Quick Start

### Python (CSV)

```python
import pandas as pd

df = pd.read_csv("kodepos_parsed.csv")

# All desa in kecamatan Wonosari, Kabupaten Malang, Jawa Timur
mask = (df.provinsi == "Jawa Timur") & (df.kabupaten == "Malang") & (df.kecamatan == "Wonosari")
print(df[mask][["kode_wilayah", "kode_pos", "desa"]])

# Reverse lookup: given a kode_pos, what desa can receive mail there?
print(df[df.kode_pos == "65161"])
```

### Python (SQLite)

```python
import sqlite3
con = sqlite3.connect("kodepos.db")
# Find all kelurahan (urban) in DKI Jakarta
print(con.execute("""
  SELECT kode_wilayah, kode_pos, desa, kecamatan, kabupaten
  FROM wilayah
  WHERE prov_code = '31' AND is_kelurahan = 1
  ORDER BY kabupaten, kecamatan, desa
""").fetchall())
```

### SQL (any RDBMS)

```sql
-- Province → Kabupaten → Kecamatan → Desa hierarchy
SELECT provinsi, kabupaten, kecamatan, desa, kode_pos, kode_wilayah
FROM wilayah
WHERE prov_code = '31'                  -- DKI Jakarta
ORDER BY kabupaten, kecamatan, desa;
```

```sql
-- All kode_pos used in a given village
SELECT DISTINCT kode_pos FROM wilayah WHERE kode_wilayah = '35.07.32.2001';
```

```sql
-- Coverage per provinsi
SELECT provinsi, COUNT(*) AS n_desa,
       SUM(is_kelurahan) AS n_kelurahan,
       COUNT(*) - SUM(is_kelurahan) AS n_desa_rural,
       COUNT(DISTINCT kode_pos) AS unique_kodepos
FROM wilayah
GROUP BY provinsi
ORDER BY n_desa DESC;
```

---

## Usage: scrape again

The scraper is resumeable: it appends to `kodepos_raw.jsonl` and skips pages already in the file.

```bash
# Full re-scrape (418 pages × ~200 rows each, ~5 min on 6 threads)
python3 scrape.py --workers 6

# Range (e.g., refresh last 20 pages)
python3 scrape.py --start 399 --end 418 --workers 6

# Then rebuild outputs
python3 build_parsed.py
python3 build_sqlite.py
```

### How pagination works

`nomor.net` exposes 418 pages of 200 rows each but the visible page nav only shows the first 50. The URL pattern is:

```
https://www.nomor.net/_kodepos.php?_i=desa-kodepos&daerah=&jobs=&perhal=200&urut=&asc=000101&sby=010000&no1=9601&no2=9800&kk=50
```

Where:
- `no1` / `no2` = row range (1-indexed, inclusive)
- `kk` = page index (>= 1; not strictly sequential, off-by-one from no1/no2 but consistent)

We hit page 1 directly (`sby=010000`) and compute `no1 = (page-1)*200 + 1`, `no2 = page*200`, `kk = page+1` for pages 2+.

---

## Data Source

- **Primary**: <https://www.nomor.net/_kodepos.php?_i=desa-kodepos>
  - Self-attributed sources: Kepmendagri RI No. 100.1.1-6117 Tahun 2022, Permendagri RI No. 58 Tahun 2021, kodepos.nomor.net, masing-masing Pemprov/Pemda, SIG Kemenhub.
- **Cross-reference** (for Permendagri hierarchy): <https://www.kemendagri.go.id/>

If you find a discrepancy with the official Permendagri, please open an issue with the row's `kode_wilayah` and what the Permendagri says.

---

## Coverage Stats

| Metric | Value |
|---|---|
| Total rows | **83,145** |
| Unique `kode_wilayah` | 83,145 (100%) |
| Unique `kode_pos` | 10,636 |
| Provinsi | 38 |
| Kabupaten / Kota | 514 |
| Kecamatan / Distrik | 7,257 |
| Kelurahan (urban) | 8,470 |
| Desa (rural) | 74,675 |

Top 5 provinsi by desa count:
1. Jawa Tengah — 8,520
2. Jawa Timur — 8,458
3. Aceh (NAD) — 6,468
4. Sumatera Utara — 6,081
5. Jawa Barat — 5,934

(`nomor.net` advertises 83,763 desa/kelurahan in its page header; we scraped 83,145. The 618-row gap is because some rows on nomor.net appear in multiple navigation lists — by deduplicating on `kode_wilayah` we get the canonical count.)

---

## License

Data sourced from a public Indonesian reference site (nomor.net). Re-published here for developer convenience. Treat it as **public information**: Kemendagri codes and postal codes are facts, not copyrighted.

Source code (`scrape.py`, `build_*.py`): MIT.

---

## Maintainer

Fadil / mrayhanfadil

Issues: <https://github.com/mrayhanfadil/kodepos-id/issues>