# Print packet: the four printed parts

> **Personal prototype for bench evaluation. Not a cleared medical device.**
> Not for diagnosis, treatment or clinical use.

Slicer settings, what to check in the slicer preview, and first-article checks with
calipers for the four printed parts.

**Sources:**
- Settings: [build §1](../05-build/build.md#1-print) and [cad.md §6](../02-cad/cad.md).
- Dimensions:
  - `cad/device/params.py`;
  - the part code in `cad/device/parts.py`;
  - the CAD checks in `docs/02-cad/checks.json`.
- Overall sizes are measured on the print meshes by
  [`print_dims.py`](print_dims.py), which writes [`print_dims.json`](print_dims.json).

## Which parts, in what order

| Order | Part | File | Filament | Needed for a working unit? |
|---|---|---|---|---|
| 1 | Sole | `docs/02-cad/3mf/sole.3mf` | black PETG | **Yes.** It holds the board, carries the 12 LED light channels and the NTC's 0.70 mm sensor window, forms the skin face, and holds the USB-C lip that N19 is about. |
| 2 | Top shell | `docs/02-cad/3mf/top_shell.3mf` | warm grey PETG | **Yes.** It closes the stone, carries the 0.40 mm button skin, and holds the top magnets. |
| 3 | Bridge | `docs/02-cad/3mf/bridge.3mf` | black PETG | **Yes.** It holds the tact switch under the button skin. Without it the closed stone has no button. |
| 4 | Seam mask | `docs/02-cad/3mf/seam_mask.3mf` | black PETG | **No.** Its only job is to carry the five amber status LEDs' light to the seam slot (cad.md §4). The unit lights, switches, charges and protects itself without it. |

**If you leave the mask out at first:**
- Leave out its two posts too (build §4.2). They only hold the mask.
- Judge the seam patterns and light leaks only once it is fitted: checklist 3.5 (item 9) and
  the seam's visibility (M15) assume it is in place.

**Filament:** about 16 g grey and 13 g black, plus supports (cad.md §6). Masses in
`checks.json`: sole 10.57 g, top shell 15.94 g, bridge 1.56 g, mask 0.34 g.

## 1. Slicer settings

Printer: Creality K2 Pro, 0.4 mm nozzle, PETG. The 3MF files are already in print
orientation, each sitting on z = 0 (`cad/device/build.py`, `export_3mf`).

| | Sole | Top shell | Bridge | Seam mask |
|---|---|---|---|---|
| Orientation | turned over, waterline face down | waterline face down | on its side (+x face down) | base (board face) down |
| Layer height | 0.16 mm | adaptive 0.08–0.16 mm, or a fixed 0.12 | 0.2 mm | 0.12 mm |
| Walls | 4 | 5 lines (solid 1.8 mm wall) | 3 | 2 (0.8 mm fences) |
| Infill | 30 % gyroid | 100 % (all wall) | 40 % gyroid | — |
| Top / bottom layers | 6 / 4 | 6 / 4 | 4 / 4 | 4 / 3 |
| Supports | none | **tree, build plate only**, for the interior | none | none |
| Support Z gap | — | 0.2 mm, 2 interface layers (cad.md §6) | — | — |
| Brim | none | 3 mm | none | 5 mm |

**Settings for all parts:**
- **Temperatures:** nozzle 235–245 °C, bed 75–80 °C, part fan 30–50 %, bridges 100 %.
  Leave the chamber lid open.
- **Plate:** textured PEI; on smooth PEI, glue stick as a release agent.
- **Elephant-foot / first-layer compensation:** 0.10–0.15 mm. Both waterline faces must be
  flat.
- **"Detect thin walls":** on.

## 2. Preview inspection (before printing)

Layer counts below are the documented thickness divided by the layer height in §1.

### Sole
- [ ] **No supports anywhere.** The sole's skin has no overhang (checks.json
  `overhang_sole`: 0.01 mm², a tessellation speck). The interior roofs are short bridges.
