# Gate 1 — Concept

> **Personal prototype for bench evaluation. Not a cleared medical device.**
> Not for diagnosis, treatment or clinical use. Every number below is an engineering
> estimate for sizing the concept, not a safety case.

The one-page board is [`concept.pdf`](concept.pdf) (A3, built from `concept.html`).
This note carries the evidence behind it.

## 1. Summary

A palm-sized stone with a crescent window at its nose. Twelve red LEDs (6 × 660 nm,
6 × 620 nm) sit in black pockets just outside the window. They push light into the
skin under a narrow lip, and the light glows back out through the skin inside the
window, with veins as dark lines.

**Option A, "Pebble"** is chosen. It is one convex G2 dome with the crescent bored
through its nose, 90.4 × 58.9 × 25.4 mm. A planar waterline splits a warm-grey PETG top
from a black, light-tight optical sole. Behind the window it carries:
- a finger-dimple button and a hairline status seam;
- a 600 mAh protected cell lying across the crown, directly on the sole inside a PCB cut-out;
- USB-C on the waterline at the tail.

## 2. How it works (and why these choices)

* **Side transillumination, not reflection.** The skin under the window is never lit from
  above. Light enters 2–3 mm outside the window rim, below a black lip pressed on the
  skin. It then random-walks through the dermis (mean step ≈ 0.5 mm) and some of it leaves
  through the window. Deoxygenated blood absorbs it, so a vein casts a soft shadow from
  below. Room light falling on the window is the enemy: it adds a uniform veil. Hence
  the concave, light-tight black sole and a window that sits in a shallow well.
* **Two wavelengths, visible only.**
  * 660 nm: melanin absorbs ~20% less here than at 620 nm, and it reaches deeper. It
    looks dim to the eye (V(660) ≈ 0.06). Its current is still capped by skin heating,
    and lower than 620 nm's because it makes more light per mA. So the 660 bank benefits
    most from a dimmed room.
  * 620 nm: about 5× brighter per watt to the eye (V ≈ 0.38). Best for superficial
    veins on lighter skin.

  Only one bank is lit at a time.
* **The skin is the display.** No camera, no screen and no app means nothing to calibrate
  or charge except the cell, and nothing to look at except the skin.

## 3. Form exploration

### 3.1 How the form is made (G2 by construction)
OpenCascade fillets are circular blends, so they are only G1. Instead, the whole outer
skin is **one periodic cubic B-spline surface**, C2 and therefore G2 by construction,
including across the u-seam.

Measured on option A, the curvature jump across the seam is 1.4·10⁻⁷ mm⁻¹.

**Known gap, the first task at the CAD gate.** The surface's two parametric poles (crown
and underside centre) are only G1 today:
- Near the crown pole the principal curvature spreads by ±0.02 mm⁻¹ within ~2 mm, and by
  ±0.09 mm⁻¹ within ~0.3 mm. This is far below FDM resolution and invisible in the
  renders, but zebra stripes would show it.
- Cause: the piecewise-linear disk map and FEM fields feed noise into the fit exactly
  where the parametrisation is densest.
- Fix: set the first two control rows at each pole from a least-squares osculating
  paraboloid. This makes the pole G2 to fit accuracy, which is then re-checked with the
  same ring test and zebra renders.

`cad/stone/organic.py` builds it in five steps:
1. The planform is a smooth C-shape (2D SDF, C2 smooth-min/max).
2. That planform is meshed and mapped bijectively to a disk (Floater mean-value map).
3. The top is inflated with the torsion function Δτ = −1.
4. The underside tucks under with a roll whose edge curvature is **derived from the top
   at every silhouette point**, so top and bottom form one C2 curve through the
   silhouette.
5. A least-squares fit (max deviation ≤ 0.12 mm) produces the B-spline, which becomes an
   OCC face, then a shell, then a valid solid.

Concept STEP: `A_pebble_outer.step`.

### 3.2 The three options (same window, gap, waterline, sole, envelope)
| | A — Pebble | B — Crescent | C — Hagstone |
|---|---|---|---|
| Idea | one convex dome, crescent bored through its nose | teardrop; crown on the window rim; tapered horns | flat lens; worn crater dishes into the window |
| Size (mm) | 90.4 × 58.9 × 25.4 | 90.5 × 58.9 × 25.0 | 89.2 × 60.0 × 23.0 |
| 600 mAh cell (30.5 × 42 × 5.4) | **fits**, 1.9 mm margin | no: the tail is too narrow | no: crater too low |
| Switch under the button | **fits**, 0.6 mm | fits, 1.8 mm | no: −4.4 mm |
| Support-free cosmetic print¹ | yes (top: no facet > 45°; sole: 39° max) | yes | yes |
| Reads as one stone (renders) | yes: convex everywhere | yes, most sculptural | yes; window dominates |
| Room light into the window | low (rim well) | low | higher (open funnel) |
| Precision grip | tall mid-flanks, index behind window | tall front, thin tail | low flanks |

