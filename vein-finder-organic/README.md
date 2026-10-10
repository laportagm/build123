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
| 1 Concept | one-page concept, three forms as renders, chosen form + why | **done; awaiting review** |
| 2 CAD | parametric build123d model, STEP + print-ready 3MF, wall/fit/overhang reports | not started |
| 3 Electronics | schematic, PCB outline (KiCad), BOM with links and prices | not started |
| 4 Firmware | MCU source: 3 brightness levels, bank switch, 3-min auto-off, 41 °C limit | not started |
| 5 Verification | walls & fits, runtime, thermal, IEC 62471, cost total; print settings + assembly guide | not started |

## Layout
```
cad/stone/organic.py        G2 "inflated planform" surface engine (single periodic C2 B-spline skin)
cad/concepts/options.py     the three concept forms as parameters (A Pebble, B Crescent, C Hagstone)
cad/concepts/build_concept.py   fit -> OCC solid -> waterline split -> STEP + review renders
cad/concepts/feasibility.py     overhang (support-free), cell & switch fit, mass
calc/                       physics notes, concept budgets, pinning tests
render/                     Mitsuba 3 studio + concept renders
docs/01-concept/            concept.pdf (A3 board), concept.md (evidence), renders, figures, STEP
build/                      generated (gitignored)
```

## Rebuild
```bash
pip install -r requirements.txt
cd cad/concepts && python build_concept.py A && python feasibility.py
cd ../../calc && python -m pytest -q && python concept_budget.py
cd ../render && python concept_renders.py
cd ../docs/01-concept && python figures.py && python build_pdf.py
```
