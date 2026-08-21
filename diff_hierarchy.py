#!/usr/bin/env python3
"""
Diff the new hierarchy scrape (provinsi, kota, kecamatan) vs the existing
kodepos_parsed.csv to find updates, especially for the new Papua region splits.

Outputs: diff_hierarchy.md
"""
import csv
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path("/home/fadil/projects/kodepos-scraper")


def load_kodepos():
    rows = list(csv.DictReader(open(ROOT / "kodepos_parsed.csv")))
    return rows


def load_provinsi():
    return list(csv.DictReader(open(ROOT / "wilayah_provinsi.csv")))


def load_kota():
    return list(csv.DictReader(open(ROOT / "wilayah_kota.csv")))


def load_kecamatan():
    return list(csv.DictReader(open(ROOT / "wilayah_kecamatan.csv")))


def _as_int(x):
    if x is None or x == "":
        return 0
    if isinstance(x, int):
        return x
    s = str(x).replace(".", "").replace(",", "").replace(" ", "")
    try:
        return int(s)
    except Exception:
        return 0


def diff_provinsi(mine_rows, prov_rows):
    """Build {(prov_name): row} maps. Compare prov_code + desa_count per prov."""
    # Group desa count per province from the master
    mine_prov = defaultdict(lambda: {"desa_count": 0, "kab_set": set(),
                                      "kec_set": set(), "kode_pos_set": set()})
    for r in mine_rows:
        p = r["provinsi"]
        mine_prov[p]["desa_count"] += 1
        mine_prov[p]["kab_set"].add(r["kabupaten"])
        mine_prov[p]["kec_set"].add(r["kecamatan"])
        mine_prov[p]["kode_pos_set"].add(r["kode_pos"])

    # Build {(prov_name): scrape_row}
    scrape_prov = {r["nama_provinsi"]: r for r in prov_rows}

    diffs = []
    all_names = set(mine_prov.keys()) | set(scrape_prov.keys())
    for name in sorted(all_names):
        m = mine_prov.get(name, {})
        s = scrape_prov.get(name, {})
        scrape_desa = _as_int(s.get("desa_count"))
        scrape_kab_total = _as_int(s.get("kab_total"))
        scrape_kec = _as_int(s.get("kec_count"))
        diffs.append({
            "provinsi": name,
            "mine_desa": m.get("desa_count", 0),
            "scrape_desa": scrape_desa,
            "diff_desa": scrape_desa - m.get("desa_count", 0),
            "mine_kab": len(m.get("kab_set", set())),
            "scrape_kab": scrape_kab_total,
            "mine_kec": len(m.get("kec_set", set())),
            "scrape_kec": scrape_kec,
            "scrape_prov_code": s.get("prov_code", ""),
        })
    return diffs


def diff_kota(mine_rows, kota_rows):
    """Check if the kota/kab set matches per-province."""
    mine_kab = defaultdict(set)
    for r in mine_rows:
        mine_kab[r["provinsi"]].add(r["kabupaten"])
    scrape_kab = defaultdict(set)
    scrape_kab_detail = defaultdict(dict)
    for r in kota_rows:
        prov = r["provinsi_filter"]
        scrape_kab[prov].add(r["nama_kota_kab"])
        scrape_kab_detail[prov][r["nama_kota_kab"]] = r["kode_wilayah_kab"]

    diffs = []
    for prov in sorted(set(mine_kab.keys()) | set(scrape_kab.keys())):
        mine_set = mine_kab.get(prov, set())
        scrape_set = scrape_kab.get(prov, set())
        only_mine = mine_set - scrape_set
        only_scrape = scrape_set - mine_set
        if only_mine or only_scrape or len(mine_set) != len(scrape_set):
            diffs.append({
                "provinsi": prov,
                "mine_count": len(mine_set),
                "scrape_count": len(scrape_set),
                "only_mine": sorted(only_mine),
                "only_scrape": sorted(only_scrape),
                "scrape_prov_codes": scrape_kab_detail[prov],
            })
    return diffs


def diff_kecamatan(mine_rows, kec_rows):
    """Compare kecamatan sets per (provinsi, kabupaten)."""
    mine_kec = defaultdict(set)
    mine_kec_detail = defaultdict(dict)
    for r in mine_rows:
        key = (r["provinsi"], r["kabupaten"])
        mine_kec[key].add(r["kecamatan"])
        mine_kec_detail[key][r["kecamatan"]] = r["kec_code"]

    scrape_kec = defaultdict(set)
    scrape_kec_detail = defaultdict(dict)
    for r in kec_rows:
        key = (r["provinsi_filter"], r["kab_kota"])
        scrape_kec[key].add(r["nama_kecamatan"])
        scrape_kec_detail[key][r["nama_kecamatan"]] = r["kode_wilayah_kec"]

    diffs = []
    all_keys = set(mine_kec.keys()) | set(scrape_kec.keys())
    for key in sorted(all_keys):
        prov, kab = key
        mine_set = mine_kec.get(key, set())
        scrape_set = scrape_kec.get(key, set())
        only_mine = mine_set - scrape_set
        only_scrape = scrape_set - mine_set
        # Focus on Papua regions
        if "Papua" in prov or "Papua" in kab or only_mine or only_scrape:
            diffs.append({
                "provinsi": prov,
                "kabupaten": kab,
                "mine_count": len(mine_set),
                "scrape_count": len(scrape_set),
                "only_mine": sorted(only_mine),
                "only_scrape": sorted(only_scrape),
            })
    return diffs


