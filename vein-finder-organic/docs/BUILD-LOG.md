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
- If the body drops into the seat, the free travel before the click is about 0.65 mm,
  and the press unshimmed is 7.1–7.7 N, above item 5's 2–5 N.
- The existing shim step (build §4.4) covers it with about 6–7 paper shims.
- Status: **open**. Checked by print packet B3, build-day 4.4 and item 5. A rev A.1 fit
  fix only if the bench confirms it. No CAD change now (no redesign).

**Documentation corrected with the packet:**
- checklist 3.2: the expected grams for 3.0–3.6 N are 306–367 g (was 308–368 g);
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

**Open, in order:**
1. Merge PR #1.
2. Order: checklist 1.3 on the live pages.
3. Print, then the first-article checks.
4. Build day.
5. Send the sheet ([return loop](08-prototype/return-loop.md)).

**Next entry:** rev A.1, after the bench results.
