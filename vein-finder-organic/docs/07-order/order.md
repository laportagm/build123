# Order pack

> **Personal prototype for bench evaluation. Not a cleared medical device.**
> Not for diagnosis, treatment or clinical use.

Everything needed to order one device: the board, three parts orders and one tool.
The files here are made from `ee/design.py` by `ee/make_order.py`; quantities include
minimum order sizes and a few spares. **Prices and stock come from search-result
snippets** (the distributor pages could not be opened from where this was made),
re-checked on 2026-10-12; where cached copies of a page disagree, the highest price is
used. Check each line on the live page before paying.

| Order | What | Cost (USD) |
|---|---|---|
| PCB fab | 5 bare boards (§1) | 5–15 (estimate, NV) |
| Digi-Key | 8 lines (§2) | 26.44 |
| LCSC | 18 lines (§3) | 13.35 |
| Adafruit | 3 lines (§4) | 2.25 |
| **Parts + PCB** | | **47–57** |
| Tool, one-off | UPDI programmer (USB-C, 3 V / 5 V) | 6.95 |

Shipping is not included.

## 1. PCB

Upload [`vein_finder-gerbers.zip`](../03-electronics/fab/vein_finder-gerbers.zip) (Gerbers and drill files) to any
fab (JLCPCB, PCBWay, OSH Park, …). Choose:

| Setting | Value |
|---|---|
| Layers | 2 |
| Size | 85.8 × 54.5 mm (the fab reads it from the outline) |
| **Thickness** | **1.0 mm** (not the usual 1.6 mm: the stone is sized for 1.0) |
| Copper | 1 oz (35 µm) outer |
| Surface finish | HASL (lead-free) or ENIG |
| Solder mask | any colour; black matches the sole |
| Silkscreen | white |
| Quantity | 5 (the usual minimum) |
| Assembly, stencil | none: everything is hand-soldered |

What the fab's checks will see:

- Smallest track 0.25 mm (0.2 mm minimum gap); vias 0.6 mm pad, 0.3 mm drill.
- Holes: 1.0 mm plated (6 locating pins); plated slots 0.6 × 1.2 and 0.6 × 1.6 mm (USB-C shell).
- Edge: 0.3 mm copper to edge, except the USB-C pads at 0.20 mm (datasheet land pattern). **Check that one against the fab's
  copper-to-board-edge minimum**; if it is larger, ask the fab whether it can pull the
  copper back at the USB-C notch.
- The outline is a C with four magnet holes; the two at the tail open onto the edge. The fab
  routes them like any outline.

## 2. Digi-Key

Upload [`digikey_cart.csv`](digikey_cart.csv) with Digi-Key's list / BOM upload and map the columns (Quantity, Digi-Key Part Number), or add the lines one by one.