def main():
    print("Loading master kodepos_parsed.csv...")
    mine = load_kodepos()
    print(f"  {len(mine)} desa rows")

    print("Loading hierarchy scrapes...")
    prov = load_provinsi()
    kota = load_kota()
    kec = load_kecamatan()
    print(f"  {len(prov)} provinsi, {len(kota)} kota, {len(kec)} kecamatan")

    print("\n=== Diff provinsi ===")
    prov_diffs = diff_provinsi(mine, prov)
    print(f"  {len(prov_diffs)} provinsi compared")

    print("\n=== Diff kota ===")
    kota_diffs = diff_kota(mine, kota)
    print(f"  {len(kota_diffs)} provinsi with kota differences")

    print("\n=== Diff kecamatan (Papua + any others) ===")
    kec_diffs = diff_kecamatan(mine, kec)
    print(f"  {len(kec_diffs)} kabupaten with kecamatan differences")

    # Build markdown report
    md = []
    md.append("# Diff: kodepos-id vs nomor.net hierarchy (kota/kab/prov)")
    md.append("")
    md.append("Generated: 2026-08-21 WIB")
    md.append("")
    md.append("Source: https://www.nomor.net/_kodepos.php?_i=provinsi-kodepos (and kota, kecamatan)")
    md.append("")
    md.append(f"Master: kodepos_parsed.csv ({len(mine)} desa)")
    md.append(f"New scrape: wilayah_provinsi.csv ({len(prov)}), "
              f"wilayah_kota.csv ({len(kota)}), wilayah_kecamatan.csv ({len(kec)})")
    md.append("")

    md.append("## Provinsi comparison")
    md.append("")
    md.append("| Provinsi | mine.desa | scrape.desa | Δ desa | mine.kab | scrape.kab | mine.kec | scrape.kec | prov_code |")
    md.append("|---|---|---|---|---|---|---|---|---|")
    for d in prov_diffs:
        flag = " 🔴" if d["diff_desa"] != 0 else ""
        md.append(f"| {d['provinsi']} | {d['mine_desa']} | {d['scrape_desa']} | "
                  f"{d['diff_desa']:+d}{flag} | {d['mine_kab']} | {d['scrape_kab']} | "
                  f"{d['mine_kec']} | {d['scrape_kec']} | `{d['scrape_prov_code']}` |")
    md.append("")

    md.append("## Kota/Kab differences")
    md.append("")
    if not kota_diffs:
        md.append("_No kota/kab differences between master and scrape._")
    else:
        md.append("| Provinsi | mine.count | scrape.count | Only in mine | Only in scrape |")
        md.append("|---|---|---|---|---|")
        for d in kota_diffs:
            only_mine = ", ".join(f"`{x}`" for x in d["only_mine"][:10])
            only_scrape = ", ".join(f"`{x}`" for x in d["only_scrape"][:10])
            md.append(f"| {d['provinsi']} | {d['mine_count']} | {d['scrape_count']} | "
                      f"{only_mine or '—'} | {only_scrape or '—'} |")
    md.append("")

    md.append("## Kecamatan differences (Papua-focused)")
    md.append("")
    if not kec_diffs:
        md.append("_No kecamatan differences found._")
    else:
        md.append("| Provinsi | Kabupaten | mine.count | scrape.count | Only in mine | Only in scrape |")
        md.append("|---|---|---|---|---|---|")
        for d in kec_diffs:
            only_mine = ", ".join(f"`{x}`" for x in d["only_mine"][:8])
            only_scrape = ", ".join(f"`{x}`" for x in d["only_scrape"][:8])
            md.append(f"| {d['provinsi']} | {d['kabupaten']} | {d['mine_count']} | "
                      f"{d['scrape_count']} | {only_mine or '—'} | {only_scrape or '—'} |")
    md.append("")

    # Summary verdict
    md.append("## Verdict")
    md.append("")
    papua_provs = [p for p in prov if "Papua" in p["nama_provinsi"]]
    md.append("## Papua region coverage")
    md.append("")
    for p in papua_provs:
        md.append(f"- **{p['nama_provinsi']}**: prov_code=`{p['prov_code']}`, "
                  f"kab={p['kab_total']}, kec={p['kec_count']}, desa={p['desa_count']}")
    md.append("")
    md.append("Note: nomor.net's `prov_code` for Papua Barat and Papua Barat Daya both report `92` "
              "(this is a kodepos-system quirk — both regions share the `9xxxx` kodepos prefix). "
              "Kemendagri official codes are: Papua=91, Papua Barat=92 (parent), Papua Barat Daya=92, "
              "Papua Selatan=93, Papua Tengah=94, Papua Pegunungan=95.")
    md.append("")
    papua_diffs = [d for d in kota_diffs if "Papua" in d["provinsi"]]
    if papua_diffs:
        md.append("### Papua kota/kab updates")
        md.append("")
        for d in papua_diffs:
            md.append(f"- **{d['provinsi']}**: master={d['mine_count']}, scrape={d['scrape_count']}")
            if d["only_mine"]:
                md.append(f"  - Only in master: {', '.join(f'`{x}`' for x in d['only_mine'])}")
            if d["only_scrape"]:
                md.append(f"  - Only in scrape (new): {', '.join(f'`{x}`' for x in d['only_scrape'])}")

    out = ROOT / "diff_hierarchy.md"
    out.write_text("\n".join(md), encoding="utf-8")
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()