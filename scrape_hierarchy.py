#!/usr/bin/env python3
"""
Scrape the 3 hierarchy lists from nomor.net:
  - provinsi  (38 rows, 1 page)
  - kota/kab  (514 rows, organized by provinsi, ~10 pages each)
  - kecamatan (7,277 rows, organized by provinsi, ~36 pages each)

Then diff against the existing kodepos_parsed.csv to find Papua-related updates
and anything else that changed.

Outputs:
  wilayah_provinsi.csv   (38 rows)
  wilayah_kota.csv       (514 rows)
  wilayah_kecamatan.csv  (7,277 rows)
  diff_papua.md          (markdown report of Papua-related differences)
"""
import csv
import json
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path("/home/fadil/projects/kodepos-scraper")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
BASE = "https://www.nomor.net/_kodepos.php"


def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": "https://www.nomor.net/",
    })
    retry = Retry(total=5, backoff_factor=1.5,
                  status_forcelist=(429, 500, 502, 503, 504),
                  allowed_methods=("GET",))
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    s.mount("https://", adapter)
    return s


# ---------------------------------------------------------------------------
# Table row extractor (handles both #ccffff and #ffffcc row backgrounds)
# ---------------------------------------------------------------------------

def parse_hierarchy_rows(html: str) -> list[list[str]]:
    """Parse the main data table, returning rows as lists of cell text."""
    tr_pattern = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
    td_pattern = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
    strip_tags = re.compile(r"<[^>]+>")
    rows = []
    for tr_m in tr_pattern.finditer(html):
        tr = tr_m.group(1)
        cells = []
        for td_m in td_pattern.finditer(tr):
            inner = td_m.group(1)
            text = strip_tags.sub(" ", inner)
            text = " ".join(text.split()).strip()
            cells.append(text)
        rows.append(cells)
    return rows


# ---------------------------------------------------------------------------
# Provinsi scraper (1 page)
# ---------------------------------------------------------------------------

def scrape_provinsi() -> list[dict]:
    s = make_session()
    url = f"{BASE}?_i=provinsi-kodepos&sby=010000"
    r = s.get(url, timeout=60)
    r.raise_for_status()
    if r.encoding is None or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding or "utf-8"

    rows = parse_hierarchy_rows(r.text)
    prov = []
    for cells in rows:
        # Skip "Jumlah Total" footer
        if len(cells) < 8 or not cells[0].isdigit():
            continue
        if cells[1].strip().lower().startswith("jumlah"):
            continue
        no = int(cells[0])
        # Real columns from nomor.net:
        # 0=no, 1=name, 2=digit_prefix, 3=range_str, 4=range_kodepos,
        # 5=kab_count (link), 6=kota_count, 7=kab_total (numeric, may be same as 5 for Kota-only),
        # 8=kec_count (link), 9=desa_count (with "1.552" thousand-sep), 10=pulau_count, 11=prov_code
        def to_int(s):
            if not s:
                return None
            cleaned = s.replace(".", "").replace(",", "").replace(" ", "")
            if cleaned.lstrip("-").isdigit():
                return int(cleaned)
            try:
                return int(float(cleaned))
            except Exception:
                return None

        prov.append({
            "no": no,
            "nama_provinsi": cells[1],
            "digit_prefix": cells[2],
            "kodepos_range_str": cells[3],
            "kodepos_range": cells[4],
            "kab_count_link": cells[5],
            "kota_count": to_int(cells[6]),
            "kab_total": to_int(cells[7]),
            "kec_count": to_int(cells[8]),
            "desa_count": to_int(cells[9]),
            "pulau_count": cells[10] if len(cells) >= 11 else "",
            "prov_code": cells[11] if len(cells) >= 12 else "",
        })
    return prov


# ---------------------------------------------------------------------------
# Kota/Kabupaten scraper (multi-page, per-provinsi filter)
# ---------------------------------------------------------------------------

def fetch_kota_page(session: requests.Session, jobs: str, page_no: int) -> list[dict]:
    """Fetch all kota/kab for a provinsi in one shot. nomor.net returns data
    only when no1=2 (not no1=1); perhal can be up to 1000 which fits any prov
    (max 33 rows)."""
    perhal = 1000
    params = {
        "_i": "kota-kodepos",
        "daerah": "Provinsi",
        "jobs": jobs,
        "perhal": str(perhal),
        "urut": "",
        "asc": "000011111",
        "sby": "010000",
        "no1": "2",
        "no2": str(perhal),
        "kk": "2",
    }
    url = f"{BASE}?{urllib.parse.urlencode(params)}"
    r = session.get(url, timeout=60)
    r.raise_for_status()
    if r.encoding is None or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding or "utf-8"

    rows = parse_hierarchy_rows(r.text)
    out = []
    for cells in rows:
        if len(cells) < 8 or not cells[0].isdigit():
            continue
        if cells[1].strip().lower().startswith("jumlah"):
            continue
        # Real columns from nomor.net:
        # 0=no, 1=DT2 (Kota/Kab.), 2=nama_kota_kab, 3=kodepos_range_str,
        # 4=kodepos_range, 5=n_kota, 6=n_kab, 7=n_pulau, 8=kode_wilayah_kab,
        # 9=provinsi
        try:
            out.append({
                "no": int(cells[0]),
                "dt2": cells[1],
                "nama_kota_kab": cells[2],
                "kodepos_range_str": cells[3],
                "kodepos_range": cells[4],
                "n_kota": int(cells[5]) if cells[5].isdigit() else cells[5],
                "n_kab": int(cells[6]) if cells[6].isdigit() else cells[6],
                "n_pulau": int(cells[7]) if cells[7].isdigit() else cells[7],
                "kode_wilayah_kab": cells[8],
                "provinsi_filter": cells[9] if len(cells) > 9 else jobs,
                "source_page": page_no,
            })
        except Exception as e:
            print(f"[kota:{jobs}] skip row {cells[0]}: {e}", file=sys.stderr)
    return out


