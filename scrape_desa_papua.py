#!/usr/bin/env python3
"""
Scrape desa/kelurahan rows filtered by provinsi to extract the missing
desa records identified in the hierarchy diff (especially Papua regions).

For each provinsi, fetch all pages of the desa-kodepos page filtered by
daerah=Provinsi&jobs=<prov>. Combine results into a single JSONL.
"""
import json
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

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


def fetch_desa_page(session: requests.Session, jobs: str, page_no: int) -> tuple[int, list[dict]]:
    """Fetch one page of desa list filtered by provinsi. Returns (page_no, rows)."""
    perhal = 200
    no1 = (page_no - 1) * perhal + 2
    no2 = page_no * perhal + 1
    kk = page_no + 1
    params = {
        "_i": "desa-kodepos",
        "daerah": "Provinsi",
        "jobs": jobs,
        "perhal": str(perhal),
        "urut": "",
        "asc": "000101",
        "sby": "010000",
        "no1": str(no1),
        "no2": str(no2),
        "kk": str(kk),
    }
    url = f"{BASE}?{urllib.parse.urlencode(params)}"
    r = session.get(url, timeout=60)
    r.raise_for_status()
    if r.encoding is None or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding or "utf-8"

    rows = _parse(r.text, jobs, page_no)
    return (page_no, rows)


def _parse(html: str, jobs: str, page_no: int) -> list[dict]:
    """Parse desa rows. Same format as scrape.py parse_rows_with_prov."""
    import re
    start_marker = 'class="ktu" title='
    end_marker = "Halaman ke"
    s = html.find(start_marker)
    if s == -1:
        s = html.find("Daftar Desa & Kelurahan")
    e = html.find(end_marker, s if s != -1 else 0)
    if e == -1:
        e = len(html)
    if s == -1:
        return []
    slice_html = html[s:e]

    tr_pattern = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
    td_pattern = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
    strip_tags = re.compile(r"<[^>]+>")

    rows = []
    for tr_match in tr_pattern.finditer(slice_html):
        tr = tr_match.group(1)
        cells = []
        for td_match in td_pattern.finditer(tr):
            inner = td_match.group(1)
            text = strip_tags.sub(" ", inner)
            text = " ".join(text.split()).strip()
            cells.append(text)
        if len(cells) >= 8:
            cells = cells[:8]
        elif len(cells) == 7:
            cells.append("")
        else:
            continue
        if not cells[0].isdigit():
            continue
        no, kode_pos, desa, kode_wilayah, kecamatan, dt2, kabupaten, provinsi = cells
        rows.append({
            "no": int(no),
            "kode_pos": kode_pos,
            "desa": desa,
            "kode_wilayah": kode_wilayah,
            "kecamatan": kecamatan,
            "dt2": dt2,
            "kabupaten": kabupaten,
            "provinsi": provinsi,
            "source_page_filter": jobs,
            "source_page": page_no,
        })
    return rows


def fetch_total_pages(session: requests.Session, jobs: str) -> int:
    """Probe last page from pagination links."""
    import re
    url = f"{BASE}?_i=desa-kodepos&daerah=Provinsi&jobs={urllib.parse.quote(jobs)}&sby=010000"
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


def scrape_prov(session: requests.Session, jobs: str) -> list[dict]:
    n_pages = fetch_total_pages(session, jobs)
    out = []
    for p in range(1, n_pages + 1):
        try:
            _, rows = fetch_desa_page(session, jobs, p)
            out.extend(rows)
            time.sleep(0.4)
        except Exception as e:
            print(f"[{jobs}] page {p} failed: {e}", file=sys.stderr)
    return out


def main():
    # Target: provinces with largest gaps (Papua Pegunungan +69, Tengah +54, etc.)
    # plus all Papua provinces for completeness
    targets = [
        "Papua Pegunungan",   # +69 desa, +9 kec
        "Papua Tengah",       # +54 desa, +5 kec
        "Papua",              # +29 desa
        "Papua Selatan",      # +18 desa
        "Papua Barat",        # +11 desa
        "Papua Barat Daya",   # +10 desa
        # Plus other non-Papua regions with sizable gaps
        "Jawa Tengah",        # +43 desa
        "Sumatera Barat",     # +33 desa
        "Sumatera Utara",     # +29 desa
        "Aceh (NAD)",         # +32 desa
        "Jawa Timur",          # +36 desa
        "Riau",               # +25 desa
        "Nusa Tenggara Timur (NTT)",  # +20 desa
        "Bengkulu",           # +19 desa
        "Kalimantan Selatan", # +14 desa
        "Sumatera Selatan",   # +14 desa
        "Sulawesi Tenggara",  # +13 desa
        "Sulawesi Selatan",   # +11 desa
        "Kalimantan Barat",   # +11 desa
        "Jambi",              # +10 desa
        "Kalimantan Timur",   # +9 desa
        "Lampung",            # +8 desa
        "Maluku Utara",       # +8 desa
        "Jawa Barat",         # +23 desa
        "Maluku",             # +7 desa
        "Kalimantan Tengah",  # +7 desa
        "Gorontalo",          # +5 desa
        "Nusa Tenggara Barat (NTB)",  # +5 desa
        "Bali",               # +5 desa
        "DI Yogyakarta",      # +7 desa
        "Banten",             # +7 desa
        "Kalimantan Utara",   # +3 desa
        "Kepulauan Bangka Belitung",  # +4 desa
        "Kepulauan Riau",     # +2 desa
        "DKI Jakarta",        # +1 desa
        "Sulawesi Barat",      # +2 desa
        "Sulawesi Utara",      # +7 desa
        "Sulawesi Tengah",     # +7 desa
    ]

    out_path = ROOT / "wilayah_desa_papua.jsonl"
    fw = out_path.open("w", encoding="utf-8")
    total = 0

    def worker(prov: str):
        s = make_session()
        return prov, scrape_prov(s, prov)

    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(worker, p): p for p in targets}
        for fut in as_completed(futures):
            prov = futures[fut]
            try:
                _, rows = fut.result()
                for r in rows:
                    fw.write(json.dumps(r, ensure_ascii=False) + "\n")
                fw.flush()
                total += len(rows)
                print(f"[{prov:35s}] +{len(rows)} rows (running total {total})")
            except Exception as e:
                print(f"[{prov}] FAILED: {e}")

    fw.close()
    print(f"\nTotal scraped: {total}")
    print(f"Output: {out_path} ({out_path.stat().st_size/1024/1024:.2f} MB)")


if __name__ == "__main__":
    main()