¹ Overhang measured on every tessellated outer facet in print orientation. The top shell
prints waterline-down; the sole prints inverted, also waterline-down. "No facet > 45°"
means the total area beyond 45° is < 0.05 mm² (one sliver at a horn tip).

Renders: `renders/{A,B,C}_{hero,side,plan}.jpg`. Option A also has `A_hero_seam`,
`A_detail`, `A_underside`, `A_rear` and `A_context` (on a forearm, window glowing).

### 3.3 Iteration log (what the renders taught)
1. **First pass: the horns read as tubes.** The τ-inflation alone made thin horns low
   and round, like a neck pillow. *Cause:* thin regions inflate less.
2. **Edge matching.** The bottom tuck had to match the top's edge curvature (exact G2),
   but the natural match was absurd in places: a 32 mm tuck on the horn flanks and a
   0.8 mm cliff at the window back. *Fix:* derive the tuck, clamp it smoothly, and
   rebalance the top locally.
3. **Body + arms read.** Low horns joined to a tall body through a concave saddle.
   *Fix:* a single convex ellipsoidal dome per option. Pebbles are convex.
4. **Crease at the horn tips.** It came from a hard clip in the dome field (u² > 1).
   *Fix:* a C∞ soft-positive function, plus a floor on the thickness compensation.
5. **Packaging closed the loop.** At 24 mm the cell missed by 1 mm. It now lies across
   the crown, on the sole inside a PCB ring; the stone is 25.4 mm and the tail fuller.

## 4. Chosen form A — packaging
* **Stack (z from the skin-contact rails).**
  * Black sole up to the **waterline at z = 4.2 mm**.
  * The PCB (1.0 mm FR4, black mask) lies on the sole.
  * The cell lies on a 0.4 mm foam pad in a PCB cut-out: x 24.3–54.8 mm, across the body.
* **LED ring.** 12 LEDs on the PCB underside, entry radius ≈ 17.5 mm, alternating banks.
  Each sits in a short black pocket; a 1.5–2.5 mm lip separates it from the window.
* **Button.** 6 × 6 mm tactile switch with a 7.3 mm actuator at x = 21 mm, under the
  0.5 mm-deep finger dimple. The dimple is a 0.8 mm flexing membrane. Clearance is checked
  over the whole plunger, not only its centre.
* **Status seam.** A hairline arc on the window's back-rim slope (r ≈ 18.6 mm, ±44°),
  over the PCB ring. The status LED lights it from inside through a black light mask.
* **USB-C.** On the waterline at the tail, on the PCB's tail bridge.
* **Closure.** 4 N52 magnet pairs (positions indicative) and 3 printed PETG clips.

**Mass estimate**:
- top shell 16 g (outer area × 1.8 mm), plus internal ribs and bosses 3–5 g
- sole 10 g
- cell 12.1 g
- PCB 3.5 g
- parts 3 g
- magnets 4.8 g
- clips, foam and wire 2.5 g

**Total ≈ 55 g** (limit 80 g).

## 5. Preliminary engineering budgets
Source: `calc/concept_budget.py`. Notes and equations: `calc/PHYSICS_NOTES.md`.
Pinning tests: `calc/test_concept_budget.py` (11 pass).

### 5.1 Per-LED data (distributor and datasheet snapshots)
| LED | ref point | optical | wall-plug eff. | eye weight K |
|---|---|---|---|---|
| Lumileds L1SP-DRD0002800000, 660 nm | 120 mA, 2.08 V | 149 mW (0.82 µmol/s) | 0.60 | 46 lm/W |
| Lumileds L128-RNG1003500000, ~620 nm | 120 mA, 2.10 V | 110 mW (27 lm) | 0.44 | 246 lm/W |

### 5.2 What limits brightness: skin heating
Each pocket's absorbed light heats a ~2 mm hemisphere of skin: ΔT = 3P/(4πka).

The budget is 41 °C limit − 33.5 °C skin − 1.5 K device conduction = **6 K**. That allows
each LED (6 per bank, one bank lit):

| bank | light skin | medium | dark skin |
|---|---|---|---|
| 660 nm | 42 mA (52 mW) | 31 mA | 23 mA |
| 620 nm | 50 mA (45 mW) | 38 mA | 30 mA |

These currents are 8–17% of the LEDs' ratings, so the parts run cool and efficient. Dark
skin gets the lowest cap because melanin absorbs right at the surface. That is physics,
not a design flaw. The firmware will cap current per bank, and an NTC will sit beside the
hottest LED.

