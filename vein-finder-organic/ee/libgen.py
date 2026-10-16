"""
Project-specific KiCad 7 symbols and footprints (written to ee/lib/), for the parts the
stock KiCad 7.0 libraries lack or whose stock land patterns are poor for an iron.

Pin-outs and land patterns, with sources:
  TPS61169DCK   1 SW, 2 GND, 3 FB, 4 CTRL, 5 VIN    (TI SNVSA40B pin table; TI E2E circuit file)
  BQ21040DBV    1 TS, 2 OUT, 3 /CHG, 4 ISET, 5 VSS, 6 IN   (TI SLUSCE2D pin table)
  USB4515-GF-A  GCT power-only mid-mount: contacts A5/B5 (CC), A9/B9 (VBUS), A12/B12 (GND)
                0.8 x 1.2 pads 7.35 behind the face at |y| 0.50 / 1.52 / 2.75; plated shell
                slots 0.6 x 1.6 (2.40 behind the face) and 0.6 x 1.2 (6.40), |y| 5.62
                (GCT 3D model + SnapEDA/UltraLibrarian footprints derived from the GCT drawing)
  SC-70-5       KiCad SOT-353 land pattern with the pads lengthened outward for an iron

Personal prototype for bench evaluation - NOT a medical device.
"""
from __future__ import annotations

from pathlib import Path

from sexp import Q, dump

LIB = Path(__file__).resolve().parent / "lib"
F = ["effects", ["font", ["size", 1.27, 1.27]]]
FH = ["effects", ["font", ["size", 1.27, 1.27]], "hide"]


# ----------------------------------------------------------------------------- symbols
def box_symbol(name, ref, value, footprint, datasheet, left, right, top=(), bottom=(), w=10.16, desc=""):
    """Rectangular symbol.  left/right/top/bottom: [(number, name, etype), ...] in order."""
    n_side = max(len(left), len(right), 1)
    h = max(2.54 * (n_side + 1), 7.62)
    half_h, half_w = h / 2, w / 2

    def ys(n):
        return [half_h - 2.54 * (i + 1) for i in range(n)]

    pins = []
    for (num, nm, et), y in zip(left, ys(len(left))):
        pins.append(["pin", et, "line", ["at", -half_w - 2.54, round(y, 2), 0], ["length", 2.54],
                     ["name", Q(nm), F], ["number", Q(num), F]])
    for (num, nm, et), y in zip(right, ys(len(right))):
        pins.append(["pin", et, "line", ["at", half_w + 2.54, round(y, 2), 180], ["length", 2.54],
                     ["name", Q(nm), F], ["number", Q(num), F]])
    for i, (num, nm, et) in enumerate(top):
        x = -2.54 * (len(top) - 1) / 2 + 2.54 * i
        pins.append(["pin", et, "line", ["at", round(x, 2), half_h + 2.54, 270], ["length", 2.54],
                     ["name", Q(nm), F], ["number", Q(num), F]])
    for i, (num, nm, et) in enumerate(bottom):
        x = -2.54 * (len(bottom) - 1) / 2 + 2.54 * i
        pins.append(["pin", et, "line", ["at", round(x, 2), -half_h - 2.54, 90], ["length", 2.54],
                     ["name", Q(nm), F], ["number", Q(num), F]])
    return ["symbol", Q(name), ["in_bom", "yes"], ["on_board", "yes"],
            ["property", Q("Reference"), Q(ref), ["at", 0, round(half_h + 4.0, 2), 0], F],
            ["property", Q("Value"), Q(value), ["at", 0, round(-half_h - 4.0, 2), 0], F],
            ["property", Q("Footprint"), Q(footprint), ["at", 0, 0, 0], FH],
            ["property", Q("Datasheet"), Q(datasheet), ["at", 0, 0, 0], FH],
            ["property", Q("Description"), Q(desc), ["at", 0, 0, 0], FH],
            ["symbol", Q(f"{name}_0_1"),
             ["rectangle", ["start", -half_w, round(half_h, 2)], ["end", half_w, round(-half_h, 2)],
              ["stroke", ["width", 0.254], ["type", "default"]], ["fill", ["type", "background"]]]],
            ["symbol", Q(f"{name}_1_1")] + pins]