- [ ] **USB-C lip (N19).** Upside down, the opening is a notch at the plate, 0.855 mm tall
  (`print_dims.json`, `usb_opening_below_waterline`). The lip is the bridge over it.
  - On the print mesh it is 0.95 mm thick 1 mm in from the landing face, 0.91 mm at
    0.2 mm in, and 0.87 mm at the face itself (`print_dims.json`,
    `usb_lip_from_landing_face`).
  - checks.json's 0.91 mm is its probe's minimum, which stops 0.15 mm short of the face
    (`cad/device/checks.py`).
  - Count the solid layers over the notch in the layer view. **Write the count and
    count × 0.16 mm in the notes of P-S10.**
- [ ] **NTC sensor window.** The pocket's roof is a short bridge (1.25 mm span), then solid
  top layers to the skin face.
  - 0.70 mm = 4.4 layers at 0.16 mm.
  - No gap or sparse infill may show over the pocket.
- [ ] **LED channels:** 12 open rectangles through the whole height (2.20 × 4.70 mm,
  `parts.py`). Nothing inside them.
- [ ] **Magnet and post pockets:** bridged roofs over the 4 magnet pockets (Ø 6.50) and
  the 6 post reliefs (Ø 2.6).

### Top shell
- [ ] **Supports:**
  - tree supports from the build plate only, inside the cavity: the ceiling, and the
    undersides of the 4 magnet bosses (1.05 mm above the plate);
  - none on the outer skin (max overhang 21.0°, checks.json);
  - none in the seam groove.
- [ ] **Button skin, 0.40 mm** (top of the thumb dish). At 0.08 mm adaptive that is 5
  layers; at 0.12 mm about 3. cad.md §6 expects 2–5 on the shallow crown. The layer view
  must show solid layers across the whole dish: no holes, no infill.
- [ ] **Seam wall, 0.68 mm normal** (verification §2; params.py SEAM_WALL = 0.7).
  - The seam is a groove cut from the inside (`parts.py` `top_shell()`); the outer skin
    stays closed.
  - With "detect thin walls" on, the wall left over the groove prints solid, with no gap.
- [ ] **Magnet counterbores** (Ø 6.60 horns) and top pockets (Ø 6.50): open, no support
  inside.

### Bridge
- [ ] Prints on its side with no supports (one constant 8.4 mm width, cad.md §5.3).
- [ ] The 4 post holes (Ø 1.05) and 4 switch-leg holes (Ø 1.2) lie horizontal in this
  orientation. They will print slightly small; ream them after printing (§3).

### Seam mask
- [ ] Two perimeters fill each 0.8 mm fence, with no gap between them.
- [ ] The two ear post holes (Ø 1.05, 1.6 deep) are open.

## 3. After printing

- Clip the shell's interior tree supports out through the open waterline face.
  - Keep tools away from the button skin and the seam groove.
  - **Clean the 4 boss undersides flat.** They sit 0.05 mm above the board (params.py
    BOSS_PCB_GAP), so a support scar can hold the halves apart.
- Ream any post hole that a header post does not slide into, with a 1.0 mm drill bit by
  hand (build §1).
- Check that the sole's 12 LED channels and the USB-C opening are clear.

## 4. First-article checks

**How the limits are set.** `params.py` gives no print tolerances. It gives the clearance
each fit is designed with. Each limit below is where that clearance is used up: past it,
the parts no longer fit as designed. Where no clearance applies, the line says
**record**: there is no documented limit.

**When:**
- Most checks need only the prints. Do them before build day.
- **S5, T2, T3 and B2** need the bare board, the tape and the cell: do them at build-day
  2.0.
- **M4** needs the populated board: do it at build-day 4.4.

Write each value in the bench data sheet, section P.

### Sole

