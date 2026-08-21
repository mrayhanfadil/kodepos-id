#!/usr/bin/env python3
"""
Scrape kodepos data from https://www.nomor.net/_kodepos.php?_i=desa-kodepos

Output fields per row:
  - no            : row number on nomor.net
  - kode_pos      : 5-digit postal code
  - desa          : village/kelurahan name
  - kode_wilayah  : 13-digit Kemendagri code (e.g. 95.04.32.2006)
  - kecamatan     : district name
  - dt2           : Kota/Kabupaten type
  - kabupaten     : regency/city name
  - provinsi      : province name
  - source_page   : which pagination page this came from (1-50)
"""
import json
import re
import sys
import time
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from html.parser import HTMLParser

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
       "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")
BASE = "https://www.nomor.net/_kodepos.php"
OUT_DIR = Path("/home/fadil/projects/kodepos-scraper")


# ---------------------------------------------------------------------------
# Table row extractor
# ---------------------------------------------------------------------------

class RowExtractor(HTMLParser):
    """Parse <tr> rows out of the main data table, capturing each <td>.

    We don't bother fully reconstructing the DOM — we just track the depth so
    we know when we're inside the data table, then collect cell text + a few
    link attributes in row order. Cell texts are extracted as plain strings
    (whitespace collapsed, links' hrefs ignored — we read the displayed text).
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.in_table = False
        self._depth_in_table = 0
        self.current_row: list[str] | None = None
        self.current_cell: list[str] | None = None
        self._cell_has_anchor = False
        self._rows: list[list[str]] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            self._depth_in_table += 1
            self.in_table = True
        elif self.in_table and tag == "tr":
            self.current_row = []
        elif self.in_table and self.current_row is not None and tag == "td":
            self.current_cell = []
            self._cell_has_anchor = False
        elif self.in_table and self.current_cell is not None and tag == "a":
            # We'll let handle_data capture anchor text; we don't need href here
            self._cell_has_anchor = True

    def handle_endtag(self, tag):
        if tag == "table":
            self._depth_in_table -= 1
            if self._depth_in_table <= 0:
                self.in_table = False
                self._depth_in_table = 0
        elif self.in_table and tag == "tr":
            if self.current_row is not None:
                # Skip header rows (rows that have a <th> would not hit this path
                # since we never opened a cell). Just accept rows with cells.
                if self.current_row:
                    self._rows.append(self.current_row)
            self.current_row = None
        elif self.in_table and tag == "td":
            if self.current_cell is not None and self.current_row is not None:
                txt = " ".join("".join(self.current_cell).split()).strip()
                self.current_row.append(txt)
            self.current_cell = None

    def handle_data(self, data):
        if self.current_cell is not None:
            self.current_cell.append(data)

    def handle_entityref(self, name):
        if self.current_cell is not None:
            from html import unescape
            self.current_cell.append(unescape(f"&{name};"))

    def handle_charref(self, name):
        if self.current_cell is not None:
            from html import unescape
            self.current_cell.append(unescape(f"&#{name};"))

    @property
    def rows(self) -> list[list[str]]:
        return self._rows


# ---------------------------------------------------------------------------
# HTTP session with retry
# ---------------------------------------------------------------------------

def make_session() -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent": UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Referer": "https://www.nomor.net/",
    })
    retry = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=10, pool_maxsize=10)
    s.mount("https://", adapter)
    s.mount("http://", adapter)
    return s


# ---------------------------------------------------------------------------
# Main scrape loop
# ---------------------------------------------------------------------------

def fetch_page(session: requests.Session, page_no: int) -> str:
    """page_no is 1-based; page 1 uses a different URL than pages 2+."""
    if page_no == 1:
        url = f"{BASE}?_i=desa-kodepos&sby=010000"
    else:
        no1 = (page_no - 1) * 200 + 1
        no2 = page_no * 200
        kk = page_no + 1
        params = {
            "_i": "desa-kodepos",
            "daerah": "",
            "jobs": "",
            "perhal": "200",
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
    # Server sends windows-1252 / latin1 occasionally — let BS auto-detect via meta
    if r.encoding is None or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding or "utf-8"
    return r.text


def parse_rows(html: str, source_page: int) -> list[dict]:
    # The data table is the LAST <table width="98%"> or similar before the
    # pagination. We can identify it by looking for cells whose pattern matches
    # (digits, anchor text with kode_pos, kode_wilayah anchor, etc).
    # Use RowExtractor on the slice that starts at the first <tr> with bgcolor
    # containing "#ccffff" (the data rows use that colour).
    parser = RowExtractor()
    parser.feed(html)
    rows = []
    # The parser captures every <tr> in document order. We need the second-pass
    # data table specifically. heuristically: pick rows whose first cell is a
    # plain integer (the No column) and which have exactly 7 cells (header has
    # different structure).
    for cells in parser.rows:
        if len(cells) != 7:
            continue
        if not cells[0].isdigit():
            continue
        no, kode_pos, desa, kode_wilayah, kecamatan, dt2, kabupaten = cells
        # The province is encoded inside the same row only as the 8th cell in
        # the actual table (we may have collapsed). Re-check by re-parsing with
        # 8-cell rows fallback below.
        if len(cells) == 8:
            provinsi = cells[7]
        else:
            # try to recover province from HTML by regexing the row around this row's anchor
            provinsi = ""
        rows.append({
            "no": int(no),
            "kode_pos": kode_pos,
            "desa": desa,
            "kode_wilayah": kode_wilayah,
            "kecamatan": kecamatan,
            "dt2": dt2,
            "kabupaten": kabupaten,
            "provinsi": provinsi,
            "source_page": source_page,
        })
    return rows


def parse_rows_with_prov(html: str, source_page: int) -> list[dict]:
    """More robust: re-extract the data table region with explicit province.

    Strategy: cut the HTML at the start of the data table (first <tr> after
    '<center>Daftar Desa & Kelurahan') and end at the pagination block
    ('Halaman ke'). Within that slice, parse every <td>. Each row has 8 cells:
    No, Kode POS, Desa, Kode Wilayah, Kecamatan, DT2, Kab/Kota, Provinsi.
    """
    start_marker = 'class="ktu" title='
    end_marker = "Halaman ke"
    s = html.find(start_marker)
    if s == -1:
        # fall back to known data section header
        s = html.find("Daftar Desa & Kelurahan di Indonesia")
    e = html.find(end_marker, s if s != -1 else 0)
    if e == -1:
        e = len(html)
    if s == -1:
        return []
    slice_html = html[s:e]

    # We need to capture each <tr>...</tr> as a unit. Use a regex since the
    # table rows are well-behaved and consistent (one-row-per-<tr>).
    tr_pattern = re.compile(r"<tr[^>]*>(.*?)</tr>", re.S | re.I)
    td_pattern = re.compile(r"<td[^>]*>(.*?)</td>", re.S | re.I)
    # Cell content: strip tags + collapse whitespace
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
            # sometimes provinsi is missing; append empty
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
            "source_page": source_page,
        })
    return rows


def scrape_all(start: int = 1, end: int = 418, workers: int = 4, progress_path: Path | None = None):
    """Concurrent scrape with thread-local sessions and JSONL append-as-we-go."""
    progress_path = progress_path or (OUT_DIR / "kodepos_raw.jsonl")
    progress_path.parent.mkdir(parents=True, exist_ok=True)

    # Resume: load already-done pages from the JSONL log
    done_pages: set[int] = set()
    seen_keys: set[str] = set()
    all_rows: list[dict] = []
    if progress_path.exists():
        with progress_path.open() as f:
            for line in f:
                try:
                    rec = json.loads(line)
                    done_pages.add(rec["source_page"])
                    if rec.get("kode_wilayah"):
                        seen_keys.add(rec["kode_wilayah"])
                    all_rows.append(rec)
                except Exception:
                    continue
        print(f"[resume] loaded {len(all_rows)} rows from {len(done_pages)} pages")

    pending = [p for p in range(start, end + 1) if p not in done_pages]
    if not pending:
        print("[resume] nothing to do")
        return all_rows
    print(f"[start] {len(pending)} pages remaining, workers={workers}")

    fw_lock_path = [progress_path.open("a", encoding="utf-8")]
    from threading import Lock
    write_lock = Lock()

    def worker(page: int) -> tuple[int, list[dict] | None, str | None]:
        s = make_session()
        try:
            html = fetch_page(s, page)
            rows = parse_rows_with_prov(html, page)
            return (page, rows, None)
        except Exception as exc:
            return (page, None, str(exc))

    pages_done = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(worker, p): p for p in pending}
        for fut in as_completed(futures):
            page, rows, err = fut.result()
            pages_done += 1
            if err or not rows:
                print(f"[page {page:>3}/{end}] ERROR: {err or '0 rows'}")
                continue
            new_rows = 0
            for r in rows:
                key = r["kode_wilayah"] or (r["kode_pos"], r["desa"], r["kecamatan"])
                if key in seen_keys:
                    continue
                seen_keys.add(key)
                all_rows.append(r)
                with write_lock:
                    fw_lock_path[0].write(json.dumps(r, ensure_ascii=False) + "\n")
                new_rows += 1
            with write_lock:
                fw_lock_path[0].flush()
            print(f"[page {page:>3}/{end}] +{new_rows} rows (total unique={len(all_rows)}) [{pages_done}/{len(pending)} done]")

    fw_lock_path[0].close()
    return all_rows


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", type=int, default=1)
    ap.add_argument("--end", type=int, default=418)
    ap.add_argument("--workers", type=int, default=4)
    args = ap.parse_args()

    rows = scrape_all(args.start, args.end, args.workers)

    # write final JSON + CSV
    json_path = OUT_DIR / "kodepos.json"
    csv_path = OUT_DIR / "kodepos.csv"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    import csv
    with csv_path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["no", "kode_pos", "desa", "kode_wilayah",
                    "kecamatan", "dt2", "kabupaten", "provinsi",
                    "source_page"])
        for r in rows:
            w.writerow([r["no"], r["kode_pos"], r["desa"], r["kode_wilayah"],
                        r["kecamatan"], r["dt2"], r["kabupaten"], r["provinsi"],
                        r["source_page"]])

    # Summary
    provinces = {r["provinsi"] for r in rows if r["provinsi"]}
    kab_count = len({(r["kabupaten"], r["provinsi"]) for r in rows if r["kabupaten"]})
    kec_count = len({(r["kecamatan"], r["kabupaten"]) for r in rows if r["kecamatan"]})
    kode_wilayah_unique = len({r["kode_wilayah"] for r in rows if r["kode_wilayah"]})
    kode_pos_unique = len({r["kode_pos"] for r in rows if r["kode_pos"]})

    print(f"\nTotal rows scraped (unique): {len(rows)}")
    print(f"  provinces: {len(provinces)}")
    print(f"  kabupaten/kota: {kab_count}")
    print(f"  kecamatan: {kec_count}")
    print(f"  unique kode_wilayah: {kode_wilayah_unique}")
    print(f"  unique kode_pos: {kode_pos_unique}")
    print(f"JSON: {json_path}  ({json_path.stat().st_size/1024/1024:.2f} MB)")
    print(f"CSV:  {csv_path}   ({csv_path.stat().st_size/1024/1024:.2f} MB)")


if __name__ == "__main__":
    main()