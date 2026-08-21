# Diff: kodepos-id vs nomor.net hierarchy (kota/kab/prov)

Generated: 2026-08-21 WIB

Source: https://www.nomor.net/_kodepos.php?_i=provinsi-kodepos (and kota, kecamatan)

Master: kodepos_parsed.csv (83145 desa)
New scrape: wilayah_provinsi.csv (38), wilayah_kota.csv (514), wilayah_kecamatan.csv (7277)

## Provinsi comparison

| Provinsi | mine.desa | scrape.desa | Δ desa | mine.kab | scrape.kab | mine.kec | scrape.kec | prov_code |
|---|---|---|---|---|---|---|---|---|
| Aceh (NAD) | 6468 | 6500 | +32 🔴 | 23 | 18 | 286 | 290 | `11` |
| Bali | 711 | 716 | +5 🔴 | 9 | 8 | 57 | 57 | `51` |
| Banten | 1545 | 1552 | +7 🔴 | 6 | 4 | 152 | 155 | `36` |
| Bengkulu | 1494 | 1513 | +19 🔴 | 10 | 9 | 128 | 129 | `17` |
| DI Yogyakarta | 431 | 438 | +7 🔴 | 5 | 4 | 77 | 78 | `34` |
| DKI Jakarta | 266 | 267 | +1 🔴 | 6 | 1 | 44 | 44 | `31` |
| Gorontalo | 724 | 729 | +5 🔴 | 5 | 5 | 77 | 77 | `75` |
| Jambi | 1575 | 1585 | +10 🔴 | 11 | 9 | 144 | 144 | `15` |
| Jawa Barat | 5934 | 5957 | +23 🔴 | 21 | 18 | 581 | 627 | `32` |
| Jawa Tengah | 8520 | 8563 | +43 🔴 | 31 | 29 | 553 | 576 | `33` |
| Jawa Timur | 8458 | 8494 | +36 🔴 | 31 | 29 | 629 | 666 | `35` |
| Kalimantan Barat | 2134 | 2145 | +11 🔴 | 14 | 12 | 173 | 174 | `61` |
| Kalimantan Selatan | 2002 | 2016 | +14 🔴 | 13 | 11 | 155 | 156 | `63` |
| Kalimantan Tengah | 1564 | 1571 | +7 🔴 | 14 | 13 | 136 | 136 | `62` |
| Kalimantan Timur | 1029 | 1038 | +9 🔴 | 10 | 7 | 105 | 105 | `64` |
| Kalimantan Utara | 479 | 482 | +3 🔴 | 5 | 4 | 55 | 55 | `65` |
| Kepulauan Bangka Belitung | 389 | 393 | +4 🔴 | 7 | 6 | 47 | 47 | `19` |
| Kepulauan Riau | 417 | 419 | +2 🔴 | 7 | 5 | 80 | 80 | `21` |
| Lampung | 2643 | 2651 | +8 🔴 | 15 | 13 | 226 | 229 | `18` |
| Maluku | 1228 | 1235 | +7 🔴 | 11 | 9 | 118 | 118 | `81` |
| Maluku Utara | 1177 | 1185 | +8 🔴 | 10 | 8 | 118 | 118 | `82` |
| Nusa Tenggara Barat (NTB) | 1161 | 1166 | +5 🔴 | 9 | 8 | 117 | 117 | `52` |
| Nusa Tenggara Timur (NTT) | 3422 | 3442 | +20 🔴 | 21 | 21 | 315 | 315 | `53` |
| Papua | 970 | 999 | +29 🔴 | 8 | 8 | 104 | 105 | `91` |
| Papua Barat | 813 | 824 | +11 🔴 | 7 | 7 | 85 | 86 | `92` |
| Papua Barat Daya | 1003 | 1013 | +10 🔴 | 5 | 5 | 130 | 132 | `92` |
| Papua Pegunungan | 2558 | 2627 | +69 🔴 | 8 | 8 | 243 | 252 | `95` |
| Papua Selatan | 672 | 690 | +18 🔴 | 4 | 4 | 80 | 82 | `93` |
| Papua Tengah | 1154 | 1208 | +54 🔴 | 8 | 8 | 126 | 131 | `94` |
| Riau | 1837 | 1862 | +25 🔴 | 12 | 10 | 171 | 172 | `14` |
| Sulawesi Barat | 646 | 648 | +2 🔴 | 6 | 6 | 69 | 69 | `76` |
| Sulawesi Selatan | 3048 | 3059 | +11 🔴 | 24 | 21 | 310 | 313 | `73` |
| Sulawesi Tengah | 2010 | 2017 | +7 🔴 | 13 | 12 | 175 | 175 | `72` |
| Sulawesi Tenggara | 2274 | 2287 | +13 🔴 | 17 | 15 | 221 | 221 | `74` |
| Sulawesi Utara | 1832 | 1839 | +7 🔴 | 15 | 11 | 171 | 171 | `71` |
| Sumatera Barat | 1232 | 1265 | +33 🔴 | 18 | 12 | 176 | 179 | `13` |
| Sumatera Selatan | 3244 | 3258 | +14 🔴 | 17 | 13 | 241 | 241 | `16` |
| Sumatera Utara | 6081 | 6110 | +29 🔴 | 33 | 25 | 453 | 455 | `12` |