### 5.3 Battery and runtime
Each bank draws 0.34–0.73 W from the cell (boost driver at 85% efficiency, plus 20 mW
overhead). With 600 mAh × 3.7 V × 90% usable, that gives **2.7–5.8 h at full brightness**.
The brief requires ≥ 45 min.

The 850 and 1000 mAh pouches do not fit any of the three forms, and are not needed.

### 5.4 What the eye will see: the window is rim-lit
Light diffuses through skin and falls by about e every 2.5 mm (μeff ≈ 0.4 /mm, literature
range 0.24–0.65). Results at the heat-limited current, with LEDs at r = 17.5 mm:

* **Rim.** A bright band 6–8 mm wide, 5–30× brighter than room light reflected from the
  half-shaded window (500 lx).
* **Centre.** 0.02–0.04× the ambient. Effectively dark in a lit room.

Moving the LED entry from r = 20 to 17.5 mm makes the rim about 5× brighter. Tilting the
LEDs would barely change it. See `figures/fig_window_profile.png`.

### 5.5 IEC 62471 (preliminary)
Worst case is a bare LED at its full rated current, die area assumed 0.3 mm², viewed from
200 mm. The die then subtends 3.1 mrad, so it counts as a *small source*.

* **Retinal thermal:** 3.6–4.4% of the exempt limit (28 000/α).
* **Blue light:** B(λ) = 0.001 above 600 nm. Assessed as small-source irradiance, it is
  25–30% of the exempt limit (E_B ≤ 0.01 W/m²) per LED at full rating. All six LEDs of a
  bank together stay well under the limit at the planned ≤ 50 mA cap, about ⅙ of rating.
* **Other hazards:** no UV, no IR.

Expected **Exempt group**. The limits were taken from secondary sources that reproduce
IEC 62471 Table 6. The formal calculation against the standard's tables, including
whole-lamp and field-of-view rules, comes at the verification gate.

## 6. Requirements that conflict with physics, cost or printing
| Brief | Problem | Smallest change (proposed) |
|---|---|---|
| LEDs angled 30–45° down and inward | A single flat crescent PCB cannot tilt SMD LEDs. In skin, light loses its direction within ~1/μs′ ≈ 0.5 mm, so tilt shifts the effective source by < 1 mm. | Mount the LEDs flat, facing the skin, in short black pockets right behind a narrow lip. Pull the entry ring in to r ≈ 17.5 mm. Same intent (light enters under the lip, heading inward), 5× more rim light than tilting at r = 20. |
| 30 mm window | Side transillumination lights only a 6–8 mm band inside the rim; the centre is dim under room light. | Keep 30 mm: the needle needs room. Use: put the vein near a side rim, or dim the room. The window radius is one CAD parameter; a 24 mm variant (LED ring moved in with it) makes the centre 5–7× brighter (model: 5.0× at 660 nm, 6.6× at 620 nm). |
| ≥ 45 min at full brightness; 600–1000 mAh | Brightness is capped by skin heating, not energy. 45 min needs only ~60 mAh. 850–1000 mAh pouches don't fit under a 25 mm stone. | Use the 600 mAh protected cell (2.7–5.8 h). |
| Walls ≥ 1.6 mm | A glow-through seam and a flexing button both need thin PETG. | Two deliberate local zones of 0.6–0.8 mm, backed by internal ribs. Every other wall is ≥ 1.8 mm. |
| Snap-fit closure + cosmetic surfaces printed without supports | With no flat outer faces, both halves must print waterline-down, so no hook can cross the waterline. | Three small PETG clips printed flat, in their strongest layer direction, pressed into slots in both halves. Four magnet pairs give pull-in and alignment. No visible screws. |
| ~26 mm height | The cell plus switch stack needs 25.4 mm. A lower stone looked better but missed the cell by 1 mm. | 25.4 mm. |
| Underside concave to seal against a forearm | A forearm is R ≈ 35–50 mm, but the back of the hand and the antecubital fossa are flat. One radius cannot fit all. | R = 120 mm across, with rails 44 mm apart. It seals on a slim forearm under light pressure. The radius is a parameter for bench tuning. |
| G2 everywhere, no hard edges | The USB-C opening and the waterline must be edges. | These are the only two. The port gets a small round. |

## 7. Assumptions
* Light warm-grey PETG for the top and black PETG for the sole (two spools on hand; only
  the ~55 g used is costed).
* Exam-room light is 500 lx. Skin and tissue optical parameters are literature ranges, not
  measurements.
* The creator orders from the US, mostly from Digi-Key. The PCB comes from JLCPCB: it is
  fabricated, not a stocked part, so it falls outside the four-distributor rule.
* The 1.0 mm PCB is 2-layer FR4 with black mask.
* The K2 Pro prints PETG at 0.2 mm layers (0.08–0.12 mm adaptive on the shallow crown).
* Snap clips and magnet positions are indicative until the CAD gate.

