"""
KiCad 7 schematic writer driven by `design.py`.

Every part is a real KiCad library symbol (embedded in the sheet's lib_symbols, as KiCad
does).  Connectivity is by net labels: each pin gets a short wire stub ending in a local
label that carries the net name, so the drawn sheet and `design.py` cannot disagree.
`verify_netlist()` exports the netlist with kicad-cli and checks it against the design.
"""
from __future__ import annotations

import subprocess
import uuid
from pathlib import Path

from sexp import Q, dump, find, first, parse

GRID = 1.27


def _uid():
    return str(uuid.uuid4())


def snap(v, g=GRID):
    return round(v / g) * g


# ----------------------------------------------------------------------------- library
class SymbolLib:
    def __init__(self, sym_dirs):
        self.dirs = [Path(d) for d in (sym_dirs if isinstance(sym_dirs, (list, tuple)) else [sym_dirs])]
        self._libs = {}

    def _lib(self, name):
        if name not in self._libs:
            for d in self.dirs:
                f = d / f"{name}.kicad_sym"
                if f.exists():
                    self._libs[name] = parse(f.read_text())[0]
                    break
            else:
                raise FileNotFoundError(f"{name}.kicad_sym not in {self.dirs}")
        return self._libs[name]

    def raw(self, lib, name):
        for s in find(self._lib(lib), "symbol"):
            if s[1] == name:
                return s
        raise KeyError(f"{lib}:{name}")

    def flat(self, lib_id):
        """Symbol definition flattened (resolves `extends`), renamed to the full lib_id."""
        lib, name = lib_id.split(":")
        s = self.raw(lib, name)
        ext = first(s, "extends")
        if ext is None:
            out = [x for x in s]
            out[1] = Q(lib_id)
            # rename the unit sub-symbols to the plain symbol name (KiCad convention)
            return out
        parent = self.raw(lib, ext[1])
        out = ["symbol", Q(lib_id)]
        props = {p[1]: p for p in find(s, "property")}
        for c in parent[2:]:
            if isinstance(c, list) and c and c[0] == "property":
                out.append(props.pop(c[1], c))
            elif isinstance(c, list) and c and c[0] == "symbol":
                sub = [x for x in c]
                sub[1] = Q(c[1].replace(ext[1], name, 1))
                out.append(sub)
            else:
                out.append(c)
        out.extend(props.values())
        return out

    def pins(self, lib_id, unit=1):
        """{number: (x, y, angle_deg, name, etype)} in symbol coordinates (y up)."""
        s = self.flat(lib_id)
        res = {}
        for sub in find(s, "symbol"):
            nm = str(sub[1])
            try:
                u = int(nm.split("_")[-2])
            except ValueError:
                continue
            if u not in (0, unit):
                continue
            for p in find(sub, "pin"):
                at = first(p, "at")
                num = str(first(p, "number")[1])
                pname = str(first(p, "name")[1])
                res[num] = (float(at[1]), float(at[2]), float(at[3]) if len(at) > 3 else 0.0, pname, str(p[1]))
        return res