def fetch_kota_total_pages(session: requests.Session, jobs: str) -> int:
    """Each prov's kota list fits on 1 page (perhal=200, max ~33 kota).
    Return 1 always unless pagination links are present."""
    url = f"{BASE}?_i=kota-kodepos&daerah=Provinsi&jobs={urllib.parse.quote(jobs)}&sby=010000"
    r = session.get(url, timeout=60)
    r.raise_for_status()
    if r.encoding is None or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding or "utf-8"
    # Find pagination kk= values from links (excludes kk=2 in URL itself)
    # Real pagination links appear inside <center> Halaman ke block
    m = re.search(r"Halaman ke.*?</table>", r.text, re.S)
    if m:
        block = m.group(0)
        kks = [int(x) for x in re.findall(r"kk=(\d+)", block)]
        if kks:
            # kk=2 is the "next page" link; max real page is kk-1
            return max(kks) - 1 if max(kks) > 1 else 1
    return 1


def scrape_kota(prov_list: list[dict]) -> list[dict]:
    """For each provinsi, scrape its kota/kab pages."""
    all_rows = []
    s = make_session()

    def per_prov(prov: dict) -> list[dict]:
        jobs = prov["nama_provinsi"]
        try:
            n_pages = fetch_kota_total_pages(s, jobs)
        except Exception as e:
            print(f"[kota:{jobs}] total_pages failed: {e}", file=sys.stderr)
            return []
        local = []
        for p in range(1, n_pages + 1):
            try:
                rows = fetch_kota_page(s, jobs, p)
                local.extend(rows)
                time.sleep(0.4)
            except Exception as e:
                print(f"[kota:{jobs}] page {p} failed: {e}", file=sys.stderr)
        return local

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(per_prov, p): p for p in prov_list}
        for fut in as_completed(futures):
            p = futures[fut]
            try:
                rows = fut.result()
                print(f"[kota] {p['nama_provinsi']}: +{len(rows)} (running total {len(all_rows)})")
                all_rows.extend(rows)
            except Exception as e:
                print(f"[kota] {p['nama_provinsi']} FAILED: {e}")

    # Dedupe on (no, provinsi_filter, nama_kota_kab)
    seen = set()
    dedup = []
    for r in all_rows:
        key = (r["no"], r["provinsi_filter"], r["nama_kota_kab"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)
    return dedup


# ---------------------------------------------------------------------------
# Kecamatan scraper (similar to kota)
# ---------------------------------------------------------------------------

def fetch_kecamatan_page(session: requests.Session, jobs: str, page_no: int) -> list[dict]:
    """Fetch kecamatan list for one provinsi. The kecamatan page returns data
    only when no1=2 (matching the kota page convention). perhal=1000 fits any
    province (max prov has 666 kecamatan, well under 1000)."""
    perhal = 1000
    params = {
        "_i": "kecamatan-kodepos",
        "daerah": "Provinsi",
        "jobs": jobs,
        "perhal": str(perhal),
        "urut": "",
        "asc": "001000",
        "sby": "010000",
        "no1": "2",
        "no2": str(perhal),
        "kk": "2",
    }
    url = f"{BASE}?{urllib.parse.urlencode(params)}"
    r = session.get(url, timeout=60)
    r.raise_for_status()
    if r.encoding is None or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding or "utf-8"

    rows = parse_hierarchy_rows(r.text)
    out = []
    for cells in rows:
        if len(cells) < 7 or not cells[0].isdigit():
            continue
        if cells[1].strip().lower().startswith("jumlah"):
            continue
        # Real columns from nomor.net for kecamatan list:
        # 0=no, 1=nama_kecamatan, 2=kodepos_range_str,
        # 3=n_desa (or '-' for special), 4=?, 5=kab_kota,
        # 6=provinsi_filter
        # Actually let me sample first: from earlier output row 'Pulau Banyak,24791,3,-,11.10.01,Kab.,Aceh Singkil,Aceh (NAD),1'
        # That's 9 cells after CSV write, but in raw HTML structure let's see actual order.
        # From real fetch: row 204 = Pulo Aceh,23391,17,-,11.06.13,Kab.,Aceh Besar,Aceh (NAD),1
        # So: 0=no, 1=name, 2=pos_max, 3=count?, 4='-', 5=kode_wilayah_kec, 6='Kab.', 7=kab_kota, 8=prov
        try:
            out.append({
                "no": int(cells[0]),
                "nama_kecamatan": cells[1],
                "kodepos_max": cells[2] if len(cells) > 2 else "",
                "desa_count_raw": cells[3] if len(cells) > 3 else "",
                "sep": cells[4] if len(cells) > 4 else "",
                "kode_wilayah_kec": cells[5] if len(cells) > 5 else "",
                "dt2": cells[6] if len(cells) > 6 else "",
                "kab_kota": cells[7] if len(cells) > 7 else "",
                "provinsi_filter": cells[8] if len(cells) > 8 else jobs,
                "source_page": page_no,
            })
        except Exception as e:
            print(f"[kec:{jobs}] skip row {cells[0]}: {e}", file=sys.stderr)
    return out


def fetch_kecamatan_total_pages(session: requests.Session, jobs: str) -> int:
    url = f"{BASE}?_i=kecamatan-kodepos&daerah=Provinsi&jobs={urllib.parse.quote(jobs)}&sby=010000"
    r = session.get(url, timeout=60)
    r.raise_for_status()
    if r.encoding is None or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding or "utf-8"
    m = re.search(r"Halaman ke.*?</table>", r.text, re.S)
    if m:
        block = m.group(0)
        kks = [int(x) for x in re.findall(r"kk=(\d+)", block)]
        if kks:
            return max(kks) - 1 if max(kks) > 1 else 1
    return 1


def scrape_kecamatan(prov_list: list[dict]) -> list[dict]:
    all_rows = []
    s = make_session()

    def per_prov(prov: dict) -> list[dict]:
        jobs = prov["nama_provinsi"]
        try:
            n_pages = fetch_kecamatan_total_pages(s, jobs)
        except Exception as e:
            print(f"[kec:{jobs}] total_pages failed: {e}", file=sys.stderr)
            return []
        local = []
        for p in range(1, n_pages + 1):
            try:
                rows = fetch_kecamatan_page(s, jobs, p)
                local.extend(rows)
                time.sleep(0.4)
            except Exception as e:
                print(f"[kec:{jobs}] page {p} failed: {e}", file=sys.stderr)
        return local

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(per_prov, p): p for p in prov_list}
        for fut in as_completed(futures):
            p = futures[fut]
            try:
                rows = fut.result()
                print(f"[kec] {p['nama_provinsi']}: +{len(rows)} (running total {len(all_rows)})")
                all_rows.extend(rows)
            except Exception as e:
                print(f"[kec] {p['nama_provinsi']} FAILED: {e}")

    seen = set()
    dedup = []
    for r in all_rows:
        key = (r["no"], r["provinsi_filter"], r["nama_kecamatan"], r["kode_wilayah_kec"])
        if key in seen:
            continue
        seen.add(key)
        dedup.append(r)
    return dedup


