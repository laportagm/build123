"""
Finish the routing Freerouting leaves undone, and stitch the GND pours.

  1. For every connection DRC still reports open (pad / track pairs), route it with a
     two-layer grid A* (0.1 mm grid, 8 directions, vias between layers) around every
     existing pad, track, via and the board edge, at the net class's width and clearance.
  2. GND: place stitching vias wherever they fit (2.5 mm grid) and a via next to every GND
     pad, so each top-pour island joins the underside plane.
  3. Refill, DRC again.

    python finish_route.py      (after make_pcb.py; then make_pcb.py --stage finish)

Personal prototype for bench evaluation - NOT a medical device.
"""
from __future__ import annotations

import heapq
import math
import re
import sys
from pathlib import Path

import numpy as np
import pcbnew
import shapely
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union

from board import MM, dev, kpt

HERE = Path(__file__).resolve().parent
PCB = HERE / "kicad" / "vein_finder.kicad_pcb"
RES = 0.1                 # grid, mm
CLR = 0.2                 # copper clearance, mm
EDGE = 0.3                # copper to board edge, mm
VIA_D, VIA_DRILL = 0.6, 0.3
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)


def pad_poly(p, layer):
    ps = pcbnew.SHAPE_POLY_SET()
    p.TransformShapeToPolygon(ps, layer, 0, 5000)
    out = []
    for i in range(ps.OutlineCount()):
        ol = ps.Outline(i)
        out.append(Polygon([dev(ol.CPoint(k)) for k in range(ol.PointCount())]))
    return unary_union(out)


class Grid:
    def __init__(self, board):
        self.b = board
        outline = pcbnew.SHAPE_POLY_SET()
        board.GetBoardPolygonOutlines(outline)
        polys = []
        for i in range(outline.OutlineCount()):
            ol = outline.Outline(i)
            holes = [[dev(outline.Hole(i, h).CPoint(k)) for k in range(outline.Hole(i, h).PointCount())]
                     for h in range(outline.HoleCount(i))]
            polys.append(Polygon([dev(ol.CPoint(k)) for k in range(ol.PointCount())], holes))
        self.board_poly = unary_union(polys)
        x0, y0, x1, y1 = self.board_poly.bounds
        self.x0, self.y0 = x0 - 1, y0 - 1
        self.nx, self.ny = int((x1 - x0 + 2) / RES) + 1, int((y1 - y0 + 2) / RES) + 1
        xs = self.x0 + np.arange(self.nx) * RES
        ys = self.y0 + np.arange(self.ny) * RES
        self.X, self.Y = np.meshgrid(xs, ys)          # [iy, ix]
        self.items = self._collect()

    def _collect(self):
        """[(net, layer_set, shapely geometry of the copper)]"""
        items = []
        for fp in self.b.GetFootprints():
            for p in fp.Pads():
                net = p.GetNetname()
                for L in LAYERS:
                    if p.IsOnLayer(L):
                        items.append((net, L, pad_poly(p, L)))
                if p.GetDrillSize().x > 0 and not p.GetNetname():
                    pass
        for t in self.b.GetTracks():
            net = t.GetNetname()
            if t.GetClass() == "PCB_VIA":
                c = Point(*dev(t.GetPosition())).buffer(MM_(t.GetWidth()) / 2, 16)
                for L in LAYERS:
                    items.append((net, L, c))
            else:
                g = LineString([dev(t.GetStart()), dev(t.GetEnd())]).buffer(MM_(t.GetWidth()) / 2, 8)
                items.append((net, t.GetLayer(), g))
        return items

    def blocked(self, net, layer, inflate):
        """Boolean grid of cells a track centre (or via centre) of `net` may NOT occupy."""
        m = np.zeros((self.ny, self.nx), dtype=bool)
        geoms = [g for (n, L, g) in self.items if L == layer and n != net]
        edge = self.board_poly.buffer(-(EDGE + inflate - CLR))      # inside the board, away from the edge
        inside = shapely.contains_xy(edge, self.X, self.Y)
        m |= ~inside
        for g in geoms:
            gb = g.buffer(inflate, 8)
            x0, y0, x1, y1 = gb.bounds
            i0, i1 = max(0, int((x0 - self.x0) / RES)), min(self.nx, int((x1 - self.x0) / RES) + 2)
            j0, j1 = max(0, int((y0 - self.y0) / RES)), min(self.ny, int((y1 - self.y0) / RES) + 2)
            if i0 >= i1 or j0 >= j1:
                continue
            m[j0:j1, i0:i1] |= shapely.contains_xy(gb, self.X[j0:j1, i0:i1], self.Y[j0:j1, i0:i1])
        return m

    def cell(self, x, y):
        return int(round((y - self.y0) / RES)), int(round((x - self.x0) / RES))

    def xy(self, j, i):
        return self.x0 + i * RES, self.y0 + j * RES


