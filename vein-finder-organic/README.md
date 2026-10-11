# Vein Finder · Organic

A palm-sized, naked-eye **transillumination vein finder** shaped like a water-worn river stone.
It presses on the forearm and side-lights the skin with visible red light. Veins show as dark
lines inside an open crescent window. There is no camera, no screen and no app: the skin is
the display.

> ### ⚠ Personal prototype for bench evaluation — not a cleared medical device
> Not for diagnosis, treatment or clinical use on patients. Built and documented for
> one person's bench evaluation in a home workshop.

![Concept board](docs/01-concept/concept_preview.jpg)

## Status by gate
| Gate | Deliverable | Status |
|---|---|---|
| 1 Concept | one-page concept, three forms as renders, chosen form + why | **done; reviewed 2026-10-11** (answers in `docs/01-concept/concept.md` §9) |
| 2 CAD | parametric build123d model, STEP + print-ready 3MF, wall/fit/overhang reports | **done** — `docs/02-cad/cad.md` (one decision open: optional window-wall relief, §7) |
| 3 Electronics | schematic, PCB outline (KiCad), BOM with links and prices | not started |
| 4 Firmware | MCU source: 3 brightness levels, bank switch, 3-min auto-off, 41 °C limit | not started |
| 5 Verification | walls & fits, runtime, thermal, IEC 62471, cost total; print settings + assembly guide | not started |

## Layout
```
cad/stone/organic.py        G2 "inflated planform" surface engine (single periodic C2 B-spline skin, G2 poles)
cad/stone/verify_g2.py      ring / seam / equator curvature-continuity tests
cad/concepts/               gate 1: the three concept forms, feasibility, review renders
cad/device/params.py        gate 2: every internal dimension (single source of truth)
cad/device/skin.py          device skin (form A + thumb dish) and inner offset ("cavity") solids
cad/device/layout.py        PCB outline, LED ring, magnets, seam mask, bridge, USB-C from the real cavity
cad/device/parts.py         top shell, sole, seam mask, button bridge + stand-ins for bought parts
cad/device/checks.py        walls, overhang, interference, mass, button force (shell Ritz), magnet pull
cad/device/build.py         build -> BREP cache, STEP, PLY, 3MF, checks
calc/                       physics notes, concept budgets, pinning tests
render/                     Mitsuba 3 studio, concept and CAD renders
docs/01-concept/            concept.pdf (A3 board), concept.md (evidence), renders, figures, STEP
docs/02-cad/                cad.md (gate-2 report), renders, figures, step.zip, 3mf/, pcb/ (DXF + layout.json)
build/                      generated (gitignored)
```

## Rebuild
```bash
pip install -r requirements.txt
# gate 1
cd cad/concepts && python build_concept.py A && python feasibility.py
cd ../../calc && python -m pytest -q && python concept_budget.py
cd ../render && python concept_renders.py
cd ../docs/01-concept && python figures.py && python build_pdf.py
# gate 2
cd ../../cad/device && python layout.py && python build.py --force --3mf --checks && python verify_skin.py
cd ../../render && python cad_renders.py --spp 128 --scale 1.0
cd ../docs/02-cad && python figures.py && python package.py
```
