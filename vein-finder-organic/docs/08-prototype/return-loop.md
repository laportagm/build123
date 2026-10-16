# Return loop: after the bench

> **Personal prototype for bench evaluation. Not a cleared medical device.**
> Not for diagnosis, treatment or clinical use.

What to send back after the build, and what then happens to it. **Nothing in §2 starts
until your results arrive.**

## 1. What to send back

| What | From | Needed |
|---|---|---|
| [`bench-sheet.csv`](bench-sheet.csv): `measured`, `pass_fail` and `notes` on every row you ran | the whole build | yes |
| [`bench-offset-log.csv`](bench-offset-log.csv): TC1, TC2 and events per minute, both banks | build-day 5.7 | if 5.7 ran |
| **Photos:** the USB-C lip at print time and before and after the 20 cycles; both board sides after soldering; the dry fit; any light leak; anything that failed | build-day 1, 2.3, 4.2, 5.4, 5.5 | yes |
| **Slicer screenshots:** the layer view at the USB-C lip and over the button skin | print packet §2 | yes |
| **Scope captures:** VOUT and the drain at turn-off (4); VBUS to the seam at USB wake | build-day 3.7, 3.15 | yes |
| **Context:** `git log -1` of what you built; the firmware hashes; printer, filament and any setting that differs from print packet §1; the meter and thermocouple models; any step done differently | — | yes |

**How:** attach the files in this session or a new one, or commit them to
`docs/08-prototype/results/<date>/` on a branch.

## 2. What happens with it

### Step 1. Triage
- Check every row against its limit.
- List the fails, the deviations from the expected values, and the record-only values.
- Note which gates passed: A, N19, B.

### Step 2. Rules for any change
- **Only what the data requires.** Each change cites the row IDs that call for it.
- **No redesign, no rev B, no styling changes.**
- **N19 is not reopened.** If GATE N19 failed, its documented options come to you; nothing
  changes without your decision.
- **Stop and ask** if a result conflicts with N19, with a settled decision (electronics
  §7, the readiness register), or with this build log, and before any substitute part or
  board change.

### Step 3. Changes, in lockstep
The limits live in `fw/src/logic.h`; the predictions live in `cad/`, `calc/`, `ee/` and
the model scripts beside the docs. They change together, or not at all.

| If the bench shows | Change | And, in the same commit |
|---|---|---|
| **Thermocouple 1 passed 41 °C on the phantom** (B-3.7), still after thermal paste on RT1 (N20); or the cut-off came only above 42 °C (B-3.6) | lower `T_DERATE_DC`, `T_LIMIT_DC` and `T_CUTOFF_DC` in `logic.h` by the overshoot, thermocouple 1's maximum − 41 °C: the documented rule (verification §4; checklist 3.7). The offset rows (B-3.6, B-3.7) are supporting data; reading them together is PROPOSED, not a rule | the thermal tests and labels in `fw/test/test_logic.c` and `mutants.py`; `thermal.py`'s inputs refitted so it reproduces the measured face temperatures, then its output; firmware §1–2, verification §4 and item 11, build §5, checklist 3.6–3.7; `make_bench_sheet.py`, whose checks fail until the thresholds are updated |
| **Lower limits would derate it in normal use**, or brightness is in question | nothing by default. Lowering `CAP_A_PERMILLE` / `CAP_B_PERMILLE` is not a documented remedy: it would change the brightness settled in electronics §7 and the caps firmware §1 takes from the concept's thermal study. **Only on your decision** | if you decide it: the caps in `budget.py` and `budget.json`; electronics §5; runtime (verification §3); `optics.py` and `iec62471.py` at the new current |
| **Measured optical power** (B-3.8) differs from the 12 mW (660 nm) estimate | the power inputs to `optics.py`, `iec62471.py` and `thermal.py` | their outputs; electronics §5; verification §4 and §6. Above about 2× the estimate, the IEC 62471 result is re-checked first |
| **LED current, VOUT or supply current** off the model (A-2.9) | record the cause (R9, VREF, efficiency). Change `budget.py` only for a measured input | `budget.json`; electronics §5 |
| **VOUT rises at turn-off** (A-2.10) | the pre-authorised fix in item 16: keep the gate on one tick after CTRL goes low (`fw/src/logic.c`) | a host test for the new order and a mutant for it; firmware §2 |
| **USB not detected with a full cell** (A-2.19) | R7 → 200 kΩ, the documented fix, **only with your approval** (a board change) | `ee/design.py`, then schematic, PCB, BOM, order pack and fab files regenerated; electronics §2 |
| **A print fit fails** (section P, A-2.20). First candidate: the 0.60 mm switch seat if B3 confirms it (print packet §5) | the clearance in `cad/device/params.py` or the feature in `parts.py`. Fit only: no change to the skin or the form | CAD rebuild (`layout.py`; `build.py --force --3mf --checks`; `verify_skin.py`); `checks.json` read against every thin-spot decision (no new thin spot without you); `print_dims.py`; the print packet; `make_bench_sheet.py` |
| **Sleep or held-button current** (A-2.14) | none in code; the measured values | budget standby; firmware §2.1 (N14) |
| **Timing off** (A-2.13) | none in code unless you ask; the measured tick | firmware §1.1 (N05) |

### Step 4. Re-run every gate before committing
1. `make -C fw clean all`, `make -C fw test`, `make -C fw mutants`, `make -C fw wdt-test`.
2. `cd calc && python -m pytest -q`.
3. `python ee/check_fab.py` and `python ee/check_fit.py`.
4. `thermal.py`, `iec62471.py`, `budget.py`, `optics.py`: commit their outputs when they
   change; otherwise they must be identical.
5. `print_dims.py` and `make_bench_sheet.py`.
6. If `cad/` changed: the CAD build with checks, and `verify_skin.py`.
7. `git status` clean after the read-only checks.

A change ships only with all of them passing (your rule; checklist 1.1; readiness §5).

### Step 5. Record it
- **A "rev A.1" entry in [`docs/BUILD-LOG.md`](../BUILD-LOG.md):**
  - the date and the data received;
  - each change as file, old → new, and the row IDs that require it;
  - the gate results;
  - what is still open;
  - which bench rows to repeat (for example a new image: A-1.2, build-day 3.2; new
    limits: 5.6 and 5.7; new fits: section P and 4.2).
- New issues continue the readiness numbering in the build log (N23 and on).

### Step 6. Hand back
- Commit on a new branch and open a draft PR.
- Then stop. You decide whether to rebuild, reprint or re-flash.

**Not done at any step:** placing orders; merging; changing N19 or any settled decision;
redesign; rev B; styling.
