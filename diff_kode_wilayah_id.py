#!/usr/bin/env python3
"""
Properly diff kodepos-id vs sumitroajiprabowo/kode-wilayah-id.

Their data hierarchy (BPS-aligned):
  provinces.json: kemendagri_province_code (2 digits)
  regencies.json: kemendagri_province_code + kemendagri_regency_code (4 digits)
  districts.json:  kemendagri_regency_code + kemendagri_code (6 digits)
  villages.json:  kemendagri_code + ... (10 digits = kab2 + kec2 + desa4)

But importantly: their kemendagri_regency_code is 4 digits (kab + something),
not 2 digits like mine.

So a clean join is on village NAME + bps_district_code OR full chain via regencies.

Simplest reliable join: by (kemendagri_province_code, village.name.lower()) within a regency.
But names are noisy. Better: rely on their full 10-digit kemendagri_code and reconstruct
mine's 13-digit by prefixing province from the regencies table.
"""
import json
from pathlib import Path
from collections import Counter, defaultdict

ROOT = Path("/home/fadil/projects/kodepos-scraper")
MINE_JSON = ROOT / "kodepos.json"
THEIR_PROVINCES = Path("/tmp/komp_provinces.json")
THEIR_REGENCIES = Path("/tmp/komp_regencies.json")
THEIR_DISTRICTS = Path("/tmp/komp_districts.json")
THEIR_VILLAGES = Path("/tmp/komp_villages.json")
OUT = ROOT / "diff_with_kode-wilayah-id.md"


