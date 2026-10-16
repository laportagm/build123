# First unit: build packet (2026-10-12)

> **Personal prototype for bench evaluation. Not a cleared medical device.**
> Not for diagnosis, treatment or clinical use.

Everything needed to order, print, build and test the first physical unit, then send the
results back.

| # | Deliverable | File |
|---|---|---|
| 1 | Status: verified in software vs unproven on hardware; PR #1; watchers | [status.md](status.md) |
| 2 | Order list: every BOM line with spares, re-checked stock and prices, flags, total | [order-list.md](order-list.md) |
| 3 | Print packet: slicer settings, preview checks, first-article caliper checks | [print-packet.md](print-packet.md) |
| 4 | Build-day checklist, in build-guide order, with gates | [build-day.md](build-day.md) |
| 5 | Bench data sheet: one row per measurement; the per-minute offset log | [bench-sheet.md](bench-sheet.md), [bench-sheet.csv](bench-sheet.csv), [bench-offset-log.csv](bench-offset-log.csv) |
| 6 | Return loop: what to send back, and what happens next | [return-loop.md](return-loop.md) |

**Also here:**
- [checklist.md](checklist.md): the full procedure for every test. The build-day list
  puts them in build order.
- The log of this packet and of every revision after it:
  [docs/BUILD-LOG.md](../BUILD-LOG.md).

**Regenerate the generated files** (read-only on `cad/`):
```sh
python docs/08-prototype/print_dims.py        # print_dims.json, from docs/02-cad/3mf + params.py
python docs/08-prototype/make_bench_sheet.py  # bench-sheet.md / .csv, bench-offset-log.csv
```
`make_bench_sheet.py` stops with an error if any number it prints no longer matches its
source: values are read from the JSON files and `logic.h`, and each literal is checked
against the exact text of the document it cites.