def symbols():
    syms = [
        box_symbol("TPS61169DCK", "U", "TPS61169DCKR", "vf:SC-70-5_HandSolder",
                   "https://www.ti.com/lit/ds/symlink/tps61169.pdf",
                   left=[("5", "VIN", "power_in"), ("4", "CTRL", "input")],
                   right=[("1", "SW", "power_out"), ("3", "FB", "input")],
                   bottom=[("2", "GND", "power_in")],
                   desc="40 V boost white-LED driver, 1.2 MHz, 1.2 A switch, SC-70-5 (TI SNVSA40B)"),
        box_symbol("BQ21040DBV", "U", "BQ21040DBVR", "Package_TO_SOT_SMD:SOT-23-6",
                   "https://www.ti.com/lit/ds/symlink/bq21040.pdf",
                   left=[("6", "IN", "power_in"), ("1", "TS", "input"), ("4", "ISET", "passive")],
                   right=[("2", "OUT", "power_out"), ("3", "~{CHG}", "open_collector")],
                   bottom=[("5", "VSS", "power_in")],
                   desc="Li-ion linear charger, 4.2 V, 30 V input, OVP 6.6 V, SOT-23-6 (TI SLUSCE2D)"),
    ]
    doc = ["kicad_symbol_lib", ["version", 20220914], ["generator", "vf_libgen"]] + syms
    (LIB / "vf.kicad_sym").write_text(dump(doc) + "\n")


# ----------------------------------------------------------------------------- footprints
def _fp(name, descr, items, attr="smd"):
    head = ["footprint", Q(name), ["version", 20221018], ["generator", "vf_libgen"], ["layer", Q("F.Cu")],
            ["descr", Q(descr)], ["attr", attr] if attr else ["attr"],
            ["fp_text", "reference", Q("REF**"), ["at", 0, -3, 0], ["layer", Q("F.SilkS")],
             ["effects", ["font", ["size", 0.8, 0.8], ["thickness", 0.12]]]],
            ["fp_text", "value", Q(name), ["at", 0, 3, 0], ["layer", Q("F.Fab")],
             ["effects", ["font", ["size", 0.8, 0.8], ["thickness", 0.12]]]]]
    return head + items


def _pad_smd(num, x, y, w, h, shape="roundrect"):
    p = ["pad", Q(num), "smd", shape, ["at", round(x, 4), round(y, 4)], ["size", w, h],
         ["layers", Q("F.Cu"), Q("F.Paste"), Q("F.Mask")]]
    if shape == "roundrect":
        p.append(["roundrect_rratio", 0.25])
    return p


def _rect(layer, x0, y0, x1, y1, w=0.12):
    return [["fp_line", ["start", x0, y0], ["end", x1, y0], ["stroke", ["width", w], ["type", "solid"]], ["layer", Q(layer)]],
            ["fp_line", ["start", x1, y0], ["end", x1, y1], ["stroke", ["width", w], ["type", "solid"]], ["layer", Q(layer)]],
            ["fp_line", ["start", x1, y1], ["end", x0, y1], ["stroke", ["width", w], ["type", "solid"]], ["layer", Q(layer)]],
            ["fp_line", ["start", x0, y1], ["end", x0, y0], ["stroke", ["width", w], ["type", "solid"]], ["layer", Q(layer)]]]