| # | Check | How | Nominal | Limit | Source |
|---|---|---|---|---|---|
| S1 | Overall size, print orientation (L × W × H) | outside jaws | 89.92 × 58.66 × 4.18 mm | record | `print_dims.json` |
| S2 | Each magnet pocket takes a magnet | push a dry magnet in | Ø 6.50 | **goes in** (Ø ≥ 6.35) | params.py MAG_D + MAG_POCKET_CLEAR |
| S3 | Magnet top above the waterline face, seated dry | depth rod | horns 1.95, tails 1.10 | **below 2.20 / 1.35**, where it would touch a top magnet seated in its pocket | parts.py `sole()` and `top_shell()` both cut the pockets 0.05 mm deeper than the magnet's place in the CAD (no reason given); params.py MAGNETS, MAG_GAP; `print_dims.json` |
| S4 | Magnet centre distances (magnets in, dry): measure across two magnets' outer edges and subtract 6.35 | outside jaws | horn pair 40.00; tail pair 24.00; horn to tail on the same side 69.06 | **± 0.25 mm** | params.py MAGNETS (−12, ±20), (56.6, ±12). Per magnet, the board's horn hole allows (6.75 − 6.35) / 2 = 0.20, less the pocket's own 0.075 play: 0.125 each, 0.25 for a pair. The tail magnets sit in edge notches (order.md §1), so the limit is conservative there |
| S5 | Bare PCB over the four dry magnets (build-day 2.0) | lay it on | — | **drops over all four without force** | layout.json `pcb_holes` = magnet positions; MAG_PCB_HOLE 6.75 |
| S6 | LED channels take an LED body | push a spare LED of each type into its channels from the waterline face | 2.20 × 4.70 | **body enters** (max body 1.8 mm wide) | params.py LED_PKG + LED_TOL; parts.py `sole()` |
| S7 | NTC pocket depth | depth rod | 1.10 | **≥ 0.95** (NTC max height), or the NTC holds the board up | params.py NTC_PKG; parts.py `sole()` |
| S8 | Sole thickness at the NTC pocket (θ = 0, r = 20.4), reaching in from the window bore. **Window = S8 − S7** | outside jaws | 1.80 (window 0.70) | window: record; a hole means reprint (checklist 1.6) | checks.json "ntc (sensor window)" 0.7 |
| S9 | USB-C opening width **at the sole's waterline face** (the sole holds only the opening's lower 0.855 mm) | inside jaws | 8.87 | **≥ 8.26** (the receptacle shell's width at that height) | params.py USB_W, USB_H, USB_CLEAR; layout.json usb z_c; `print_dims.json` (stadium widths 0.98 mm below centre) |
| S10 | **USB-C lip under the opening (N19), at least 0.2 mm in from the landing face**: one jaw on the floor of the opening's notch, one on the skin below | outside jaws | 0.91–0.95 there (0.87 at the face itself) | record. N19 is accepted provisionally; item 20 judges the lip as printed | `print_dims.json` `usb_lip_from_landing_face`; readiness N19 |
| S11 | Waterline face flat | on glass or a flat stone | — | record any rocking or gap | build §1 |

### Top shell

| # | Check | How | Nominal | Limit | Source |
|---|---|---|---|---|---|
| T1 | Overall size, print orientation | outside jaws | 90.17 × 58.86 × 20.50 mm | record | `print_dims.json` |
| T2 | Boss undersides below the waterline face (4; build-day 2.0) | depth rod | 1.05 | **≥ the measured board thickness** (A-2.1a). Otherwise the bosses hold the halves apart by the difference | params.py PCB_T + BOSS_PCB_GAP ("boards are 1.0 ± 0.1") |
| T3 | Bare PCB in the shell's waterline opening, shell upside down (build-day 2.0) | lay it in; straightedge across | 0.3 mm clearance all round | **no wall contact; board face at or below the waterline face** | params.py PCB_CLEAR, BOSS_PCB_GAP |
| T4 | Horn counterbores take a magnet | push a magnet in | Ø 6.60 | **goes in** | params.py MAG_D + MAG_DOWEL_CLEAR |
| T5 | Top magnet pockets take a magnet | push a magnet in | Ø 6.50 | **goes in** | params.py MAG_D + MAG_POCKET_CLEAR |
| T6 | USB-C opening width at its widest, 0.98 mm above the waterline face | inside jaws | 9.44 | **≥ 8.94** (receptacle shell) | params.py USB_W + 2 × USB_CLEAR; `print_dims.json` |
| T7 | Button skin, and the seam's thin wall over its groove | hold against a bright light | — | **both glow evenly, with no pinholes** | checklist 1.6; parts.py `top_shell()` |

### Bridge

| # | Check | How | Nominal | Limit | Source |
|---|---|---|---|---|---|
| B1 | Pedestal top above the feet | outside jaws | 12.01 | record; B3 decides | `print_dims.json` (size along x) |
| B2 | Deck underside above the feet (build-day 2.0) | depth rod | 7.40 | **≥ the measured tape + cell** (A-2.1f), or the deck touches the cell | params.py BATT_FOAM + BATT_T + BATT_TOP_CLEAR |
| B3 | **Switch height when seated:** feet to the actuator top, legs through the holes, not soldered | outside jaws | 17.01 if the switch sits on the pedestal top (the CAD's stand-in); **16.41 if it sits down in the 0.60 mm seat pocket** | **≤ 17.06** (membrane underside, zero gap). Shim stack ≈ 17.06 − B3 (§5) | parts.py `bridge()` seat 6.3 × 6.3 × 0.6; params.py SWITCH_H 5.0, SWITCH_GAP 0.05; cad.md §4 (pedestal top z 17.19, skin underside z 22.24) less the board top (layout.json z_part + pcb_t = 5.18) |
| B4 | Leg span | outside jaws | 50.00 | record | params.py BRIDGE_LEG_Y, BRIDGE_LEG |
| B5 | Posts slide into the 4 leg holes | header post | Ø 1.05 hole; 0.905 post diagonal | **snug slip fit**; ream with a 1.0 mm bit if tight | params.py PIN_HOLE_PART, PIN_SQ; build §1 |

### Seam mask (printed last)

| # | Check | How | Nominal | Limit | Source |
|---|---|---|---|---|---|
| M1 | Highest point above the base | outside jaws | 6.61 | **≤ 6.77**, or the shell presses it | params.py MASK_GAP is 0.10 mm normal to the shell. On the mask's top, which slopes at 53–77°, that leaves at least 0.10 / cos 53° = 0.165 mm vertically (`print_dims.json`) |
| M2 | Ear height | outside jaws | 3.00 | record | params.py MASK_EAR |
| M3 | Posts slide into the two ear holes | header post | Ø 1.05 | snug slip fit; ream if tight | params.py PIN_HOLE_PART; build §1 |
| M4 | Fits over the five amber LEDs on the populated board (build-day 4.4) | lay it on | channel 1.30 | **no LED touched** (their lands are 0.95 wide) | params.py MASK_CHANNEL; electronics §3 item 7 |

## 5. The bridge's switch seat (N23): check this before the shim step

**The finding.**
- `parts.py` cuts a 6.3 × 6.3 mm seat 0.60 mm deep into the bridge pedestal for the 6.0 mm
  switch body.
- The CAD's switch stand-in sits on the pedestal top. So do the 0.05 mm gap in `params.py`,
  the button-force model in `checks.json` ("gap 0.05 + travel 0.25 mm") and cad.md §4.
- The committed print mesh has it: `bridge.3mf` shows a 6.3 × 6.3 mm floor at 11.41 mm
  above the feet, 0.60 mm below the 12.01 mm pedestal top.

**The consequence.** If the body drops into the seat, the dish moves 0.60 + 0.05 =
**0.65 mm** before it meets the actuator, not 0.05 mm. The click then comes after the
switch's 0.25 mm travel, at about **0.90 mm** instead of the 0.30 mm that build §4.4 asks
for.
- Unshimmed, the press would then be 6.8 N/mm × (0.65 + 0.25) mm plus the switch's
  0.98–1.57 N, so 7.1–7.7 N. That is above item 5's 2–5 N.
- The stiffness and switch force are the model's own (checks.json `membrane`).

**What to do.** No redesign. The build guide already handles free play: build §4.4 step 5
adds 0.1 mm paper shims under the switch.
1. Measure B3.
2. Expect about (17.06 − B3) / 0.1 shims: **6 or 7** if B3 reads 16.41.
3. Shim until the click comes within the first 0.3 mm (build §4.4).
4. Then measure item 5.

Record B3 and the shim count. N23 in the [build log](../BUILD-LOG.md) tracks it; a fit
fix for rev A.1 follows only if the bench confirms it ([return loop](return-loop.md)).
