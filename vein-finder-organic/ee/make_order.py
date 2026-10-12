"""
Order pack from the BOM (design.py): one page with the PCB settings and the steps per
distributor, plus cart files.

    python make_order.py   ->  docs/07-order/order.md, digikey_cart.csv, lcsc_cart.csv,
                               adafruit_list.csv

Personal prototype for bench evaluation - NOT a medical device.
"""
from __future__ import annotations

import csv
from collections import OrderedDict
from pathlib import Path

import design as D
from make_bom import rows

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "07-order"
FAB = ROOT / "docs" / "03-electronics" / "fab"

# board facts for the fab order (from the routed board; make_pcb.py checks them)
BOARD = dict(size="85.8 × 54.5 mm", layers=2, thickness="1.0 mm", copper="1 oz (35 µm) outer",
             track="0.25 mm (0.2 mm minimum gap)", via="0.6 mm pad, 0.3 mm drill",
             holes="1.0 mm plated (6 locating pins); plated slots 0.6 × 1.2 and 0.6 × 1.6 mm (USB-C shell)",
             edge="0.3 mm copper to edge, except the USB-C pads at 0.20 mm (datasheet land pattern)")


def money(v):
    return "NV" if v is None else f"{v:.2f}"


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rs = rows()
    by = OrderedDict()
    for r in rs:
        by.setdefault(r["distributor"], []).append(r)

    # cart files: the columns each distributor's list / BOM upload can be mapped from
    with open(OUT / "digikey_cart.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Quantity", "Digi-Key Part Number", "Manufacturer Part Number", "Customer Reference"])
        for r in by.get("Digi-Key", []):
            w.writerow([r["order_qty"], r["distributor_pn"], r["mpn"], r["refs"]])
    with open(OUT / "lcsc_cart.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Quantity", "LCSC Part Number", "Manufacturer Part Number", "Comment"])
        for r in by.get("LCSC", []):
            w.writerow([r["order_qty"], r["distributor_pn"], r["mpn"], r["refs"]])
    with open(OUT / "adafruit_list.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["Quantity", "Adafruit product ID", "Description", "URL"])
        for r in by.get("Adafruit", []):
            w.writerow([r["order_qty"], r["distributor_pn"], r["description"], r["url"]])

    def total(d):
        return sum(r["line_cost_usd"] for r in by.get(d, []) if r["line_cost_usd"] is not None)
    nv = [r for r in rs if r["line_cost_usd"] is None]
    tools = D.TOOLS
    lo, hi = D.PCB["price_estimate"]
    zipname = "vein_finder-gerbers.zip"

    L = ["# Order pack", "",
         "> **Personal prototype for bench evaluation. Not a cleared medical device.**",
         "> Not for diagnosis, treatment or clinical use.", "",
         "Everything needed to order one device: the board, three parts orders and one tool.",
         "The files here are made from `ee/design.py` by `ee/make_order.py`; quantities include",
         "minimum order sizes and a few spares. **Prices and stock come from search-result",
         "snippets** (the distributor pages could not be opened from where this was made): check",
         "each line on the live page before paying.", "",
         "| Order | What | Cost (USD) |", "|---|---|---|",
         f"| PCB fab | 5 bare boards (§1) | {lo:.0f}–{hi:.0f} (estimate, NV) |"]
    sec = {"Digi-Key": 2, "LCSC": 3, "Adafruit": 4}
    for d in by:
        L.append(f"| {d} | {len(by[d])} lines (§{sec.get(d, '')}) | {total(d):.2f} |")
    L.append(f"| **Parts + PCB** | | **{sum(total(d) for d in by) + lo:.0f}–{sum(total(d) for d in by) + hi:.0f}** |")
    for t in tools:
        L.append(f"| Tool, one-off | {t['item']} | {t['price']:.2f} |")
    L += ["", "Shipping is not included.", ""]

    L += ["## 1. PCB", "",
          f"Upload [`{zipname}`](../03-electronics/fab/{zipname}) (Gerbers and drill files) to any",
          "fab (JLCPCB, PCBWay, OSH Park, …). Choose:", "",
          "| Setting | Value |", "|---|---|",
          f"| Layers | {BOARD['layers']} |",
          f"| Size | {BOARD['size']} (the fab reads it from the outline) |",
          f"| **Thickness** | **{BOARD['thickness']}** (not the usual 1.6 mm: the stone is sized for 1.0) |",
          f"| Copper | {BOARD['copper']} |",
          "| Surface finish | HASL (lead-free) or ENIG |",
          "| Solder mask | any colour; black matches the sole |",
          "| Silkscreen | white |",
          "| Quantity | 5 (the usual minimum) |",
          "| Assembly, stencil | none: everything is hand-soldered |", "",
          "What the fab's checks will see:", "",
          f"- Smallest track {BOARD['track']}; vias {BOARD['via']}.",
          f"- Holes: {BOARD['holes']}.",
          f"- Edge: {BOARD['edge']}. **Check that one against the fab's",
          "  copper-to-board-edge minimum**; if it is larger, ask the fab whether it can pull the",
          "  copper back at the USB-C notch.",
          "- The outline is a C with four magnet holes; the two at the tail open onto the edge. The fab",
          "  routes them like any outline.", ""]

    def dist_section(n, d, how):
        out = [f"## {n}. {d}", "", how, "",
               "| Qty | Part number | Manufacturer, MPN | For | Unit $ | Line $ |", "|---|---|---|---|---|---|"]
        for r in by.get(d, []):
            pn = f"[{r['distributor_pn']}]({r['url']})" if r["url"] else r["distributor_pn"]
            unit = "NV" if r["unit_price_usd"] is None else f"{r['unit_price_usd']:.4g}"
            out.append(f"| {r['order_qty']} | {pn} | {r['manufacturer']} {r['mpn']} | {r['refs']} | {unit} | {money(r['line_cost_usd'])} |")
        out += [f"| | | | | **Total** | **{total(d):.2f}** |", ""]
        return out
    L += dist_section(2, "Digi-Key",
                      "Upload [`digikey_cart.csv`](digikey_cart.csv) with Digi-Key's list / BOM upload and map the "
                      "columns (Quantity, Digi-Key Part Number), or add the lines one by one.")
    L += dist_section(3, "LCSC",
                      "Upload [`lcsc_cart.csv`](lcsc_cart.csv) with LCSC's BOM tool and map the columns (Quantity, "
                      "LCSC Part Number). The quantities already respect LCSC's minimum order per line.")
    L += dist_section(4, "Adafruit",
                      "Adafruit has no list upload: add the three products from their pages "
                      "([`adafruit_list.csv`](adafruit_list.csv) has the links).")
    L += ["## 5. Tool", ""]
    for t in tools:
        L.append(f"- {t['item']}: {t['mfr']} {t['mpn']}, [{t['dist']} {t['dist_pn']}]({t['url']}), "
                 f"${t['price']:.2f}. Set it to 5 V logic and wire only UPDI and GND (firmware notes, §4).")
    L += ["", "## 6. Before you pay", "",
          "- Open every line on the live page: prices and stock here are from snippets.",
          ]
    if nv:
        L.append("- Lines without a verified price: " + ", ".join(f"{r['mpn']} ({r['distributor']} {r['distributor_pn']})" for r in nv) + ".")
    L += ["- PCB thickness 1.0 mm, and the USB-C edge clearance (§1).",
          "- The two magnet sizes are easy to mix up: 8193 is 1/8″ thick (horn dowels), 8195 is 1/16″.",
          "- Keep the two LED reels apart when they arrive (660 nm XZM2MR55W-3, 625 nm XZM2CRK55W-3): "
          "they look alike, and the build guide places them by reel.", ""]
    (OUT / "order.md").write_text("\n".join(L) + "\n")
    print("order pack ->", OUT)


if __name__ == "__main__":
    main()
