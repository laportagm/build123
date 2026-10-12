# Order list for the first unit

> **Personal prototype for bench evaluation. Not a cleared medical device.**
> Not for diagnosis, treatment or clinical use. **No order has been placed.**

This is the purchase list for build 1: every BOM line, with spares, re-checked on
2026-10-12.
- It starts from the [order pack](../07-order/order.md) and its cart files. Those stay
  unchanged.
- **One change:** one more ring LED of each wavelength (10 → 11, see §1). After uploading
  `digikey_cart.csv`, edit those two lines.

**How prices were checked.** The distributor sites cannot be opened from this
environment: the proxy refuses Digi-Key, LCSC, Mouser and Adafruit. So:
- Stock and prices come from search-result snippets of the distributor pages. Each is
  cited as [S…] and listed in §7.
- Snippets of the same page often disagree. The unit price used is the **highest** seen,
  either in this check or in the BOM's own check earlier the same day (`bom.csv`,
  "verification" column). That is the BOM's existing rule.
- **Check every line on the live page before paying** (checklist 1.3).

## Totals

| Order | Lines | Cost (USD) | Order pack |
|---|---|---|---|
| Digi-Key | 8 | **27.31** | 26.44 (+0.87: the two extra LEDs) |
| LCSC | 18 | **13.35** | 13.35 |
| Adafruit | 3 | **2.25** | 2.25 |
| **Parts** | 29 | **42.91** | 42.04 |
| PCB, 5 boards, 1.0 mm | — | 5–15 (estimate, NV) | order.md §1 |
| **One device, parts + PCB** | | **47.91–57.91** | brief: ≤ 75 |
| Tool: UPDI Friend (one-off) | 1 | 6.95 | order.md §5 |

- Shipping and filament are not included.
- **The PCB price is not verified.** JLCPCB's "$2 for 5 pcs" offer is quoted for its
  standard 1.6 mm, 100 × 100 mm board [S37]. No price for 1.0 mm was found. Get the fab's
  instant quote.

## 1. Spares

| Rule (your brief) | Part | Fitted | Ordered | Spares | Why that many |
|---|---|---|---|---|---|
| ≥ 2 extra LEDs per wavelength | 660 nm XZM2MR55W-3 (D2–D7) | 6 | **11** | 5 | 2 spares, plus 3 loose LEDs for the optical-power test (checklist 3.8 measures 3 of each type) |
| ≥ 2 extra LEDs per wavelength | 625 nm XZM2CRK55W-3 (D8–D13) | 6 | **11** | 5 | as above |
| LEDs, easy to damage | amber LTST-C190KSKT (D14–D18) | 5 | 20 | 15 | LCSC minimum order |
| 1 extra thermistor | NTC NCP18XH103F03RB (RT1) | 1 | 10 | 9 | LCSC price break |
| Spare R9 (no ballast resistors in this design) | 8.2 Ω RC0603FR-078R2L (R9) | 1 | 100 | 99 | LCSC price break |
| TPS61169 | TPS61169DCKR (U3) | 1 | 5 | 4 | LCSC minimum order |
| Fine pitch | U3 is the finest part, SC-70-5 at **0.65 mm** pitch (footprint `ee/lib/vf.pretty/SC-70-5_HandSolder`) | | | | covered above |
| Next finest | BQ21040 (U2, SOT-23-6, 0.95 mm pitch) | 1 | 5 | 4 | LCSC minimum order |
| Coarser, spares anyway | AO3400A (Q1, Q2, SOT-23) · ATtiny1614 (U1, SOIC-14, 1.27 mm) · USB-C (J1, pads ≥ 1.0 mm apart, `params.py` USB_PADS_X) | 2 · 1 · 1 | 5 · 2 · 2 | 3 · 1 · 1 | LCSC minimum order; order pack |

Pitches come from the footprints in `ee/design.py` (KiCad `SOT-23-6`, `SOT-23`,
`SOIC-14_3.9x8.7mm_P1.27mm`; project `SC-70-5_HandSolder`, pads 0.65 mm apart).