def footprints():
    d = LIB / "vf.pretty"
    d.mkdir(parents=True, exist_ok=True)
    out = {}
    # GCT USB4515-GF-A.  Origin: face centre on the board top; +X out of the face.
    items = []
    for num, y in (("A5", -0.50), ("B5", 0.50), ("B9", -1.52), ("A9", 1.52), ("B12", -2.75), ("A12", 2.75)):
        items.append(_pad_smd(num, -7.35, y, 1.2, 0.8 if num.endswith("12") else (0.76 if num.endswith("9") else 0.7)))
    for xb, sl, pl in ((2.40, 1.6, 2.1), (6.40, 1.2, 1.7)):
        for y in (-5.62, 5.62):
            items.append(["pad", Q("S1"), "thru_hole", "oval", ["at", -xb, y, 90], ["size", 1.1, pl],
                          ["drill", "oval", 0.6, sl], ["layers", Q("*.Cu"), Q("*.Mask")]])
    items += _rect("F.CrtYd", -8.2, -6.4, 0.5, 6.4, 0.05)
    items += _rect("F.Fab", -7.13, -4.47, 0.0, 4.47, 0.1)
    items.append(["fp_text", "user", Q("board edge 0.85 behind face; cut-out 9.24 x 5.70"), ["at", -4, 7.2, 0],
                  ["layer", Q("Cmts.User")], ["effects", ["font", ["size", 0.5, 0.5], ["thickness", 0.08]]]])
    out["USB_C_GCT_USB4515-GF-A_MidMount"] = _fp(
        "USB_C_GCT_USB4515-GF-A_MidMount",
        "GCT USB4515-GF-A USB-C power-only receptacle, mid-mount 1.6 mm offset; needs a 9.24 x 5.70 mm board cut-out (in Edge.Cuts)",
        items)
    # SC-70-5 with pads lengthened outward (stock: 0.65 x 0.4 at +-0.95)
    items = []
    for num, x, y in (("1", -1, -0.65), ("2", -1, 0.0), ("3", -1, 0.65), ("4", 1, 0.65), ("5", 1, -0.65)):
        items.append(_pad_smd(num, x * 1.15, y, 1.05, 0.4))
    items += _rect("F.CrtYd", -1.95, -1.2, 1.95, 1.2, 0.05)
    items += _rect("F.Fab", -0.625, -1.0, 0.625, 1.0, 0.1)
    items.append(["fp_circle", ["center", -1.5, -1.25], ["end", -1.4, -1.25], ["stroke", ["width", 0.15], ["type", "solid"]],
                  ["fill", "solid"], ["layer", Q("F.SilkS")]])
    out["SC-70-5_HandSolder"] = _fp("SC-70-5_HandSolder", "SC-70-5 (SOT-353), KiCad land pattern with pads lengthened 0.4 mm outward for iron soldering", items)
    # wire pads
    for nm, w, h in (("WirePad_1.5x3.0mm", 1.5, 3.0), ("WirePad_1.2x2.0mm", 1.2, 2.0)):
        items = [_pad_smd("1", 0, 0, w, h)] + _rect("F.CrtYd", -w / 2 - 0.25, -h / 2 - 0.25, w / 2 + 0.25, h / 2 + 0.25, 0.05)
        out[nm] = _fp(nm, f"Solder pad {w} x {h} mm for a hook-up wire", items)
    # locating pin: plated 1.0 mm hole, round 1.7 pad, for a header post soldered from the underside
    items = [["pad", Q("1"), "thru_hole", "circle", ["at", 0, 0], ["size", 1.7, 1.7], ["drill", 1.0],
              ["layers", Q("*.Cu"), Q("*.Mask")]]] + _rect("F.CrtYd", -1.1, -1.1, 1.1, 1.1, 0.05)
    out["LocatingPin_D1.0mm"] = _fp("LocatingPin_D1.0mm", "Plated 1.0 mm hole, 1.7 mm pad, for a 0.64 mm square header post used as a locating pin", items, attr="through_hole")
    for nm, fp in out.items():
        (d / f"{nm}.kicad_mod").write_text(dump(fp) + "\n")
    return list(out)


if __name__ == "__main__":
    symbols()
    print(footprints())