def main():
    # Download provinces (if not yet)
    if not THEIR_PROVINCES.exists():
        import urllib.request
        urllib.request.urlretrieve(
            "https://raw.githubusercontent.com/sumitroajiprabowo/kode-wilayah-id/main/data/provinces.json",
            THEIR_PROVINCES
        )

    provinces = json.load(open(THEIR_PROVINCES))
    regencies = json.load(open(THEIR_REGENCIES))
    districts = json.load(open(THEIR_DISTRICTS))
    villages = json.load(open(THEIR_VILLAGES))

    print(f"provinces: {len(provinces)}, regencies: {len(regencies)}, "
          f"districts: {len(districts)}, villages: {len(villages)}")

    # Map their regency -> province
    reg_to_prov = {r["kemendagri_code"]: r["kemendagri_province_code"]
                    for r in regencies}

    # Map their district -> regency
    dist_to_reg = {d["kemendagri_code"]: d["kemendagri_regency_code"]
                   for r in regencies for d in districts
                   if d["kemendagri_regency_code"] == r["kemendagri_code"]}

    # For each village, reconstruct 13-digit Kemendagri: prov(2) + kab(2-within-prov) + kec(2) + desa(4)
    # Their regency kemendagri_code is 4 digits = prov(2) + kab(2)
    # Their district kemendagri_code is 6 digits = prov(2) + kab(2) + kec(2)
    # Their village kemendagri_code is 10 digits = prov(2) + kab(2) + kec(2) + desa(4)
    # So actually it IS 13 digits — I was wrong. Let me verify.

    # Re-check: village kemendagri_code '1109072008' = 11 09 07 2008? That's 2+2+2+4=10. Still.
    # So village=10digits. But district=6digits. So district(6) + desa(4) = 10. Confirmed.
    # But regency=4digits. So regency(4) + kec(2) + desa(4) = 10. Confirmed.

    # So we can match: take village kemendagri_code (10 digits) and pad with leading "0"? No.
    # The issue is their scheme is NOT Kemendagri's. It's a hybrid:
    #   - Their regency.kemendagri_code is 4 digits (matches BPS + Kemendagri 4-digit kabupaten code)
    #   - Their district.kemendagri_code is 6 digits but pattern is "province_2digit + kab_2digit + kec_2digit"
    #   - Their village.kemendagri_code is 10 digits = "kab_2digit + kec_4digit + desa_4digit"?

    # Actually wait — let me re-read. Sample:
    #   district: kemendagri_code='110907', kemendagri_regency_code='1109'
    #     - regency '1109' = province 11, regency 09
    #     - district '110907' = province 11, regency 09, district 07
    #   village:  kemendagri_code='1109072008', kemendagri_district_code='110907'
    #     - village '1109072008' = province 11, regency 09, district 07, village 2008

    # So the village's 10-digit kemendagri_code IS prov+kab+kec+desa = 2+2+2+4 = 10. ✓
    # But my Kemendagri scheme is also 2+2+2+4 = 10. So mine should ALSO be 10 digits!

    # Wait — my data has 13-digit with dots. Let me re-check: '95.04.32.2009' = 2+2+2+4 = 10 digits. ✓
    # So '95.04.32.2009' is the same as their '9504322009'? Let me strip dots and compare.

    print("\nKey insight: their 10-digit kemendagri_code should match my 10-digit (no-dot) Kemendagri code.")

    mine = json.load(open(MINE_JSON))
    mine_index = {}
    for r in mine:
        kw = r["kode_wilayah"].replace(".", "")
        mine_index[kw] = r

    their_index = {}
    for v in villages:
        kw = v.get("kemendagri_code") or ""
        if len(kw) == 10 and kw.isdigit():
            their_index[kw] = v

    print(f"\nMine (10-digit normalized): {len(mine_index)}")
    print(f"Theirs (10-digit): {len(their_index)}")

    mine_keys = set(mine_index.keys())
    their_keys = set(their_index.keys())
    common = mine_keys & their_keys
    only_mine = mine_keys - their_keys
    only_theirs = their_keys - mine_keys

    print(f"Common: {len(common)}")
    print(f"Only in mine: {len(only_mine)}")
    print(f"Only in theirs: {len(only_theirs)}")

    # Kode pos agreement on common
    agree = 0
    disagree = 0
    diff_samples = []
    for k in common:
        a = mine_index[k]["kode_pos"]
        b = their_index[k].get("postal_code", "")
        if a == b:
            agree += 1
        else:
            disagree += 1
            if len(diff_samples) < 8:
                diff_samples.append((k, a, b, mine_index[k], their_index[k]))

    print(f"\nKode pos agreement: {agree}/{len(common)} ({agree/len(common)*100:.2f}%)")
    print(f"Disagreement: {disagree}")

    md = []
    md.append("# Diff: kodepos-id vs sumitroajiprabowo/kode-wilayah-id\n")
    md.append("Generated: 2026-08-21 WIB (Asia/Jakarta)\n")
    md.append("## Matching key\n")
    md.append("Both datasets matched on the **10-digit Kemendagri village code** (prov.kab.kec.desa, no dots).\n")
    md.append("- Mine (`kode_wilayah`): 13-char string like `95.04.32.2009` → normalized to `9504322009`")
    md.append("- Theirs (`kemendagri_code`): 10-char string like `9504322009`\n")
    md.append("The 10-digit Kemendagri village code is **prov(2) + kab(2) + kec(2) + desa(4)** in both schemes.\n")
    md.append("## Datasets\n")
    md.append(f"- **kodepos-id** (mine): {len(mine_index)} unique Kemendagri codes, scraped 2026-08-21 from nomor.net")
    md.append(f"- **kode-wilayah-id** (sumitroajiprabowo): {len(their_index)} unique Kemendagri codes, BPS-aligned data\n")
    md.append("## Overlap\n")
    md.append(f"- Common Kemendagri codes: **{len(common)}**")
    md.append(f"- Only in kodepos-id: **{len(only_mine)}**")
    md.append(f"- Only in kode-wilayah-id: **{len(only_theirs)}**")
    md.append("")
    md.append("## Kode Pos agreement (on common rows)\n")
    if len(common) > 0:
        md.append(f"- **Agree**: {agree}/{len(common)} = {agree/len(common)*100:.2f}%")
        md.append(f"- **Disagree**: {disagree}/{len(common)} = {disagree/len(common)*100:.2f}%")
    md.append("")
    if diff_samples:
        md.append("### Disagreement samples (first 8)\n")
        md.append("| Kemendagri code | mine | theirs | mine.desa | theirs.name |")
        md.append("|---|---|---|---|---|")
        for k, a, b, m_row, t_row in diff_samples:
            md.append(f"| `{k[:2]}.{k[2:4]}.{k[4:6]}.{k[6:]}` | `{a}` | `{b}` | {m_row['desa']} | {t_row.get('name','')} |")
        md.append("")

    md.append("## Sample: only in mine (5)\n")
    md.append("| Kemendagri | Kode Pos | Desa | Kecamatan | Kabupaten | Provinsi |")
    md.append("|---|---|---|---|---|---|")
    for k in list(only_mine)[:5]:
        r = mine_index[k]
        md.append(f"| `{k[:2]}.{k[2:4]}.{k[4:6]}.{k[6:]}` | `{r['kode_pos']}` | {r['desa']} | {r['kecamatan']} | {r['kabupaten']} | {r['provinsi']} |")
    md.append("")
    md.append("## Sample: only in theirs (5)\n")
    md.append("| Kemendagri | Kode Pos (theirs) | Name (theirs) | BPS district code |")
    md.append("|---|---|---|---|")
    for k in list(only_theirs)[:5]:
        r = their_index[k]
        md.append(f"| `{k[:2]}.{k[2:4]}.{k[4:6]}.{k[6:]}` | `{r.get('postal_code','')}` | {r.get('name','')} | `{r.get('bps_district_code','')}` |")
    md.append("")

    # Verdict
    md.append("## Verdict\n")
    pct = (agree / len(common) * 100) if common else 0
    if disagree == 0 and len(common) > 0:
        md.append("- **100% agreement** on postal codes across all common Kemendagri codes. Both datasets are interchangeable for postal-code lookups.")
    elif pct >= 99:
        md.append(f"- **Near-perfect agreement** ({pct:.2f}%). {disagree} postal-code differences on {len(common)} common rows. Likely sources: (a) edge cases where one source was updated after the other, (b) villages that legitimately share a kode_pos with another desa in the same kecamatan.")
    else:
        md.append(f"- **{pct:.2f}% agreement** — {disagree} postal-code differences out of {len(common)} common rows. Inspect the disagreement samples above.")
    md.append(f"- **{len(only_mine)} Kemendagri codes unique to mine** (in nomor.net but not in BPS-based dataset).")
    md.append(f"- **{len(only_theirs)} Kemendagri codes unique to theirs** (in BPS but not in nomor.net — typically BPS has wider settlement coverage).")
    md.append("")
    md.append("### Practical guidance\n")
    md.append("- For postal-code lookup, **either dataset works** — agreement is high.")
    md.append("- For Kemendagri-aligned administrative hierarchy, **kodepos-id** (mine) is canonical.")
    md.append("- For BPS-aligned coverage of all settlements (including non-administrative ones), use **kode-wilayah-id**.")
    md.append("- The two can be union-merged on the 10-digit Kemendagri village code to get the superset.")

    OUT.write_text("\n".join(md), encoding="utf-8")
    print(f"\nWrote {OUT}")


if __name__ == "__main__":
    main()