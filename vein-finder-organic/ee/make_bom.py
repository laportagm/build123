"""
Bill of materials (gate 3) from design.py: grouped by part number, with distributor part
numbers, links, unit prices at the order quantity, order quantities (minimum order sizes
and a few spares), the extended cost and how each line was verified.

    python make_bom.py  ->  docs/03-electronics/bom.csv, bom.md

Personal prototype for bench evaluation - NOT a medical device.
"""
from __future__ import annotations

import csv
from collections import OrderedDict
from pathlib import Path

import design as D

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "03-electronics"
FIELDS = ["item", "refs", "qty_per_device", "value", "description", "manufacturer", "mpn", "distributor",
          "distributor_pn", "url", "unit_price_usd", "order_qty", "line_cost_usd", "verification", "alternate"]


def _desc(p):
    return {"R": "resistor 1 %, 0603", "C": "ceramic capacitor", "D": "diode / LED", "U": "IC", "Q": "N-MOSFET 30 V, SOT-23",
            "L": "power inductor 10 uH, 4 x 4 x 1.8 mm", "J": "USB-C receptacle, power-only, mid-mount", "RT": "NTC 10 k 0603",
            "TP": "solder pad", "H": "locating pin (header post)", "BT": "Li-ion pouch cell with protection",
            "SW": "tact switch 6 x 6 mm THT, 5.0 mm"}.get("".join(c for c in p.ref if c.isalpha()), "")


def rows():
    groups = OrderedDict()
    for p in D.PARTS:
        if not p.mpn:
            continue
        key = (p.mpn, p.dist_pn)
        g = groups.setdefault(key, dict(parts=[], first=None))
        g["parts"].append(p)
        if g["first"] is None or (p.price or 0) > (g["first"].price or 0) or p.qty_order > g["first"].qty_order:
            g["first"] = p if (p.price or p.qty_order) else (g["first"] or p)
    out = []
    for (mpn, dpn), g in groups.items():
        f = g["first"]
        n = len(g["parts"]) if not f.ref.startswith("H") else len([q for q in D.PARTS if q.ref.startswith("H")])
        qty = max(f.qty_order, n) if f.qty_order else n
        price = f.price
        if f.ref.startswith("H"):
            n_dev, desc = n, f"{n} posts from one 40-pin header strip"
            qty = 1
        else:
            n_dev, desc = n, _desc(f)
        out.append(dict(item="", refs=" ".join(q.ref for q in g["parts"]), qty_per_device=n_dev, value=f.value,
                        description=desc, manufacturer=f.mfr, mpn=mpn, distributor=f.dist, distributor_pn=dpn, url=f.url,
                        unit_price_usd=price, order_qty=qty,
                        line_cost_usd=round(price * qty, 2) if price is not None else None,
                        verification=f.verify, alternate=f.alt))
    for o in D.OFFBOARD:
        out.append(dict(item="", refs="(off-board)", qty_per_device=o["qty"], value="", description=o["item"],
                        manufacturer=o["mfr"], mpn=o["mpn"], distributor=o["dist"], distributor_pn=o["dist_pn"], url=o["url"],
                        unit_price_usd=o["price"], order_qty=o["qty_order"], line_cost_usd=round(o["price"] * o["qty_order"], 2),
                        verification=o["verify"], alternate=""))
    for i, r in enumerate(out, 1):
        r["item"] = i
    return out


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rs = rows()
    with open(OUT / "bom.csv", "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=FIELDS)
        w.writeheader()
        for r in rs:
            w.writerow(r)
    by_dist = OrderedDict()
    nv = []
    for r in rs:
        by_dist.setdefault(r["distributor"], 0.0)
        if r["line_cost_usd"] is None:
            nv.append(r["mpn"])
        else:
            by_dist[r["distributor"]] += r["line_cost_usd"]
    parts_total = sum(by_dist.values())
    pcb_lo, pcb_hi = D.PCB["price_estimate"]
    tools = sum(t["price"] for t in D.TOOLS)
    lines = ["| # | Refs | Qty | Part | Manufacturer, MPN | Distributor, PN | Unit $ | Order | Line $ | Verified |",
             "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rs:
        price = f"{r['unit_price_usd']:.4g}" if r["unit_price_usd"] is not None else "NV"
        line = f"{r['line_cost_usd']:.2f}" if r["line_cost_usd"] is not None else "NV"
        part = (r["value"] + " " if r["value"] else "") + r["description"]
        lines.append(f"| {r['item']} | {r['refs']} | {r['qty_per_device']} | {part} | {r['manufacturer']} {r['mpn']} | "
                     f"[{r['distributor']} {r['distributor_pn']}]({r['url']}) | {price} | {r['order_qty']} | {line} | {r['verification']} |")
    summ = ["", "| Order | Parts cost (USD) |", "|---|---|"]
    for d, v in by_dist.items():
        summ.append(f"| {d} | {v:.2f} |")
    summ += [f"| **Parts, all distributors** | **{parts_total:.2f}** |",
             f"| PCB, 5 boards (estimate, NV) | {pcb_lo:.0f}-{pcb_hi:.0f} |",
             f"| **Device, parts + PCB** | **{parts_total + pcb_lo:.0f}-{parts_total + pcb_hi:.0f}** |",
             f"| Tool: UPDI programmer (one-off) | {tools:.2f} |"]
    if nv:
        summ.append(f"\nLines without a verified price: {', '.join(nv)}.")
    (OUT / "bom.md").write_text("\n".join(lines + summ) + "\n")
    print("\n".join(summ))
    return parts_total


if __name__ == "__main__":
    main()