**No spare cell.** The cell is not in the spare rule, ships by ground only, and costs
$10.81. Add one only if you want it.

## 2. Digi-Key

Upload [`digikey_cart.csv`](../07-order/digikey_cart.csv), then **change the two LED
quantities from 10 to 11.**

| Order | Fitted | Part (refs) | MPN | Digi-Key PN | Unit $ | Line $ | Re-check 2026-10-12 | Flag |
|---|---|---|---|---|---|---|---|---|
| 2 | 1 | USB-C (J1) | GCT USB4515-GF-A | [2073-USB4515-GF-ACT-ND](https://www.digikey.com/en/products/result?keywords=USB4515-GF-A) | 0.61 | 1.22 | 8,500–11,600 in stock across regional pages, active, 7-week lead [S8]; no USD price in snippets, so the BOM's $0.61 @1 (digikey.com page) stands | — |
| 1 | 1 | Cell (BT1) | Jauch LP503040JH+PCM+2 WIRES 50MM | [1908-LP503040JH+PCM+2WIRES50MM-ND](https://www.digikey.com/en/products/detail/jauch-quartz/LP503040JH-PCM-2-WIRES-50MM/9560983) | 10.81 | 10.81 | 1,727 in stock, $10.50 @1, 28-week lead once stock runs out (aggregator) [S12] | F8 |
| 2 | 1 | MCU (U1) | Microchip ATTINY1614-SSNR | [ATTINY1614-SSNRCT-ND](https://www.digikey.com/en/products/result?keywords=ATTINY1614-SSNR) | 0.90 | 1.80 | active, 7-week lead [S11]; no stock or price in snippets; the BOM's check gave $0.90 @1, 33,040 in stock | — |
| **11** | 6 | 660 nm LEDs (D2–D7) | SunLED XZM2MR55W-3 | [1497-1364-1-ND](https://www.digikey.com/en/products/detail/sunled/XZM2MR55W-3/6709143) | 0.54 | **5.94** | 20,945–23,004 in stock, active; $0.67 @1, $0.462 @10, $0.335 @100 [S1]. 660 nm peak [S35] | — |
| **11** | 6 | 625 nm LEDs (D8–D13) | SunLED XZM2CRK55W-3 | [1497-1405-1-ND](https://www.digikey.com/en/products/result?keywords=XZM2CRK55W-3) | 0.326 | **3.59** | digikey.com: 16,312 in stock, active, $0.14–0.48 by quantity [S2]. Other regional pages: 0, backorder [S4]. One reseller says discontinued [S3]. 1.80 mm max height [S34] | **F1** |
| 1 | 6 posts | Header strip, 40 pins (H1) | Sullins PRPC040SAAN-RC | [S1011EC-40-ND](https://www.digikey.com/en/products/detail/PRPC040SAAN-RC/S1011EC-40-ND/2775214) | 1.23 | 1.23 | 46,321 in stock, active; $1.23 @1, $1.041 @10; 11-week lead [S18]. Settles the BOM's $0.55 / $1.23 conflict: $1.23 | — |
| 3 | 2 | Magnet 1/4 × 1/8″ N35 (sole dowels) | Radial Magnets 8193 | [469-1004-ND](https://www.digikey.com/en/products/result?keywords=469-1004-ND) | 0.40 | 1.20 | US page about 14,078 in stock, $0.38 @1; confirmed N35 NdFeB, 6.35 × 3.18 mm, NiCuNi [S16] | — |
| 8 | 6 | Magnet 1/4 × 1/16″ N35 | Radial Magnets 8195 | [469-1005-ND](https://www.digikey.com/en/products/result?keywords=469-1005-ND) | 0.19 | 1.52 | 12,532 in stock at $0.18 (US listing); 23,086 (Brazil page); one USD page shows 0 in stock, $0.18 @1, $0.148 @10, 3-week lead [S17] | F4 |
| | | | | | **Total** | **27.31** | | |

## 3. LCSC

Upload [`lcsc_cart.csv`](../07-order/lcsc_cart.csv) unchanged. Its quantities already
meet LCSC's minimums.

| Order | Fitted | Part (refs) | MPN | LCSC PN | Unit $ | Line $ | Re-check 2026-10-12 | Flag |
|---|---|---|---|---|---|---|---|---|
| 100 | 2 | 5.1 k (R1 R2) | UNI-ROYAL 0603WAF5101T5E | [C23186](https://www.lcsc.com/product-detail/C23186.html) | 0.0026 | 0.26 | 2.40–4.00 M in stock; $0.0012–0.0016 @100 [S23] | — |
| 5 | 1 | Charger (U2) | TI BQ21040DBVR | [C202311](https://www.lcsc.com/product-detail/C202311.html) | 0.3303 | 1.65 | 5,590–14,085 in stock; $0.2736–0.3186 @5 [S10] | — |
| 100 | 1 | 2.2 k (R3) | UNI-ROYAL 0603WAF2201T5E | [C4190](https://www.lcsc.com/product-detail/C4190.html) | 0.0041 | 0.41 | 0.47–3.7 M in stock [S24] | — |
| 100 | 2 | 10 k (R4 R8) | Yageo RC0603FR-0710KL | [C98220](https://www.lcsc.com/product-detail/C98220.html) | 0.0034 | 0.34 | one copy 9.03 M in stock, **another 0, out of stock**; $0.0014–0.0015 @100 [S25] | **F2** |
| 50 | 3 | 1 µF 25 V (C1 C2 C4) | Samsung CL10B105KA8NNNC | [C29936](https://www.lcsc.com/product-detail/C29936.html) | 0.0225 | 1.12 | one copy about 4,000 in stock (the BOM's check: 3.0–6.5 M); $0.0143 @50 [S26] | — |
| 100 | 6 | 100 k (R5 R6 R7 R10 R11 R12) | Yageo RC0603FR-07100KL | [C14675](https://www.lcsc.com/product-detail/C14675.html) | 0.0047 | 0.47 | 1.52–2.27 M in stock; $0.0010–0.0014 @100 [S27] | — |
| 100 | 1 | 100 nF (C3) | Samsung CL10B104KB8NNNC | [C1591](https://www.lcsc.com/product-detail/C1591.html) | 0.016 | 1.60 | 4,000–13.25 M in stock; $0.0027–0.0066 @100 [S28] | — |
| 5 | 1 | Tact switch (SW1) | Omron (Aratas) B3F-1020 | [C722171](https://www.lcsc.com/product-detail/C722171.html) | 0.1523 | 0.76 | no LCSC snippet; an aggregator shows 1,155 at LCSC, $0.145 [S15]; the BOM's check: 700–1,940, one copy out of stock | **F3** |
| 10 | 1 | NTC 10 k (RT1) | Murata NCP18XH103F03RB | [C13564](https://www.lcsc.com/product-detail/C13564.html) | 0.0467 | 0.47 | 510,410–721,760 in stock; $0.0295 @10, or $0.0376 @20 on a copy whose list starts at 20 [S7]; one copy: not recommended for new designs | F6 |
| 5 | 1 | LED driver (U3) | TI TPS61169DCKR | [C71045](https://www.lcsc.com/product-detail/C71045.html) | 0.3268 | 1.63 | 8,475–8,970 in stock; $0.16–0.33 @5 [S5] | — |
| 10 | 1 | 10 µH inductor (L1) | Sunlord SWPA4018S100MT | [C83442](https://www.lcsc.com/product-detail/C83442.html) | 0.0594 | 0.59 | 1,459 in stock; $0.0594 @10, minimum 10 [S19] | — |
| 10 | 1 | Schottky (D1) | onsemi MBR0540T1G | [C21353](https://www.lcsc.com/product-detail/C21353.html) | 0.061 | 0.61 | 47,700–145,260 in stock; $0.055–0.061 @10 [S20] | — |
| 10 | 2 | 1 µF 50 V 1206 (C5 C6) | Samsung CL31B105KBHNNNE | [C1848](https://www.lcsc.com/product-detail/C1848.html) | 0.0492 | 0.49 | 573,070 in stock; $0.0221 @10 [S21] | — |
| 5 | 1 | 10 µF 25 V 0805 (C7) | Murata GRM21BR61E106KA73L | [C84416](https://www.lcsc.com/product-detail/C84416.html) | 0.1764 | 0.88 | 121,900–484,120 in stock; $0.0297 @20, $0.0179 @50; one copy: not recommended for new designs [S22] | — |
| 100 | 1 | **8.2 Ω, sets the LED current (R9)** | Yageo RC0603FR-078R2L | [C137674](https://www.lcsc.com/product-detail/C137674.html) | 0.0054 | 0.54 | 2,300 in stock; $0.0054 @100 [S6] | — |
| 5 | 2 | N-MOSFET (Q1 Q2) | AOS AO3400A | [C20917](https://www.lcsc.com/product-detail/C20917.html) | 0.0898 | 0.45 | 100,725–1,142,350 in stock [S13] | — |
| 20 | 5 | Amber LED (D14–D18) | Lite-On LTST-C190KSKT | [C125095](https://www.lcsc.com/product-detail/C125095.html) | 0.0248 | 0.50 | about 194,653 in stock on LCSC's Chinese site, a page about 194 days old [S14] | **F5** |
| 100 | 5 | 1 k (R13–R17) | Yageo RC0603FR-071KL | [C22548](https://www.lcsc.com/product-detail/C22548.html) | 0.0058 | 0.58 | 9.64–9.95 M in stock; $0.0011 @100; one copy: not recommended for new designs [S29] | — |
| | | | | | **Total** | **13.35** | | |

## 4. Adafruit

| Order | Part | Adafruit PID | Unit $ | Line $ | Re-check 2026-10-12 | Flag |
|---|---|---|---|---|---|---|
| 1 | Silicone wire 30 AWG, red, 2 m | [2001](https://www.adafruit.com/product/2001) | 0.75 | 0.75 | $0.75 (1–9) [S30]; Mouser 485-2001: 59 in stock | — |
| 1 | Silicone wire 30 AWG, black, 2 m | [2003](https://www.adafruit.com/product/2003) | 0.75 | 0.75 | $0.75 (1–9) [S31]; stock not shown | — |
| 1 | Foam tape, 2 pieces | [5019](https://www.adafruit.com/product/5019) | 0.75 | 0.75 | $0.75 (1–9); the listing says "3/4" x 1.5" x 0.063" / 37.7mm x 19mm x 1mm" [S32]; stock not shown | F9 |
| | | | **Total** | **2.25** | | |

**Tool:** Adafruit UPDI Friend 5879, Digi-Key
[1528-5879-ND](https://www.digikey.com/en/products/detail/adafruit-industries-llc/5879/22596413):
$6.95, 40 in stock on one snapshot [S33].

## 5. Flags, fallbacks and their re-verification

| # | Line | Finding | What to do |
|---|---|---|---|
| **F1** | 625 nm LED, XZM2CRK55W-3 | digikey.com shows 16,312 in stock and "Active" [S2]. Some regional Digi-Key pages show 0 and backorder [S4], and one reseller calls it discontinued [S3]. | **No verified substitute.** Digi-Key's German page suggests XZM2ACR55W-3, but no datasheet for it was found. Its sibling XZM2ACR55W-1 is a flat-top lens 0.75 mm tall [S36], so the family is not a verified drop-in. A substitute must fit the 625 nm positions: 1206 dome, ≤ 1.80 mm tall (`params.py` LED_H, where the sole is thinnest), and ≤ 30 mA. If the live page shows no stock, **stop**. Checklist 1.3 treats that as a blocker that needs a BOM change and a `check_fit` re-run. |
| **F2** | 10 k, LCSC C98220 | One LCSC copy shows 0 in stock [S25]. | **Fallback, re-verified:** the same part, Yageo RC0603FR-0710KL, from Digi-Key as **311-10.0KHRCT-ND** (the BOM's alternate). An aggregator ties that number to this MPN, with 9.5–14.1 M in stock, $0.10 @1 and $0.006 @10 [S25]. Same MPN, so the 1 % value R8 needs for the NTC divider is unchanged. Add 10 to the Digi-Key order (about $0.06–0.10). |
| **F3** | Tact switch, LCSC C722171 | No LCSC page in today's snippets; one LCSC copy was out of stock in the BOM's check. | **Fallback, re-verified:** Digi-Key **SW402-ND** is the B3F-1020. Digi-Key's listing maps it to that MPN, with 100 gf force and a **5.00 mm** actuator height. That is `params.py` SWITCH_H = 5.0, so the button stack is unchanged. $0.42 @1 (digikey.com); 23,492 in stock and a 26-week lead on digikey.ca [S15]. Order 2 (1 + 1 spare, as for J1 and U1). |
| F4 | Magnet 8195 | One USD snapshot shows 0 in stock [S17]. | No other N35 1/4 × 1/16″ part is stocked (electronics §7), so there is no fallback. If the live page shows none, **stop**: another grade or size needs the magnet model re-run (`cad/device/checks.py`). |
| **F5** | Amber LED, LCSC C125095 | Only a stale LCSC page was found [S14]. The BOM's alternate, Digi-Key 160-1437-1-ND, now shows out of stock and backorder (20-week lead) on regional pages [S14]. | The alternate is not a dependable fallback today. If LCSC has none, **stop and ask**: a different amber part needs its forward voltage checked against the 1 k resistors (electronics §2). |
| F6 | NTC, LCSC C13564 | One copy's price list starts at 20 pieces [S7]. | If LCSC raises the line to 20, it costs at most $0.47 more at the price used. |
| F7 | 1 µF, LCSC C29936 | One copy shows about 4,000 in stock [S26]. | Still above the 50 ordered; no action. |
| F8 | Cell | Lead time 28 weeks once Digi-Key's stock runs out [S12]. Li-ion: **ground shipping only** (order.md §6). | Order it first. |
| F9 | Foam tape | The listing gives both 0.063″ (1.6 mm) and 1 mm [S32]. | Measure it on arrival: tape + cell ≤ 7.4 mm (build §4.3, checklist 2.1). |
| F10 | LED wavelengths | Digi-Key lists XZM2MR55W-3 with a 660 nm peak (640 nm dominant per [S35]), and XZM2CRK55W-3 as "Red 625nm" with a 640 nm peak-wavelength field [S34]. | No sourcing change. Use these wavelengths when setting the optical power meter (bench sheet, item 1). |

## 6. Before you pay

- Open every line on the live page; confirm part number, stock ≥ order and price
  (checklist 1.3).
- Digi-Key: **11** of each ring LED; the cell by **ground**. Add F2's resistor or F3's
  switch only if LCSC lacks them.
- PCB: settings in order.md §1. **1.0 mm** thick. Read the fab's DFM report (checklist 1.4).
- Keep the two LED reels apart when they arrive (order.md §6).

## 7. Sources (search snippets, 2026-10-12)

- [S1] Digi-Key NL, XZM2MR55W-3, prices in USD: https://www.digikey.nl/en/products/detail/sunled/XZM2MR55W-3/6709143
- [S2] Digi-Key US, XZM2CRK55W-3: https://www.digikey.com/en/products/detail/sunled/XZM2CRK55W-3/4901982
- [S3] CDIWEB, XZM2CRK55W-3: https://www.cdiweb.com/products/detail/xzm2crk55w3-sunled-company-llc/555458/
- [S4] Digi-Key regional pages, XZM2CRK55W-3: https://punchouttest.digikey.kr/en/products/detail/sunled/XZM2CRK55W-3/4901982 · https://punchouttest.digikey.de/en/products/detail/sunled/XZM2CRK55W-3/4901982 · https://www.digikey.sg/en/products/detail/sunled/XZM2CRK55W-3/4901982
- [S5] LCSC C71045: https://www.lcsc.com/product-image/C71045.html
- [S6] LCSC C137674: https://www.lcsc.com/product-image/C137674.html
- [S7] LCSC C13564: https://www.lcsc.com/product-image/C13564.html · https://fat.lcsc.com/product-image/C13564.html
- [S8] Digi-Key, USB4515-GF-A: https://www.digikey.ch/en/products/detail/gct/USB4515-GF-A/15635474
- [S10] LCSC C202311: https://www.lcsc.com/product-image/C202311.html
- [S11] Digi-Key, ATTINY1614-SSNR: https://digikey.dk/en/products/detail/microchip-technology/ATTINY1614-SSNR/7354616
- [S12] Findchips, Jauch LP503040JH at Digi-Key: https://www.findchips.com/search/LP503
- [S13] LCSC C20917: https://www.lcsc.com/product-image/C20917.html
- [S14] LCSC (Chinese site), C125095: https://item.szlcsc.com/136371.html · Digi-Key 160-1437-1-ND: https://punchouttest.digikey.com.mx/en/products/detail/liteon/LTST-C190KSKT/386818
- [S15] Digi-Key SW402-ND = B3F-1020: https://www.digikey.com/product-detail/en/omron-electronics-inc-emc-div/B3F-1020/SW402-ND/44059 · https://digikey.ca/product-detail/en/omron-electronics-inc-emc-div/B3F-1020/SW402-ND/44059 · aggregator: https://www.digipart.com/part/B3F-1020
- [S16] Digi-Key, Radial Magnets 8193: https://www.digikey.com/en/products/detail/radial-magnets-inc/8193/555328
- [S17] Digi-Key, Radial Magnets 8195: https://www.digikey.com.br/en/products/detail/radial-magnets-inc/8195/555329 · https://www.digikey.com/en/products/filter/magnets-multi-purpose/511
- [S18] Digi-Key, S1011EC-40-ND: https://www.digikey.com/en/products/detail/PRPC040SAAN-RC/S1011EC-40-ND/2775214
- [S19] LCSC C83442: https://lcsc.com/product-detail/Power-Inductors_10uH-20_C83442.html
- [S20] LCSC C21353: https://www.lcsc.com/product-image/C21353.html
- [S21] LCSC C1848: https://www.lcsc.com/product-image/C1848.html
- [S22] LCSC C84416: https://www.lcsc.com/product-image/C84416.html
- [S23] LCSC C23186: https://www.lcsc.com/product-image/C23186.html
- [S24] LCSC C4190: https://www.lcsc.com/product-image/C4190.html
- [S25] LCSC C98220: https://www.lcsc.com/product-image/C98220.html · Digi-Key 311-10.0KHRCT-ND (aggregator): https://www.oemstrade.com/search/rc0603fr0710kl%20(lf)
- [S26] LCSC C29936: https://www.lcsc.com/product-image/C29936.html
- [S27] LCSC C14675: https://www.lcsc.com/product-image/C14675.html
- [S28] LCSC C1591: https://www.lcsc.com/product-image/C1591.html
- [S29] LCSC C22548: https://www.lcsc.com/product-image/C22548.html
- [S30] Adafruit 2001: https://www.adafruit.com/products/2001 · Mouser 485-2001: https://www.mouser.com/ProductDetail/485-2001
- [S31] Adafruit 2003: https://www.adafruit.com/products/2003
- [S32] Adafruit 5019: https://www.adafruit.com/product/5019
- [S33] Digi-Key, Adafruit 5879: https://www.digikey.com/en/products/detail/adafruit-industries-llc/5879/22596413
- [S34] Digi-Key, XZM2CRK55W-3 fields: https://digikey.cn/en/products/detail/sunled/XZM2CRK55W-3/4901982
- [S35] Zenode, XZM2MR55W-3: https://zenode.ai/parts/1g1z958dx6
- [S36] Digi-Key, XZM2ACR55W-1: https://www.digikey.com/en/products/detail/sunled/XZM2ACR55W-1/1497-1148-1-ND/4745622
- [S37] JLCPCB promotion table: https://jlcpcb.com/blog/4-free · standard spec: https://jlcpcb.com/help/article/pcb-fabrication-services-and-production-time