# ----------------------------------------------------------------------------- writer
class Sheet:
    def __init__(self, lib: SymbolLib, title, project, rev="A", date="2026-10-11", comments=()):
        self.lib = lib
        self.root = _uid()
        self.project = project
        self.items = []
        self.lib_ids = {}
        self.title = title
        self.rev = rev
        self.date = date
        self.comments = comments

    def text(self, s, x, y, size=2.0, bold=False):
        eff = ["effects", ["font", ["size", size, size]] + (["bold"] if bold else []), ["justify", "left", "bottom"]]
        self.items.append(["text", Q(s), ["at", snap(x), snap(y), 0], eff, ["uuid", Q(_uid())]])

    def rect(self, x0, y0, x1, y1):
        self.items.append(["rectangle", ["start", snap(x0), snap(y0)], ["end", snap(x1), snap(y1)],
                           ["stroke", ["width", 0.15], ["type", "dash"]], ["fill", ["type", "none"]], ["uuid", Q(_uid())]])

    def place(self, part, x, y, show_value=True):
        """Place a part's symbol at (x, y) and label every pin with its net."""
        lib_id = part.lib_id
        if lib_id not in self.lib_ids:
            self.lib_ids[lib_id] = self.lib.flat(lib_id)
        x, y = snap(x), snap(y)
        pins = self.lib.pins(lib_id)
        sym_def = self.lib_ids[lib_id]
        props = {str(p[1]): p for p in find(sym_def, "property")}

        def prop(name, val, dx, dy, hide=False):
            eff = ["effects", ["font", ["size", 1.27, 1.27]]]
            if hide:
                eff.append(["hide", "yes"]) if False else eff.append("hide")
            return ["property", Q(name), Q(val), ["at", snap(x + dx), snap(y + dy), 0], eff]

        ref_at = props.get("Reference")
        val_at = props.get("Value")
        rdx, rdy = (float(ref_at[3][1]), -float(ref_at[3][2])) if ref_at else (0, -3)
        vdx, vdy = (float(val_at[3][1]), -float(val_at[3][2])) if val_at else (0, 3)
        node = ["symbol", ["lib_id", Q(lib_id)], ["at", x, y, 0], ["unit", 1],
                ["in_bom", "no" if part.dnp else "yes"],
                ["on_board", "yes" if part.on_board else "no"],
                ["dnp", "yes" if part.dnp else "no"], ["uuid", Q(_uid())],
                prop("Reference", part.ref, rdx, rdy),
                prop("Value", part.value, vdx, vdy, hide=not show_value),
                prop("Footprint", part.footprint, 0, 0, hide=True),
                prop("Datasheet", part.datasheet or "~", 0, 0, hide=True)]
        for k, v in (("MPN", part.mpn), ("Manufacturer", part.mfr), ("Distributor", part.dist),
                     ("Distributor PN", part.dist_pn), ("URL", part.url), ("Verified", part.verify)):
            if v:
                node.append(prop(k, v, 0, 0, hide=True))
        for num in pins:
            node.append(["pin", Q(num), ["uuid", Q(_uid())]])
        node.append(["instances", ["project", Q(self.project), ["path", Q("/" + self.root), ["reference", Q(part.ref)], ["unit", 1]]]])
        self.items.append(node)
        # stubs + labels
        for num, (px, py, ang, pname, etype) in pins.items():
            sx, sy = x + px, y - py                      # pin connection point, sheet coords (y down)
            net = part.pins.get(num)
            if net is None:
                if etype in ("no_connect",):
                    continue
                self.items.append(["no_connect", ["at", snap(sx), snap(sy)], ["uuid", Q(_uid())]])
                continue
            # outward direction = opposite of the pin's body-facing angle (symbol y up -> sheet y down)
            import math
            dx = -math.cos(math.radians(ang))
            dy = math.sin(math.radians(ang))
            ex, ey = sx + 2.54 * dx, sy + 2.54 * dy
            self.items.append(["wire", ["pts", ["xy", snap(sx), snap(sy)], ["xy", snap(ex), snap(ey)]],
                               ["stroke", ["width", 0], ["type", "default"]], ["uuid", Q(_uid())]])
            lab_ang = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[(round(dx), round(dy))]
            just = "left" if lab_ang in (0, 90) else "right"
            self.items.append(["label", Q(net), ["at", snap(ex), snap(ey), lab_ang], ["fields_autoplaced"],
                               ["effects", ["font", ["size", 1.0, 1.0]], ["justify", just, "bottom"]],
                               ["uuid", Q(_uid())]])

    def write(self, path: Path):
        tb = ["title_block", ["title", Q(self.title)], ["date", Q(self.date)], ["rev", Q(self.rev)],
              ["company", Q("Personal prototype for bench evaluation - NOT a medical device")]]
        for i, c in enumerate(self.comments, 1):
            tb.append(["comment", i, Q(c)])
        doc = ["kicad_sch", ["version", 20230121], ["generator", "eeschema"], ["uuid", Q(self.root)],
               ["paper", Q("A3")], tb, ["lib_symbols"] + list(self.lib_ids.values())]
        doc += self.items
        doc.append(["sheet_instances", ["path", Q("/"), ["page", Q("1")]]])
        Path(path).write_text(dump(doc) + "\n")


# ----------------------------------------------------------------------------- netlist check
def export_netlist(sch: Path, out: Path):
    subprocess.run(["kicad-cli", "sch", "export", "netlist", "--output", str(out), str(sch)],
                   check=True, capture_output=True)
    return parse(out.read_text())[0]


def nets_from_netlist(net_root):
    nets = {}
    for n in find(first(net_root, "nets"), "net"):
        name = str(first(n, "name")[1]).lstrip("/")
        nodes = sorted((str(first(nd, "ref")[1]), str(first(nd, "pin")[1])) for nd in find(n, "node"))
        nets[name] = nodes
    return nets
