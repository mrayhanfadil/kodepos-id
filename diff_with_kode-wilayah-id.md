# Diff: kodepos-id vs sumitroajiprabowo/kode-wilayah-id

Generated: 2026-08-21 WIB (Asia/Jakarta)

## Matching key

Both datasets matched on the **10-digit Kemendagri village code** (prov.kab.kec.desa, no dots).

- Mine (`kode_wilayah`): 13-char string like `95.04.32.2009` → normalized to `9504322009`
- Theirs (`kemendagri_code`): 10-char string like `9504322009`

The 10-digit Kemendagri village code is **prov(2) + kab(2) + kec(2) + desa(4)** in both schemes.

## Datasets

- **kodepos-id** (mine): 83145 unique Kemendagri codes, scraped 2026-08-21 from nomor.net
- **kode-wilayah-id** (sumitroajiprabowo): 77180 unique Kemendagri codes, BPS-aligned data

## Overlap

- Common Kemendagri codes: **76666**
- Only in kodepos-id: **6479**
- Only in kode-wilayah-id: **514**

## Kode Pos agreement (on common rows)

- **Agree**: 76594/76666 = 99.91%
- **Disagree**: 72/76666 = 0.09%

### Disagreement samples (first 8)

| Kemendagri code | mine | theirs | mine.desa | theirs.name |
|---|---|---|---|---|
| `35.05.11.2008` | `66182` | `66181` | Sidodadi | SIDODADI |
| `35.05.17.1004` | `66185` | `66184` | Wlingi | WLINGI |
| `61.12.09.2013` | `78380` | `78381` | Punggur Kapuas | PUNGGUR KAPUAS |
| `53.03.20.1006` | `85670` | `None` | Atmen (Kelurahan Atmen) | DESA ADMEN |
| `53.03.06.1001` | `85683` | `None` | Boronubaen | BORONUBAEN |
| `91.03.01.2007` | `99352` | `None` | Keheran (Kehiran) | YOBOY / KEHUSA / KEHIRAN |
| `91.03.02.2007` | `99359` | `None` | Yokiwa | YOKIWA |
| `35.05.11.1004` | `66182` | `66181` | Garum | GARUM |

## Sample: only in mine (5)

| Kemendagri | Kode Pos | Desa | Kecamatan | Kabupaten | Provinsi |
|---|---|---|---|---|---|
| `95.04.22.2006` | `99060` | Koinggambu | Timori | Tolikara | Papua Pegunungan |
| `92.09.07.2002` | `98374` | Banso | Syujak | Tambrauw | Papua Barat Daya |
| `93.01.01.1004` | `99617` | Mandala | Merauke | Merauke | Papua Selatan |
| `95.04.44.2007` | `99031` | Tingwi | Li Anogomma | Tolikara | Papua Pegunungan |
| `95.02.21.2009` | `99426` | Honkuding | Oksamol | Pegunungan Bintang | Papua Pegunungan |

## Sample: only in theirs (5)

| Kemendagri | Kode Pos (theirs) | Name (theirs) | BPS district code |
|---|---|---|---|
| `72.07.17.2001` | `94889` | SAMBULANGAN | `7201062` |
| `71.03.08.2025` | `95856` | BOWONGKULU I | `7103100` |
| `74.04.11.2024` | `93752` | LABURUNCI | `7401060` |
| `33.13.09.1012` | `57716` | GEDONG | `3313090` |
| `33.12.09.2004` | `57661` | MLOPOHARJO | `3312110` |

## Verdict

- **Near-perfect agreement** (99.91%). 72 postal-code differences on 76666 common rows. Likely sources: (a) edge cases where one source was updated after the other, (b) villages that legitimately share a kode_pos with another desa in the same kecamatan.
- **6479 Kemendagri codes unique to mine** (in nomor.net but not in BPS-based dataset).
- **514 Kemendagri codes unique to theirs** (in BPS but not in nomor.net — typically BPS has wider settlement coverage).

### Practical guidance

- For postal-code lookup, **either dataset works** — agreement is high.
- For Kemendagri-aligned administrative hierarchy, **kodepos-id** (mine) is canonical.
- For BPS-aligned coverage of all settlements (including non-administrative ones), use **kode-wilayah-id**.
- The two can be union-merged on the 10-digit Kemendagri village code to get the superset.