# ---------------------------------------------------------------------------
# CSV writers
# ---------------------------------------------------------------------------

def write_csv(path: Path, rows: list[dict], fieldnames: list[str]):
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main():
    print("=== 1. Scrape provinsi ===")
    prov = scrape_provinsi()
    print(f"Got {len(prov)} provinsi")
    if prov:
        for p in prov[:3]:
            print(f"  {p['no']:>2}. {p['nama_provinsi']:35s} kab={p['kab_total']}, "
                  f"kec={p['kec_count']}, desa={p['desa_count']}")
    write_csv(ROOT / "wilayah_provinsi.csv", prov,
              fieldnames=["no", "nama_provinsi", "digit_prefix", "kodepos_range_str",
                          "kodepos_range", "kab_count_link", "kota_count", "kab_total",
                          "kec_count", "desa_count", "pulau_count", "prov_code"])
    print(f"Wrote wilayah_provinsi.csv ({len(prov)} rows)")

    print("\n=== 2. Scrape kota/kab per provinsi ===")
    kota = scrape_kota(prov)
    print(f"Got {len(kota)} kota/kab")
    write_csv(ROOT / "wilayah_kota.csv", kota,
              fieldnames=["no", "dt2", "nama_kota_kab", "kodepos_range_str",
                          "kodepos_range", "n_kota", "n_kab", "n_pulau",
                          "kode_wilayah_kab", "provinsi_filter", "source_page"])
    print(f"Wrote wilayah_kota.csv ({len(kota)} rows)")

    print("\n=== 3. Scrape kecamatan per provinsi ===")
    kec = scrape_kecamatan(prov)
    print(f"Got {len(kec)} kecamatan")
    write_csv(ROOT / "wilayah_kecamatan.csv", kec,
              fieldnames=["no", "nama_kecamatan", "kodepos_max", "desa_count_raw",
                          "sep", "kode_wilayah_kec", "dt2", "kab_kota",
                          "provinsi_filter", "source_page"])
    print(f"Wrote wilayah_kecamatan.csv ({len(kec)} rows)")


if __name__ == "__main__":
    main()