| Qty | Part number | Manufacturer, MPN | For | Unit $ | Line $ |
|---|---|---|---|---|---|
| 2 | [2073-USB4515-GF-ACT-ND](https://www.digikey.com/en/products/result?keywords=USB4515-GF-A) | GCT USB4515-GF-A | J1 | 0.61 | 1.22 |
| 1 | [1908-LP503040JH+PCM+2WIRES50MM-ND](https://www.digikey.com/en/products/detail/jauch-quartz/LP503040JH-PCM-2-WIRES-50MM/9560983) | Jauch LP503040JH+PCM+2 WIRES 50MM | BT1 | 10.81 | 10.81 |
| 2 | [ATTINY1614-SSNRCT-ND](https://www.digikey.com/en/products/result?keywords=ATTINY1614-SSNR) | Microchip ATTINY1614-SSNR | U1 | 0.9 | 1.80 |
| 10 | [1497-1364-1-ND](https://www.digikey.com/en/products/detail/sunled/XZM2MR55W-3/6709143) | SunLED XZM2MR55W-3 | D2 D3 D4 D5 D6 D7 | 0.54 | 5.40 |
| 10 | [1497-1405-1-ND](https://www.digikey.com/en/products/result?keywords=XZM2CRK55W-3) | SunLED XZM2CRK55W-3 | D8 D9 D10 D11 D12 D13 | 0.326 | 3.26 |
| 1 | [S1011EC-40-ND](https://www.digikey.com/en/products/detail/PRPC040SAAN-RC/S1011EC-40-ND/2775214) | Sullins PRPC040SAAN-RC | H1 | 1.23 | 1.23 |
| 3 | [469-1004-ND](https://www.digikey.com/en/products/result?keywords=469-1004-ND) | Radial Magnets 8193 | (off-board) | 0.4 | 1.20 |
| 8 | [469-1005-ND](https://www.digikey.com/en/products/result?keywords=469-1005-ND) | Radial Magnets 8195 | (off-board) | 0.19 | 1.52 |
| | | | | **Total** | **26.44** |

## 3. LCSC

Upload [`lcsc_cart.csv`](lcsc_cart.csv) with LCSC's BOM tool and map the columns (Quantity, LCSC Part Number). The quantities already respect LCSC's minimum order per line.

| Qty | Part number | Manufacturer, MPN | For | Unit $ | Line $ |
|---|---|---|---|---|---|
| 100 | [C23186](https://www.lcsc.com/product-detail/C23186.html) | UNI-ROYAL 0603WAF5101T5E | R1 R2 | 0.0026 | 0.26 |
| 5 | [C202311](https://www.lcsc.com/product-detail/C202311.html) | Texas Instruments BQ21040DBVR | U2 | 0.3303 | 1.65 |
| 100 | [C4190](https://www.lcsc.com/product-detail/C4190.html) | UNI-ROYAL 0603WAF2201T5E | R3 | 0.0041 | 0.41 |
| 100 | [C98220](https://www.lcsc.com/product-detail/C98220.html) | Yageo RC0603FR-0710KL | R4 R8 | 0.0034 | 0.34 |
| 50 | [C29936](https://www.lcsc.com/product-detail/C29936.html) | Samsung CL10B105KA8NNNC | C1 C2 C4 | 0.0225 | 1.12 |
| 100 | [C14675](https://www.lcsc.com/product-detail/C14675.html) | Yageo RC0603FR-07100KL | R5 R6 R7 R10 R11 R12 | 0.0047 | 0.47 |
| 100 | [C1591](https://www.lcsc.com/product-detail/C1591.html) | Samsung CL10B104KB8NNNC | C3 | 0.016 | 1.60 |
| 5 | [C722171](https://www.lcsc.com/product-detail/C722171.html) | Omron (Aratas) B3F-1020 | SW1 | 0.1523 | 0.76 |
| 10 | [C13564](https://www.lcsc.com/product-detail/C13564.html) | Murata NCP18XH103F03RB | RT1 | 0.0467 | 0.47 |
| 5 | [C71045](https://www.lcsc.com/product-detail/C71045.html) | Texas Instruments TPS61169DCKR | U3 | 0.3268 | 1.63 |
| 10 | [C83442](https://www.lcsc.com/product-detail/C83442.html) | Sunlord SWPA4018S100MT | L1 | 0.0594 | 0.59 |
| 10 | [C21353](https://www.lcsc.com/product-detail/C21353.html) | onsemi MBR0540T1G | D1 | 0.061 | 0.61 |
| 10 | [C1848](https://www.lcsc.com/product-detail/C1848.html) | Samsung CL31B105KBHNNNE | C5 C6 | 0.0492 | 0.49 |
| 5 | [C84416](https://www.lcsc.com/product-detail/C84416.html) | Murata GRM21BR61E106KA73L | C7 | 0.1764 | 0.88 |
| 100 | [C137674](https://www.lcsc.com/product-detail/C137674.html) | Yageo RC0603FR-078R2L | R9 | 0.0054 | 0.54 |
| 5 | [C20917](https://www.lcsc.com/product-detail/C20917.html) | Alpha & Omega AO3400A | Q1 Q2 | 0.0898 | 0.45 |
| 20 | [C125095](https://www.lcsc.com/product-detail/C125095.html) | Lite-On LTST-C190KSKT | D14 D15 D16 D17 D18 | 0.0248 | 0.50 |
| 100 | [C22548](https://www.lcsc.com/product-detail/C22548.html) | Yageo RC0603FR-071KL | R13 R14 R15 R16 R17 | 0.0058 | 0.58 |
| | | | | **Total** | **13.35** |

## 4. Adafruit

Adafruit has no list upload: add the three products from their pages ([`adafruit_list.csv`](adafruit_list.csv) has the links).

| Qty | Part number | Manufacturer, MPN | For | Unit $ | Line $ |
|---|---|---|---|---|---|
| 1 | [2001](https://www.adafruit.com/product/2001) | Adafruit 2001 | (off-board) | 0.75 | 0.75 |
| 1 | [2003](https://www.adafruit.com/product/2003) | Adafruit 2003 | (off-board) | 0.75 | 0.75 |
| 1 | [5019](https://www.adafruit.com/product/5019) | Adafruit 5019 | (off-board) | 0.75 | 0.75 |
| | | | | **Total** | **2.25** |

## 5. Tool

- UPDI programmer (USB-C, 3 V / 5 V): Adafruit (UPDI Friend) 5879, [Digi-Key 1528-5879-ND (NV)](https://www.digikey.com/en/products/detail/adafruit-industries-llc/5879/22596413), $6.95. Set it to 5 V logic and wire only UPDI and GND (firmware notes, §4).

## 6. Before you pay

- Open every line on the live page: prices and stock here are from snippets.
- The cell cannot ship by air from Digi-Key (Li-ion): choose ground shipping.
- If LCSC is out of the B3F-1020 switch (one cached page said so), order the BOM's alternate, Digi-Key SW402-ND.
- The foam tape is listed as both 1.0 mm and 1.6 mm thick: measure it before relying on the cell height.
- PCB thickness 1.0 mm, and the USB-C edge clearance (§1).
- The two magnet sizes are easy to mix up: 8193 is 1/8″ thick (horn dowels), 8195 is 1/16″.
- Keep the two LED reels apart when they arrive (660 nm XZM2MR55W-3, 625 nm XZM2CRK55W-3): they look alike, and the build guide places them by reel.