## Kota/Kab differences

_No kota/kab differences between master and scrape._

## Kecamatan differences (Papua-focused)

| Provinsi | Kabupaten | mine.count | scrape.count | Only in mine | Only in scrape |
|---|---|---|---|---|---|
| Bengkulu | Muko Muko | 14 | 15 | — | `XIV Koto` |
| Jawa Tengah | Wonogiri | 24 | 25 | — | `Wuryantoro` |
| Papua | Biak Numfor | 19 | 19 | — | — |
| Papua | Jayapura | 24 | 24 | — | — |
| Papua | Keerom | 10 | 11 | — | `Yaffi` |
| Papua | Kepulauan Yapen | 17 | 17 | — | — |
| Papua | Mamberamo Raya | 8 | 8 | — | — |
| Papua | Sarmi | 10 | 10 | — | — |
| Papua | Supiori | 5 | 5 | — | — |
| Papua | Waropen | 11 | 11 | — | — |
| Papua Barat | Fak Fak | 17 | 17 | — | — |
| Papua Barat | Kaimana | 6 | 7 | — | `Yamor` |
| Papua Barat | Manokwari | 9 | 9 | — | — |
| Papua Barat | Manokwari Selatan | 6 | 6 | — | — |
| Papua Barat | Pegunungan Arfak | 10 | 10 | — | — |
| Papua Barat | Teluk Bintuni | 24 | 24 | — | — |
| Papua Barat | Teluk Wondama | 13 | 13 | — | — |
| Papua Barat Daya | Maybrat | 24 | 24 | — | — |
| Papua Barat Daya | Raja Ampat | 24 | 24 | — | — |
| Papua Barat Daya | Sorong | 39 | 39 | — | — |
| Papua Barat Daya | Sorong Selatan | 15 | 15 | — | — |
| Papua Barat Daya | Tambrauw | 29 | 29 | — | — |
| Papua Pegunungan | Jayawijaya | 39 | 40 | — | `Yalengga` |
| Papua Pegunungan | Lanny Jaya | 39 | 39 | — | — |
| Papua Pegunungan | Mamberamo Tengah | 5 | 5 | — | — |
| Papua Pegunungan | Nduga | 29 | 32 | — | `Wusi`, `Wutpaga`, `Yal` |
| Papua Pegunungan | Pegunungan Bintang | 34 | 34 | — | — |
| Papua Pegunungan | Tolikara | 46 | 46 | — | — |
| Papua Pegunungan | Yahukimo | 49 | 51 | — | `Wusama`, `Yahuliambut` |
| Papua Pegunungan | Yalimo | 5 | 5 | — | — |
| Papua Selatan | Asmat | 25 | 25 | — | — |
| Papua Selatan | Boven Digoel | 19 | 20 | — | `Yaniruma` |
| Papua Selatan | Mappi | 14 | 15 | — | `Yakomi` |
| Papua Selatan | Merauke | 22 | 22 | — | — |
| Papua Tengah | Deiyai | 5 | 5 | — | — |
| Papua Tengah | Dogiyai | 10 | 10 | — | — |
| Papua Tengah | Intan Jaya | 8 | 8 | — | — |
| Papua Tengah | Mimika | 18 | 18 | — | — |
| Papua Tengah | Nabire | 15 | 15 | — | — |
| Papua Tengah | Paniai | 23 | 24 | — | `Yagai` |
| Papua Tengah | Puncak | 25 | 25 | — | — |
| Papua Tengah | Puncak Jaya | 23 | 26 | — | `Yambi`, `Yamo`, `Yamoneri` |
| Riau | Kampar | 20 | 21 | — | `XIII Koto Kampar` |
| Sumatera Barat | Solok | 14 | 16 | — | `X Koto Diatas`, `X Koto Singkarak` |
| Sumatera Barat | Tanah Datar | 13 | 14 | — | `X Koto (Sepuluh Koto)` |

## Verdict

## Papua region coverage

- **Papua**: prov_code=`91`, kab=8, kec=105, desa=999
- **Papua Barat**: prov_code=`92`, kab=7, kec=86, desa=824
- **Papua Barat Daya**: prov_code=`92`, kab=5, kec=132, desa=1013
- **Papua Pegunungan**: prov_code=`95`, kab=8, kec=252, desa=2627
- **Papua Selatan**: prov_code=`93`, kab=4, kec=82, desa=690
- **Papua Tengah**: prov_code=`94`, kab=8, kec=131, desa=1208

Note: nomor.net's `prov_code` for Papua Barat and Papua Barat Daya both report `92` (this is a kodepos-system quirk — both regions share the `9xxxx` kodepos prefix). Kemendagri official codes are: Papua=91, Papua Barat=92 (parent), Papua Barat Daya=92, Papua Selatan=93, Papua Tengah=94, Papua Pegunungan=95.