def MM_(v):
    return pcbnew.ToMM(v)


def astar(grid, blk, via_ok, starts, goals, via_cost=25.0):
    """starts/goals: lists of (layer_index, j, i).  8-connected moves, layer change = via."""
    goal_set = set(goals)
    gj = np.mean([g[1] for g in goals])
    gi = np.mean([g[2] for g in goals])
    h = lambda j, i: math.hypot(j - gj, i - gi)
    openq = []
    best = {}
    for s in starts:
        best[s] = 0.0
        heapq.heappush(openq, (h(s[1], s[2]), 0.0, s, None))
    came = {}
    moves = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
             (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
    n = 0
    while openq:
        f, g, s, parent = heapq.heappop(openq)
        if s in came:
            continue
        came[s] = parent
        n += 1
        if s in goal_set:
            path = [s]
            while came[path[-1]] is not None:
                path.append(came[path[-1]])
            return path[::-1], n
        if n > 3_000_000:
            break
        L, j, i = s
        for dj, di, c in moves:
            jj, ii = j + dj, i + di
            if not (0 <= jj < grid.ny and 0 <= ii < grid.nx) or blk[L][jj, ii]:
                continue
            t = (L, jj, ii)
            ng = g + c
            if ng < best.get(t, 1e18):
                best[t] = ng
                heapq.heappush(openq, (ng + h(jj, ii), ng, t, s))
        if via_ok[j, i]:
            t = (1 - L, j, i)
            if not blk[1 - L][j, i]:
                ng = g + via_cost
                if ng < best.get(t, 1e18):
                    best[t] = ng
                    heapq.heappush(openq, (ng + h(j, i), ng, t, s))
    return None, n


def add_path(board, grid, path, net, width):
    """Turn a grid path into tracks (merged straight runs) and vias."""
    ni = board.FindNet(net)
    n_tr = n_via = 0
    seg_start = path[0]
    prev = path[0]
    prev_dir = None
    def emit(a, b):
        nonlocal n_tr
        if a[1:] == b[1:]:
            return
        t = pcbnew.PCB_TRACK(board)
        t.SetStart(kpt(*grid.xy(a[1], a[2])))
        t.SetEnd(kpt(*grid.xy(b[1], b[2])))
        t.SetWidth(MM(width))
        t.SetLayer(LAYERS[a[0]])
        t.SetNet(ni)
        board.Add(t)
        n_tr += 1
    for s in path[1:]:
        if s[0] != prev[0]:                      # layer change: via
            emit(seg_start, prev)
            v = pcbnew.PCB_VIA(board)
            v.SetPosition(kpt(*grid.xy(prev[1], prev[2])))
            v.SetWidth(MM(VIA_D))
            v.SetDrill(MM(VIA_DRILL))
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetNet(ni)
            board.Add(v)
            n_via += 1
            seg_start, prev, prev_dir = s, s, None
            continue
        d = (s[1] - prev[1], s[2] - prev[2])
        if prev_dir is not None and d != prev_dir:
            emit(seg_start, prev)
            seg_start = prev
        prev_dir = d
        prev = s
    emit(seg_start, prev)
    return n_tr, n_via


def open_pairs(drc_text):
    """Unconnected item pairs from a DRC report: [(net, (x, y, desc), (x, y, desc))]."""
    out = []
    lines = drc_text.splitlines()
    i = 0
    while i < len(lines):
        if lines[i].startswith("[unconnected_items]"):
            items = []
            j = i + 1
            while j < len(lines) and not lines[j].startswith("["):
                m = re.search(r"@\(([-0-9.]+) mm, ([-0-9.]+) mm\): (.*)", lines[j])
                if m:
                    items.append((float(m.group(1)) - 110.0, 100.0 - float(m.group(2)), m.group(3)))
                j += 1
            if len(items) == 2:
                net = re.search(r"\[([^\]]+)\]", items[0][2]).group(1)
                out.append((net, items[0], items[1]))
            i = j
        else:
            i += 1
    return out


def endpoints(grid, board, item):
    """Grid cells (layer, j, i) for a DRC item: the pad or the track's ends."""
    x, y, desc = item
    cells = []
    m = re.match(r"(?:PTH )?[Pp]ad (\S+) \[([^\]]+)\] of (\S+)", desc)
    if m:
        fp = board.FindFootprintByReference(m.group(3))
        for p in fp.Pads():
            if p.GetNumber() == m.group(1):
                px, py = dev(p.GetPosition())
                for k, L in enumerate(LAYERS):
                    if p.IsOnLayer(L):
                        cells.append((k, *grid.cell(px, py)))
        return cells
    if desc.startswith("Track"):
        best = None
        for t in board.GetTracks():
            if t.GetClass() == "PCB_VIA":
                continue
            for e in (t.GetStart(), t.GetEnd()):
                ex, ey = dev(e)
                d = math.hypot(ex - x, ey - y)
                if best is None or d < best[0]:
                    best = (d, t, ex, ey)
        _, t, ex, ey = best
        k = 0 if t.GetLayer() == pcbnew.F_Cu else 1
        return [(k, *grid.cell(ex, ey))]
    return []


def route_open(board, drc_text, widths):
    pairs = [p for p in open_pairs(drc_text) if p[0] != "GND"]
    done = []
    for net, a, b in pairs:
        grid = Grid(board)
        w = widths.get(net, 0.25)
        infl = CLR + w / 2
        blk = [grid.blocked(net, L, infl) for L in LAYERS]
        via_blk = grid.blocked(net, pcbnew.F_Cu, CLR + VIA_D / 2) | grid.blocked(net, pcbnew.B_Cu, CLR + VIA_D / 2)
        s, g = endpoints(grid, board, a), endpoints(grid, board, b)
        for (L, j, i) in s + g:                  # the pads themselves are free for their own net
            blk[L][j, i] = False
        path, n = astar(grid, blk, ~via_blk, s, g)
        if path is None:
            done.append((net, "FAILED", n))
            continue
        done.append((net, *add_path(board, grid, path, net, w), n))
    return done


def stitch_gnd(board, pitch=2.5):
    grid = Grid(board)
    via_blk = grid.blocked("GND", pcbnew.F_Cu, CLR + VIA_D / 2) | grid.blocked("GND", pcbnew.B_Cu, CLR + VIA_D / 2)
    ni = board.FindNet("GND")
    placed = []
    def put(x, y):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(kpt(x, y))
        v.SetWidth(MM(VIA_D))
        v.SetDrill(MM(VIA_DRILL))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(ni)
        board.Add(v)
        placed.append((x, y))
    # a via beside every GND SMD pad (within 1.6 mm), then a stitching grid
    for fp in board.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname() != "GND" or p.GetDrillSize().x > 0:
                continue
            px, py = dev(p.GetPosition())
            found = False
            for r in np.arange(0.8, 1.7, 0.1):
                for a in np.linspace(0, 2 * np.pi, 24, endpoint=False):
                    x, y = px + r * math.cos(a), py + r * math.sin(a)
                    j, i = grid.cell(x, y)
                    if 0 <= j < grid.ny and 0 <= i < grid.nx and not via_blk[j, i] and \
                            all(math.hypot(x - q[0], y - q[1]) > VIA_D + CLR for q in placed):
                        put(x, y)
                        found = True
                        break
                if found:
                    break
    x0, y0, x1, y1 = grid.board_poly.bounds
    for x in np.arange(x0 + 1, x1, pitch):
        for y in np.arange(y0 + 1, y1, pitch):
            j, i = grid.cell(x, y)
            if not via_blk[j, i] and all(math.hypot(x - q[0], y - q[1]) > 1.5 for q in placed):
                put(x, y)
    return len(placed)


if __name__ == "__main__":
    b = pcbnew.LoadBoard(str(PCB))
    drc = (HERE / "kicad" / "drc.rpt").read_text()
    widths = {n: 0.45 for n in ("VBAT", "VBUS", "SW", "VOUT", "GND")}
    res = route_open(b, drc, widths)
    print("routed:", res)
    print("GND vias:", stitch_gnd(b))
    b.Save(str(PCB))