## 8. Preliminary parts and cost (to be re-verified at the electronics gate)

> **Superseded at gate 3** by [the verified BOM](../03-electronics/bom.md). Corrections to this table:
> - The TPS61169DCKR is on **backorder** at Digi-Key; it is ordered from LCSC.
> - The LEDs are 1206 parts, because the 2.0 mm ring budget rules out the 2835 parts listed here.
> - The magnets are N35, the only grade stocked in these sizes.
Direct access to digikey.com, mouser.com, lcsc.com and adafruit.com is blocked in this
environment. Every price below comes from **search-indexed listings and may be stale**.

Confidence key:
- **D:** seen on the distributor's own listing
- **M:** manufacturer data
- **?:** not verified

| item | part | source | qty | unit $ | ext $ | conf |
|---|---|---|---|---|---|---|
| deep-red LED 660 nm | Lumileds L1SP-DRD0002800000 | Mouser 997-L1SPDRD0002800 | 6 | 0.70 | 4.20 | D |
| red-orange LED | Lumileds L128-RNG1003500000 | Digi-Key | 6 | 0.57 | 3.42 | D |
| LiPo 600 mAh, protected | Jauch LP503040JH (5.4 × 30.5 × 42) | Digi-Key | 1 | 10.81 | 10.81 | D (old snapshot) |
| LED boost CC driver | TI TPS61169DCKR | Digi-Key 296-40821-1-ND | 1 | 1.34 | 1.34 | D |
| Li-ion charger | Microchip MCP73831T-2ACI/OT | Digi-Key | 1 | 0.76 | 0.76 | D |
| MCU | Microchip ATtiny1616-SNR | Digi-Key | 1 | 1.16 | 1.16 | D |
| USB-C receptacle | GCT USB4105-GF-A | Digi-Key 2073-USB4105-GF-ACT-ND | 1 | 0.80 | 0.80 | D |
| tactile switch 6×6, ~7.3 mm | to select | Digi-Key / LCSC | 1 | ~0.30 | 0.30 | ? |
| N52 magnets 6.35 × 2.54 | Radial Magnets 9150 | Digi-Key 469-9150-ND | 8 | 0.35 | 2.80 | D (stock not seen) |
| passives, 2 MOSFETs, Schottky, inductor, NTC, status LED, ESD | various | Digi-Key | — | — | ~4.50 | ? |
| PCB, 5 pcs | JLCPCB 2-layer, black mask | JLCPCB | 1 | ~2 | ~2 | M |
| PCB shipping to US | — | JLCPCB | 1 | — | 15–20 | 3P |
| PETG used (~55 g) | eSUN PETG | Digi-Key ($21.09/kg) | — | — | ~1.20 | D |
| distributor shipping | Digi-Key, plus Mouser for the 660 nm LED if needed | — | — | — | 8–16 | ? |
| **total** | | | | | **≈ $56–70** | |

## 9. Decisions (answered at the concept review, 2026-10-11)
| # | Question | Answer |
|---|---|---|
| 1 | Form | **A "Pebble"** as shown. |
| 2 | LED mounting | **Flat LEDs in lipped black pockets** near r ≈ 17.5 mm, not tilted. |
| 3 | Window | **30 mm**, as briefed. |
| 4 | Battery | **600 mAh Jauch LP503040JH** (protected). |
| 5 | Colours | **Warm light-grey top, black sole.** |
| 6 | Thin walls | **Allowed in two spots only:** the light seam and the button skin, with ribs or a frame behind them. Every other wall ≥ 1.8 mm. |
| 7 | Closure | **Magnets only (four pairs), no clips.** This differs from the clip + magnet proposal in §6. The magnets also act as dowels: each sole magnet stands proud through a hole in the PCB into a socket in the top, which aligns the halves and clamps the board. |
| 8 | Parts check | The owner will allow `digikey.com`, `mouser.com`, `lcsc.com` and `adafruit.com` in the environment's network settings. On 2026-10-11 they still returned 403 from this session, so they are re-checked at the electronics gate. |

Changes made at the CAD gate as a consequence are listed in `docs/02-cad/cad.md`.

## 10. Reproduce
```bash
pip install build123d scipy triangle shapely scikit-image matplotlib mitsuba playwright pytest
cd cad/concepts && python build_concept.py A          # fit + STEP + quick review renders
python feasibility.py                                 # print/packaging checks -> build/concepts/feasibility.json
cd ../../calc && python -m pytest -q && python concept_budget.py
cd ../render && python concept_renders.py             # board renders (Mitsuba, ~15 min on 4 cores)
cd ../docs/01-concept && python figures.py && python build_pdf.py
```
