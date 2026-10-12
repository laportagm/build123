# Build log

> **Personal prototype for bench evaluation. Not a cleared medical device.**
> Not for diagnosis, treatment or clinical use.

A running, dated log of the physical build and its revisions. Newest entry last.

**Earlier decisions are not repeated here:**
- [readiness.md](06-verification/readiness.md): the issue register N01–N22, including the
  provisional **N19** decision of 2026-10-12;
- [electronics.md §7](03-electronics/electronics.md#7-conflicts-and-decisions): the
  decisions settled on 2026-10-12.

Issues found from here on continue that numbering (N23 and on), in this log.

---

## 2026-10-12: build packet for the first unit (rev A)

**What.** The packet for building and testing the first physical unit, in
[`docs/08-prototype/`](08-prototype/README.md):
1. [status](08-prototype/status.md): verified in software vs unproven on hardware;
2. [order list](08-prototype/order-list.md);
3. [print packet](08-prototype/print-packet.md);
4. [build-day checklist](08-prototype/build-day.md);
5. [bench data sheet](08-prototype/bench-sheet.md);
6. [return loop](08-prototype/return-loop.md).

**Baseline.** `f2a3eef`, the head of PR #1 (open, mergeable, unmerged).

**Gates re-run** on the packet branch:
- firmware: 2208 B, build checks passed, all logic tests passed, 26/26 mutants caught,
  the watchdog test image builds;
- calc: 11 passed;
- `check_fab` 10/10; `check_fit` 7/7;
- the models reproduce byte for byte.

Image hashes: `fw.hex` `e8bc8159…`, `fw_wdt_test.hex` `2dde1528…` (full values in
status §2). **Nothing in `cad/`, `fw/`, `ee/` or `calc/` changed.**

**Order.**
- Parts $42.91, PCB $5–15 (estimate), so $47.91–57.91 for one device.
- One change from the order pack: 11 ring LEDs of each wavelength instead of 10 (6
  fitted, 3 for the optical test, 2 spare).
- The other spares come from minimum order quantities: 9 NTCs, 99 R9s, 4 TPS61169s.
- Flags:
  - F1: the 625 nm LED's status is disputed between sources, and no verified substitute
    was found;
  - F2: the 10 k line shows 0 stock in one LCSC copy (fallback: the same MPN at Digi-Key);
  - F3: the switch has no LCSC snippet (fallback: Digi-Key SW402-ND, the same MPN);
  - F5: the amber LED's alternate is now on backorder.
- Prices and stock are search snippets only; the distributor sites are blocked here.
  **No order placed.**

**Print.**
- Four parts. The seam mask is **not needed for function** (it only guides the status
  light), so it is printed last.
- First-article limits come from the clearances in `params.py`.
- The board's thickness tolerance was already there: `params.py` says "boards are
  1.0 ± 0.1". That closes checklist M2.

**N23 (new): the bridge's switch seat.**
- `parts.py` cuts a 0.60 mm-deep seat (6.3 × 6.3 mm) into the pedestal for the 6.0 mm
  switch body. The CAD's switch stand-in, the 0.05 mm gap (`params.py`) and the
  button-force model (`checks.json`) all put the switch on the pedestal top.
- If the body drops into the seat, the dish moves about 0.65 mm before it meets the
  actuator, the click comes at about 0.90 mm, and the press unshimmed is 7.1–7.7 N, above
  item 5's 2–5 N.
- The existing shim step (build §4.4) covers it with about 6–7 paper shims.
- Status: **open**. Checked by print packet B3, build-day 4.4 and item 5. A rev A.1 fit
  fix only if the bench confirms it. No CAD change now (no redesign).

**Documentation corrected with the packet:**
- checklist 3.8: 11 LEDs of each type are ordered;
- checklist 2.1 and M2: the board tolerance cited from `params.py`;
- checklist 1.6: the lip is recorded rather than judged "about 0.9 mm";
- checklist 2.10, 2.19 and 3.7: firmware, board and limit changes go through the return
  loop, with every gate re-run;
- build §3 and §4.4: pointers to the build-day list and the switch-seat note.

**Housekeeping (your request).**
- The scheduled check-in on PR #1 (`trig_01SAH7nDY3B2nv2aUTeR5inf`) was deleted, and
  this session unsubscribed from PR #1's events.
- PR #1 is left for you to merge.

### Same day: independent audit of the packet

An independent check of every number against its source found 25 issues. All are fixed
in the follow-up commit. Every fix is to the packet or the checklist; nothing in `cad/`,
`fw/`, `ee/` or `calc/` changed. The main ones:
- **GATE N19 would have failed a good unit.** It asked for 223–268 mA from a full cell. It
  now runs after the runtime test, with the cell below full, and asks for charging shown
  (more than the 24.5 mA termination current).
- **Prints:**
  - the USB-C opening's width in the sole is 8.87 mm, not the full stadium's 9.44;
  - dry magnets stand 0.05 mm lower than in the CAD, and the top pockets are cut deeper
    too, so fully seated magnets leave a 0.25 mm gap, not 0.15;
  - the mask limit is 6.77 mm, measured along its slope;
  - the seam is a groove from the inside, not an open slot.
- **Safety order:**
  - no soldering on a live board: the posts move before power, and RT1 is fitted with the
    supply off;
  - the R9 voltage is read at level 1 before higher levels;
  - charging (3.15) and optical power (5.10) are now safety steps;
  - GATE A and GATE B now need every step, not only the ⚠ ones (readiness §5);
  - the 625 nm face test puts thermocouple 1 on a lit 625 nm pocket.
- **Wrong correction withdrawn.** The checklist's 308–368 g was right: it is the exact
  conversion of checks.json's 3.02–3.61 N. It is restored and cited.
- **Smaller fixes:**
  - the R9 window follows the meter's accuracy;
  - the cell is rejected above 4.28 V too;
  - N19's fallback options point to readiness N19, not electronics §7;
  - the CAP change in the return loop now needs your decision;
  - the bench sheet's self-check covers every number it prints.

**For your decision, about N19** (decided the same day: see the next entry):
- N19 records the USB-C lip as 0.91 mm. That is `checks.json`'s minimum, from a probe that
  stops 0.15 mm short of the landing face (`cad/device/checks.py`).
- On the print mesh, the lip is 0.95 mm well inside, 0.91 mm at 0.2 mm in, and **0.87 mm
  at the landing face itself** (`print_dims.json`, `usb_lip_from_landing_face`).
- The provisional acceptance and bench item 20 are unchanged. Item 20 tests the lip as
  printed, edge included. The packet measures S10 at least 0.2 mm in.
- Whether N19's record should also state the 0.87 mm edge value is your call.

**Open, in order:**
1. Merge PR #1.
2. Order: checklist 1.3 on the live pages.
3. Print, then the first-article checks.
4. Build day.
5. Send the sheet ([return loop](08-prototype/return-loop.md)).

---

## 2026-10-12: N19 record, edge value added

**Your decision:** add the 0.87 mm edge value to N19's record.

**Done.** [readiness N19](06-verification/readiness.md) now records the lip as 0.91 mm,
and 0.87 mm at the landing face itself:
- the register row and the final register;
- the decision section, with an "Edge value" note giving the source and the profile:
  0.95 mm 1 mm in, 0.91 mm 0.2 mm in, 0.87 mm at the face (`print_dims.json`);
- the physical-measurement table.

**Citations updated to match:** verification §1, §2 and item 20; the checklist's N19
paragraph and 1.6; the README status row; packet status §1.

**Unchanged:**
- the provisional acceptance;
- bench item 20 (GATE N19), which tests the lip as printed, edge included;
- the first-article check, still taken at least 0.2 mm in;
- electronics §7's settled-decision table, which points to readiness N19.

No CAD, firmware, board or BOM change.

**Next entry:** rev A.1, after the bench results.
