"""
Finish the routing Freerouting leaves undone, and stitch the GND pours.

  1. Rip up tracks and vias that break the 0.3 mm board-edge rule (Freerouting keeps only
     its 0.2 mm clearance from the outline), then any stubs left dangling.
  2. Find every net that is still in pieces (pads, tracks and vias; the GND pours are left
     to step 3) and join the pieces with a two-layer grid A*: 0.1 mm grid, 8 directions,
     vias between layers, the net class's width (narrower if it does not fit), clear of
     every other net's copper by 0.2 mm and of the board edge by 0.3 mm.  When there is no
     free path, the search may cross other nets' tracks at a cost; the tracks it crosses are
     ripped up and their nets joined again in turn (rip-up and reroute).
  3. GND: a via beside every top GND pad that has none near it, and stitching vias on a
     2.5 mm grid wherever they fit, so every top-pour island joins the underside plane.

    python finish_route.py      (after make_pcb.py; then make_pcb.py --stage finish)

Personal prototype for bench evaluation - NOT a medical device.
"""
from __future__ import annotations

import heapq
import math
from collections import Counter, deque
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
CLR = 0.2                 # copper clearance, mm (all net classes)
EDGE = 0.3                # copper to board edge, mm
MARGIN = 0.03             # on top of every clearance: covers the 0.1 mm grid's rounding
VIA_D, VIA_DRILL = 0.6, 0.3
LAYERS = (pcbnew.F_Cu, pcbnew.B_Cu)
POWER = ("VBAT", "VBUS", "SW", "VOUT")
WIDTH = dict({n: 0.45 for n in POWER}, GND=0.3)   # net classes Power and Gnd; the rest 0.25
SOFT, SOFT_POWER = 40.0, 160.0              # cost per cell of crossing another net's track
MAX_RIPS = 3                                # a net ripped this often is no longer rippable


def mm(v):
    return pcbnew.ToMM(v)


_REMOVED = []


def drop(board, obj, txn=None):
    """Take an item off the board and keep its Python wrapper alive: if the wrapper of a
    removed item is garbage-collected, KiCad 7's SWIG layer breaks (later calls return raw
    SwigPyObjects)."""
    board.Remove(obj)
    _REMOVED.append(obj)
    if txn is not None:
        txn.removed.append(obj)


class Txn:
    """Board edits that can be undone: a rip-up whose ripped nets cannot all be joined
    again is rolled back as a whole."""

    def __init__(self, board):
        self.board, self.added, self.removed = board, [], []

    def add(self, obj):
        self.board.Add(obj)
        self.added.append(obj)

    def nets(self):
        return {o.GetNetname() for o in self.added + self.removed}

    def rollback(self):
        # compare the C++ objects, not the Python proxies (a snapshot makes new proxies)
        added = {int(o.this) for o in self.added}
        removed = {int(o.this) for o in self.removed}
        for o in self.added:
            if int(o.this) not in removed:
                self.board.Remove(o)
                _REMOVED.append(o)
        for o in self.removed:
            if int(o.this) not in added:
                self.board.Add(o)
        self.added, self.removed = [], []


def pad_poly(p, layer):
    ps = pcbnew.SHAPE_POLY_SET()
    p.TransformShapeToPolygon(ps, layer, 0, 200)
    out = []
    for i in range(ps.OutlineCount()):
        ol = ps.Outline(i)
        out.append(Polygon([dev(ol.CPoint(k)) for k in range(ol.PointCount())]))
    return unary_union(out)


# ----------------------------------------------------------------------------- copper
class Item:
    """One pad, track or via: geometry per layer index (0 = F.Cu, 1 = B.Cu) and its anchors."""
    __slots__ = ("obj", "kind", "net", "geoms", "anchors")

    def __init__(self, obj, kind, net, geoms, anchors):
        self.obj, self.kind, self.net, self.geoms, self.anchors = obj, kind, net, geoms, anchors


def snapshot(board):
    items = []
    for fp in board.GetFootprints():
        for p in fp.Pads():
            g = {k: pad_poly(p, L) for k, L in enumerate(LAYERS) if p.IsOnLayer(L)}
            if g:
                x, y = dev(p.GetPosition())
                items.append(Item(p, "pad", p.GetNetname(), g, [(k, x, y) for k in g]))
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            x, y = dev(t.GetPosition())
            c = Point(x, y).buffer(mm(t.GetWidth()) / 2, 16)
            items.append(Item(t, "via", t.GetNetname(), {0: c, 1: c}, [(0, x, y), (1, x, y)]))
        else:
            k = LAYERS.index(t.GetLayer())
            a, b = dev(t.GetStart()), dev(t.GetEnd())
            line = LineString([a, b]) if a != b else Point(a)
            items.append(Item(t, "track", t.GetNetname(), {k: line.buffer(mm(t.GetWidth()) / 2, 8)},
                              [(k, *a), (k, *b)]))
    return items


def touch(a, b):
    for k, x, y in a.anchors:
        if k in b.geoms and b.geoms[k].distance(Point(x, y)) < 1e-3:
            return True
    for k, x, y in b.anchors:
        if k in a.geoms and a.geoms[k].distance(Point(x, y)) < 1e-3:
            return True
    return False


def clusters(items, net):
    its = [it for it in items if it.net == net]
    parent = list(range(len(its)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    for i in range(len(its)):
        for j in range(i + 1, len(its)):
            if find(i) != find(j) and touch(its[i], its[j]):
                parent[find(i)] = find(j)
    groups = {}
    for i, it in enumerate(its):
        groups.setdefault(find(i), []).append(it)
    # only pieces with a pad count: a piece of bare track is a stub (prune_dangling)
    return [g for g in groups.values() if any(it.kind == "pad" for it in g)]


def open_nets(board):
    items = snapshot(board)
    nets = sorted({it.net for it in items if it.net and it.net != "GND"})
    return [n for n in nets if len(clusters(items, n)) > 1]


def pad_partition(items, net):
    """Which of the net's pads are joined together: a set of frozensets of (ref, pad)."""
    out = set()
    for piece in clusters(items, net):
        out.add(frozenset((it.obj.GetParentFootprint().Cast().GetReference(), it.obj.GetNumber())
                          for it in piece if it.kind == "pad"))
    return out


def dangling(it, others):
    """KiCad's test: an item covering both ends of a track counts only for the end nearer to
    its own anchors; a track is dangling unless both ends are covered."""
    if it.kind == "via":
        # a via must join copper on both layers (a pad, track or via that touches it there)
        layers = set()
        for o in others:
            if touch(it, o):
                pt = Point(it.anchors[0][1:])
                layers |= {k for k, g in o.geoms.items() if g.distance(pt) < VIA_D / 2 + 1e-3}
        return len(layers) < 2
    (k, ax, ay), (_, bx, by) = it.anchors
    if math.hypot(bx - ax, by - ay) < 0.01:          # a stub of no length joins nothing
        return True
    count = [0, 0]
    for o in others:
        if k not in o.geoms:
            continue
        ha = o.geoms[k].distance(Point(ax, ay)) < 1e-3
        hb = o.geoms[k].distance(Point(bx, by)) < 1e-3
        if ha and hb:
            da = min(math.hypot(ax - q[1], ay - q[2]) for q in o.anchors)
            db = min(math.hypot(bx - q[1], by - q[2]) for q in o.anchors)
            count[0 if da < db else 1] += 1
        elif ha or hb:
            count[0 if ha else 1] += 1
    return not (count[0] and count[1])


def prune_dangling(board, txn=None):
    """Remove dangling tracks and vias (KiCad's test) whose removal leaves the net's pads
    joined exactly as before, until none is left."""
    removed = 0
    while True:
        items = snapshot(board)
        by_net = {}
        for it in items:
            by_net.setdefault(it.net, []).append(it)
        dead = None
        for net, its in by_net.items():
            if not net or net == "GND":
                continue
            base = None
            for it in its:
                if it.kind == "pad" or not dangling(it, [o for o in its if o is not it]):
                    continue
                rest = [o for o in its if o is not it]
                base = base if base is not None else pad_partition(its, net)
                if pad_partition(rest, net) == base:
                    dead = it
                    break
            if dead is not None:
                break
        if dead is None:
            return removed
        drop(board, dead.obj, txn)
        removed += 1


# ----------------------------------------------------------------------------- grid
class Grid:
    def __init__(self, board):
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
        self.X, self.Y = np.meshgrid(xs, ys)          # [j, i]
        self._edge = {}

    def edge(self, half):
        """Cells closer to the board edge than EDGE + half (half = the copper's half width)."""
        key = round(half, 4)
        if key not in self._edge:
            inner = self.board_poly.buffer(-(EDGE + half + MARGIN))
            self._edge[key] = ~shapely.contains_xy(inner, self.X, self.Y)
        return self._edge[key].copy()

    def mask(self, geoms, inflate):
        m = np.zeros((self.ny, self.nx), dtype=bool)
        for g in geoms:
            gb = g.buffer(inflate, 8)
            x0, y0, x1, y1 = gb.bounds
            i0, i1 = max(0, int((x0 - self.x0) / RES)), min(self.nx, int((x1 - self.x0) / RES) + 2)
            j0, j1 = max(0, int((y0 - self.y0) / RES)), min(self.ny, int((y1 - self.y0) / RES) + 2)
            if i0 < i1 and j0 < j1:
                m[j0:j1, i0:i1] |= shapely.contains_xy(gb, self.X[j0:j1, i0:i1], self.Y[j0:j1, i0:i1])
        return m

    def cell(self, x, y):
        return int(round((y - self.y0) / RES)), int(round((x - self.x0) / RES))

    def xy(self, j, i):
        return float(self.x0 + i * RES), float(self.y0 + j * RES)

    def cells_of(self, piece):
        """Grid cells (layer, j, i) a path may start or end on: pad areas, track ends, vias."""
        out = set()
        for it in piece:
            if it.kind == "track":
                # only at its ends: a path joined to the middle of a track would leave that
                # track's dangling end impossible to prune
                for k, x, y in it.anchors:
                    out.add((k, *self.cell(x, y)))
            elif it.kind == "via":
                for k, x, y in it.anchors:
                    out.add((k, *self.cell(x, y)))
            else:
                for k, g in it.geoms.items():
                    core = g.buffer(-0.05)
                    x0, y0, x1, y1 = g.bounds
                    for x in np.arange(x0, x1 + RES, RES):
                        for y in np.arange(y0, y1 + RES, RES):
                            j, i = self.cell(x, y)
                            if core.contains(Point(*self.xy(j, i))):
                                out.add((k, j, i))
                    x, y = dev(it.obj.GetPosition())
                    out.add((k, *self.cell(x, y)))
        return {c for c in out if 0 <= c[1] < self.ny and 0 <= c[2] < self.nx}


# ----------------------------------------------------------------------------- search
MOVES = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
         (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]


def astar(grid, blk, cost, via_ok, via_cost, starts, goals, limit=4_000_000):
    """blk[k]: cells a track centre may not use; cost[k]: extra cost per cell (or None);
    via_ok: cells a via may use; via_cost: extra cost there (or None)."""
    goal_set = set(goals)
    gj0, gj1 = min(g[1] for g in goals), max(g[1] for g in goals)
    gi0, gi1 = min(g[2] for g in goals), max(g[2] for g in goals)

    def h(j, i):
        dj = gj0 - j if j < gj0 else (j - gj1 if j > gj1 else 0)
        di = gi0 - i if i < gi0 else (i - gi1 if i > gi1 else 0)
        return math.hypot(dj, di)
    openq, best, came = [], {}, {}
    for s in starts:
        best[s] = 0.0
        heapq.heappush(openq, (h(s[1], s[2]), 0.0, s, None))
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
        if n > limit:
            break
        L, j, i = s
        for dj, di, c in MOVES:
            jj, ii = j + dj, i + di
            if not (0 <= jj < grid.ny and 0 <= ii < grid.nx) or blk[L][jj, ii]:
                continue
            t = (L, jj, ii)
            ng = g + c * (1.0 + (cost[L][jj, ii] if cost is not None else 0.0))
            if ng < best.get(t, 1e18):
                best[t] = ng
                heapq.heappush(openq, (ng + h(jj, ii), ng, t, s))
        if via_ok[j, i]:
            t = (1 - L, j, i)
            if not blk[1 - L][j, i]:
                ng = g + 25.0 + (via_cost[j, i] if via_cost is not None else 0.0)
                if ng < best.get(t, 1e18):
                    best[t] = ng
                    heapq.heappush(openq, (ng + h(j, i), ng, t, s))
    return None, n


class Clearance:
    """Exact checks for a straight track segment of width w on layer k: clear of the given
    other-net copper by CLR and of the board edge by EDGE."""

    def __init__(self, grid, others, w):
        self.need = CLR + w / 2 + 0.002
        self.inner = grid.board_poly.buffer(-(EDGE + w / 2 + 0.002))
        shapely.prepare(self.inner)
        self.geoms = {k: [it.geoms[k] for it in others if k in it.geoms] for k in (0, 1)}
        self.tree = {k: shapely.STRtree(self.geoms[k]) for k in (0, 1)}

    def ok(self, k, a, b):
        seg = LineString([a, b])
        if not self.inner.contains(seg):
            return False
        return len(self.tree[k].query(seg, predicate="dwithin", distance=self.need)) == 0


def add_path(board, grid, path, net, width, clear=None, own=None, txn=None):
    """Turn a grid path into tracks and vias.  Each layer run is pulled taut where `clear`
    allows (straight segments between path points that keep the exact clearances), else its
    straight grid runs are merged; the ends of the path that lie inside the net's own copper
    (`own`: per-layer geometry) are trimmed, so no stub is left inside a pad or via."""
    ni = board.FindNet(net)
    runs, vias = [], []
    k, pts = path[0][0], [grid.xy(*path[0][1:])]
    for s in path[1:]:
        if s[0] != k:
            runs.append([k, pts])
            vias.append(pts[-1])
            k, pts = s[0], [grid.xy(*s[1:])]
        else:
            pts.append(grid.xy(*s[1:]))
    runs.append([k, pts])

    def inside(k, q):
        return own is not None and k in own and own[k].contains(Point(q))
    k, pts = runs[0]
    while len(pts) > 1 and inside(k, pts[0]) and inside(k, pts[1]):
        pts.pop(0)
    k, pts = runs[-1]
    while len(pts) > 1 and inside(k, pts[-1]) and inside(k, pts[-2]):
        pts.pop()
    n_tr = 0
    for k, pts in runs:
        if clear is not None:
            out, i = [pts[0]], 0
            while i < len(pts) - 1:
                j = i + 1
                while j + 1 < len(pts) and clear.ok(k, pts[i], pts[j + 1]):
                    j += 1
                out.append(pts[j])
                i = j
        else:
            out = [pts[0]]
            for q, r in zip(pts[1:-1], pts[2:]):
                a = out[-1]
                if abs((q[0] - a[0]) * (r[1] - q[1]) - (q[1] - a[1]) * (r[0] - q[0])) > 1e-9:
                    out.append(q)
            out.append(pts[-1])
        for a, b in zip(out[:-1], out[1:]):
            if math.hypot(b[0] - a[0], b[1] - a[1]) < 1e-6:
                continue
            t = pcbnew.PCB_TRACK(board)
            t.SetStart(kpt(*a))
            t.SetEnd(kpt(*b))
            t.SetWidth(MM(width))
            t.SetLayer(LAYERS[k])
            t.SetNet(ni)
            txn.add(t) if txn is not None else board.Add(t)
            n_tr += 1
    for q in vias:
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(kpt(*q))
        v.SetWidth(MM(VIA_D))
        v.SetDrill(MM(VIA_DRILL))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(ni)
        txn.add(v) if txn is not None else board.Add(v)
    return n_tr, len(vias)


def own_copper(items, net):
    return {k: unary_union([it.geoms[k].buffer(-0.01) for it in items if it.net == net and k in it.geoms])
            for k in (0, 1)}


def join(board, grid, items, net, pieces, rip_counts, txn, locked=()):
    """Join the first piece of `net` to any other.  Returns (info, ripped nets) or None."""
    a, rest = pieces[0], [it for p in pieces[1:] for it in p]
    return connect(board, grid, items, net, grid.cells_of(a), grid.cells_of(rest), rip_counts, txn, locked)


def connect(board, grid, items, net, starts, goals, rip_counts, txn, locked=()):
    """Route `net` from any start cell to any goal cell; rip up other nets' tracks if there is
    no free path (never GND's, nor those of the nets in `locked`).  Returns (info, ripped
    nets) or None."""
    other = [it for it in items if it.net != net]
    pads = [it for it in other if it.kind == "pad"]
    wires = [it for it in other if it.kind != "pad"]
    rippable = [it for it in wires if it.net != "GND" and it.net not in locked and rip_counts[it.net] < MAX_RIPS]
    rip_ids = {id(it) for it in rippable}
    fixed = [it for it in wires if id(it) not in rip_ids]
    w0 = WIDTH.get(net, 0.25)
    via_inf = CLR + VIA_D / 2 + MARGIN
    # vias: never in a pad (any net), 0.25 mm hole to hole from every via (own net too),
    # clear of fixed copper; rippable copper is soft
    via_hard = grid.edge(VIA_D / 2)
    via_hard |= grid.mask([it.geoms[0] for it in items if it.kind == "via"], 0.25 + MARGIN)
    for k in (0, 1):
        via_hard |= grid.mask([it.geoms[k] for it in items if it.kind == "pad" and k in it.geoms], VIA_D / 2 + 0.05)
        via_hard |= grid.mask([it.geoms[k] for it in pads + fixed if k in it.geoms], via_inf)
    own = own_copper(items, net)
    via_soft = grid.mask([g for it in rippable for g in it.geoms.values()], via_inf)
    for w in dict.fromkeys(x for x in (w0, 0.3, 0.25) if x <= w0):     # each width once
        inf = CLR + w / 2 + MARGIN
        blk = [grid.edge(w / 2) | grid.mask([it.geoms[k] for it in other if k in it.geoms], inf) for k in (0, 1)]
        for (k, j, i) in starts | goals:
            blk[k][j, i] = False
        path, n = astar(grid, blk, None, ~(via_hard | via_soft), None, list(starts), list(goals))
        if path is not None:
            r = add_path(board, grid, path, net, w, Clearance(grid, other, w), own, txn)
            return dict(net=net, width=w, tracks=r[0], vias=r[1]), []
    if not rippable:
        return None
    # relaxed: other nets' tracks may be crossed at a cost, then ripped up
    w = min(0.25, w0)
    inf = CLR + w / 2 + MARGIN
    hard = [grid.edge(w / 2) | grid.mask([it.geoms[k] for it in pads + fixed if k in it.geoms], inf) for k in (0, 1)]
    cost = [np.zeros((grid.ny, grid.nx)) for _ in (0, 1)]
    for it in rippable:
        c = SOFT_POWER if it.net in POWER else SOFT
        for k, g in it.geoms.items():
            cost[k] = np.maximum(cost[k], grid.mask([g], inf) * c)
    for (k, j, i) in starts | goals:
        hard[k][j, i] = False
    path, n = astar(grid, hard, cost, ~via_hard, via_soft * SOFT * 3, list(starts), list(goals))
    if path is None:
        return None
    pts = {0: [], 1: []}
    for k, j, i in path:
        pts[k].append(grid.xy(j, i))
    via_pts = [grid.xy(p[1], p[2]) for p, q in zip(path[:-1], path[1:]) if p[0] != q[0]]
    ripped = []
    for it in rippable:
        hit = False
        for k, g in it.geoms.items():
            if pts[k]:
                xs, ys = np.array(pts[k]).T
                hit = hit or bool(shapely.contains_xy(g.buffer(inf, 8), xs, ys).any())
            if via_pts:
                xs, ys = np.array(via_pts).T
                hit = hit or bool(shapely.contains_xy(g.buffer(via_inf, 8), xs, ys).any())
        if hit:
            ripped.append(it)
    for it in ripped:
        drop(board, it.obj, txn)
    gone = {id(it) for it in ripped}
    r = add_path(board, grid, path, net, w, Clearance(grid, [it for it in other if id(it) not in gone], w), own, txn)
    return dict(net=net, width=w, tracks=r[0], vias=r[1]), sorted({it.net for it in ripped})


def edge_violators(board, grid):
    """Tracks and vias closer to the board edge than EDGE."""
    edge = grid.board_poly.boundary
    bad = []
    for t in board.GetTracks():
        if t.GetClass() == "PCB_VIA":
            d = edge.distance(Point(dev(t.GetPosition()))) - mm(t.GetWidth()) / 2
        else:
            d = edge.distance(LineString([dev(t.GetStart()), dev(t.GetEnd())])) - mm(t.GetWidth()) / 2
        if d < EDGE - 1e-3:
            bad.append((t, t.GetNetname(), round(d, 3)))
    return bad


def join_net(board, grid, net, rips, log, txn, stack=()):
    """Join all pieces of `net`; nets ripped up on the way are joined again in turn (never
    ripping a net further up the stack).  False if anything could not be joined."""
    stack = stack + (net,)
    pad = "  " * len(stack)
    for _ in range(16):
        items = snapshot(board)
        pieces = clusters(items, net)
        if len(pieces) < 2:
            return True
        res = join(board, grid, items, net, pieces, rips, txn, locked=stack)
        if res is None:
            log(f"{pad}{net}: no path ({len(pieces)} pieces)")
            return False
        info, ripped = res
        log(f"{pad}{net}: {info['tracks']} tracks, {info['vias']} vias, {info['width']} mm"
            + (f"; ripped {ripped}" if ripped else ""))
        for n in ripped:
            rips[n] += 1
            if len(stack) > 4 or not join_net(board, grid, n, rips, log, txn, stack):
                return False
    return len(clusters(snapshot(board), net)) < 2        # the last join may have finished it


def settle(board, grid, txn, rips, log):
    """After a transaction: every net it touched must be in one piece; join any that are
    not, else roll the transaction back.  True if it stands."""
    for _ in range(3):
        items = snapshot(board)
        broken = [n for n in sorted(txn.nets()) if n and n != "GND" and len(clusters(items, n)) > 1]
        if not broken:
            return True
        if not all(join_net(board, grid, n, rips, log, txn) for n in broken):
            break
    txn.rollback()
    return False


def join_all(board, grid, nets, rips, log=print):
    done, failed = [], []
    for net in nets:
        txn = Txn(board)
        ok = join_net(board, grid, net, rips, log, txn) and settle(board, grid, txn, rips, log)
        if not ok:
            txn.rollback()
            log(f"  {net}: FAILED, rolled back")
            failed.append(net)
        else:
            done.append(net)
            prune_dangling(board)
    return done, failed


def clearance_violators(board):
    """Tracks and vias closer than CLR to another net's copper (Freerouting rounds some to
    0.1994 mm).  Of each pair the track or via is taken, not GND if the other one can be."""
    items = snapshot(board)
    bad = {}
    for k in (0, 1):
        on = [it for it in items if k in it.geoms]
        tree = shapely.STRtree([it.geoms[k] for it in on])
        for a in on:
            if a.kind == "pad":
                continue
            for n in tree.query(a.geoms[k], predicate="dwithin", distance=CLR - 1e-4):
                b = on[int(n)]
                if b is a or b.net == a.net:
                    continue
                d = a.geoms[k].distance(b.geoms[k])
                if d >= CLR - 1e-4:
                    continue
                pick = a if (a.net != "GND" or b.kind == "pad" or b.net == "GND") else b
                if pick.kind != "pad":
                    bad[id(pick.obj)] = (pick.obj, pick.net, round(d, 4))
    return list(bad.values())


def finish(board, rips, log=print):
    grid = Grid(board)
    for t, net, d in edge_violators(board, grid):
        log(f"  rip {net} {'via' if t.GetClass() == 'PCB_VIA' else 'track'}: {d} mm from the edge")
        drop(board, t)
    for t, net, d in clearance_violators(board):
        log(f"  rip {net} {'via' if t.GetClass() == 'PCB_VIA' else 'track'}: {d} mm from other copper")
        drop(board, t)
    log(f"  pruned {prune_dangling(board)} dangling pieces")
    queue = open_nets(board)
    log(f"  open: {queue}")
    done, failed = join_all(board, grid, queue, rips, log)
    log(f"  pruned {prune_dangling(board)} dangling pieces")
    return done, failed


# ----------------------------------------------------------------------------- GND
_FILLERS = []


def gnd_fills(board):
    """Fill the pours and return the GND fill polygons as [(layer index, Polygon)]."""
    f = pcbnew.ZONE_FILLER(board)
    _FILLERS.append(f)                       # keep the filler alive (SWIG lifetime)
    f.Fill(board.Zones())
    out = []
    for z in board.Zones():
        if z.GetNetname() != "GND":
            continue
        for k, L in enumerate(LAYERS):
            if not z.IsOnLayer(L):
                continue
            ps = z.GetFilledPolysList(L)
            for i in range(ps.OutlineCount()):
                ol = ps.Outline(i)
                holes = [[dev(ps.Hole(i, h).CPoint(m)) for m in range(ps.Hole(i, h).PointCount())]
                         for h in range(ps.HoleCount(i))]
                out.append((k, Polygon([dev(ol.CPoint(m)) for m in range(ol.PointCount())], holes).buffer(0)))
    return out


def gnd_groups(board, polys):
    """Connectivity of the GND copper: nodes are the fill polygons and the GND pads, tracks
    and vias; an item joins the polygons it touches on its layers and the items it touches.
    Returns (polygon in the main group?, items not in it), the main group being the one
    with the largest underside polygon."""
    items = [it for it in snapshot(board) if it.net == "GND"]
    n_p = len(polys)
    parent = list(range(n_p + len(items)))

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[ra] = rb
    tree = shapely.STRtree([p for _, p in polys])
    for m, it in enumerate(items):
        for k, g in it.geoms.items():
            probe = Point(*it.anchors[0][1:]) if it.kind == "via" else g.buffer(0.02)
            for n in tree.query(probe, predicate="intersects"):
                if polys[n][0] == k:
                    union(n_p + m, int(n))
    itree = shapely.STRtree([unary_union(list(it.geoms.values())).buffer(0.01) for it in items])
    for m, it in enumerate(items):
        for q in itree.query(unary_union(list(it.geoms.values())), predicate="intersects"):
            if q > m and touch(it, items[q]):
                union(n_p + m, n_p + int(q))
    main = find(max(range(n_p), key=lambda n: (polys[n][0] == 1, polys[n][1].area)))
    return [find(n) == main for n in range(n_p)], [it for m, it in enumerate(items) if find(n_p + m) != main]


def poly_cells(grid, poly, layer, half):
    """Grid cells (layer, j, i) a track of half-width `half` may start or end on inside a
    fill polygon."""
    r = poly.buffer(-(half + 0.02))
    if r.is_empty:
        r = poly.buffer(-0.01)
    if r.is_empty:
        return set()
    x0, y0, x1, y1 = r.bounds
    j0, i0 = grid.cell(x0, y0)
    j1, i1 = grid.cell(x1, y1)
    j0, i0, j1, i1 = max(j0, 0), max(i0, 0), min(j1 + 1, grid.ny), min(i1 + 1, grid.nx)
    ok = shapely.contains_xy(r, grid.X[j0:j1, i0:i1], grid.Y[j0:j1, i0:i1])
    jj, ii = np.nonzero(ok)
    return {(layer, int(j0 + a), int(i0 + b)) for a, b in zip(jj, ii)}


def stitch_gnd(board, rips, pitch=6.0, rounds=12, log=print):
    """Join every GND pour island to the main plane with a via, then add sparse stitching
    vias where both layers' main pours overlap.  Returns (vias, island tracks, not joined)."""
    grid = Grid(board)
    ni = board.FindNet("GND")
    placed = []

    def put(x, y):
        v = pcbnew.PCB_VIA(board)
        v.SetPosition(kpt(float(x), float(y)))
        v.SetWidth(MM(VIA_D))
        v.SetDrill(MM(VIA_DRILL))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
        v.SetNet(ni)
        board.Add(v)
        placed.append((float(x), float(y)))

    def spots(region, items):
        """Free via centres inside a region: off every pad, apart from other vias, inside
        the edge rule.  The fills already keep 0.25 mm from other nets' copper, so a via
        whose pad lies inside the fill is clear of them."""
        pads = unary_union([g for it in items if it.kind == "pad" for g in it.geoms.values()])
        vias = unary_union([Point(*it.anchors[0][1:]).buffer(VIA_D + CLR) for it in items if it.kind == "via"]
                           + [Point(*q).buffer(VIA_D + CLR) for q in placed])
        inner = grid.board_poly.buffer(-(EDGE + VIA_D / 2 + MARGIN))
        r = region.buffer(-(VIA_D / 2 + 0.05)).intersection(inner).difference(pads.buffer(VIA_D / 2 + 0.1)).difference(vias)
        if r.is_empty:
            return []
        x0, y0, x1, y1 = r.bounds
        xs, ys = np.meshgrid(np.arange(x0, x1 + RES, RES), np.arange(y0, y1 + RES, RES))
        ok = shapely.contains_xy(r, xs, ys)
        pts = list(zip(xs[ok], ys[ok]))
        c = r.representative_point()
        pts.sort(key=lambda q: math.hypot(q[0] - c.x, q[1] - c.y))
        return pts
    left, tracks = [], 0
    for _ in range(rounds):
        polys = gnd_fills(board)
        joined, lost = gnd_groups(board, polys)
        orphans = [n for n in range(len(polys)) if not joined[n]]
        lost_pads = [it for it in lost if it.kind == "pad"]
        if not orphans and not lost_pads:
            left = []
            break
        items = snapshot(board)
        main = {k: unary_union([p for n, (kk, p) in enumerate(polys) if kk == k and joined[n]]) for k in (0, 1)}
        left, progress = [], False
        # a GND pad with no way to the main pours (its track was ripped, or it sits in no
        # pour): route it like an island
        for it in lost_pads:
            starts = grid.cells_of([it])
            goals = poly_cells(grid, main[0], 0, 0.15) | poly_cells(grid, main[1], 1, 0.15)
            txn = Txn(board)
            res = connect(board, grid, items, "GND", starts, goals, rips, txn, locked=("GND",)) if goals else None
            ok = res is not None
            if ok:
                for rn in res[1]:                    # count the rip-ups, as for islands below
                    rips[rn] += 1
                ok = all(join_net(board, grid, rn, rips, log, txn, ("GND",)) for rn in res[1]) \
                    and settle(board, grid, txn, rips, log)
            if ok:
                log(f"  GND pad {it.obj.GetParentFootprint().Cast().GetReference()}.{it.obj.GetNumber()}: "
                    f"{res[0]['tracks']} tracks, {res[0]['vias']} vias" + (f"; ripped {res[1]}" if res[1] else ""))
                tracks += 1
                progress = True
                break
            txn.rollback()
        if progress:
            continue
        for n in sorted(orphans, key=lambda n: -polys[n][1].area):
            k, p = polys[n]
            pts = spots(p.intersection(main[1 - k]), items)
            if pts:
                put(*pts[0])
                progress = True
            else:
                # no via fits: route GND from the island to the main pours, ripping up and
                # re-joining signal tracks if it must
                starts = poly_cells(grid, p, k, 0.125)
                goals = poly_cells(grid, main[0], 0, 0.125) | poly_cells(grid, main[1], 1, 0.125)
                txn = Txn(board)
                res = connect(board, grid, items, "GND", starts, goals, rips, txn, locked=("GND",)) \
                    if starts and goals else None
                ok = res is not None
                if ok:
                    info, ripped = res
                    log(f"  GND island {('F', 'B')[k]} {p.area:.1f} mm2 at "
                        f"{tuple(round(v, 1) for v in p.representative_point().coords[0])}: {info['tracks']} tracks, "
                        f"{info['vias']} vias, {info['width']} mm" + (f"; ripped {ripped}" if ripped else ""))
                    for rn in ripped:
                        rips[rn] += 1
                    ok = all(join_net(board, grid, rn, rips, log, txn, ("GND",)) for rn in ripped) and \
                        settle(board, grid, txn, rips, log)
                if not ok:
                    txn.rollback()
                    if res is not None:
                        log("    rolled back")
                    left.append((("F", "B")[k], round(p.area, 2), tuple(round(v, 1) for v in p.representative_point().coords[0])))
                    continue
                tracks += 1
                progress = True
                break                    # the pours change: fill again before the next one
        if not progress:
            break
    # sparse stitching where both main pours overlap
    polys = gnd_fills(board)
    joined, lost = gnd_groups(board, polys)
    both = unary_union([p for n, (k, p) in enumerate(polys) if k == 0 and joined[n]]).intersection(
        unary_union([p for n, (k, p) in enumerate(polys) if k == 1 and joined[n]]))
    items = snapshot(board)
    free = spots(both, items)
    x0, y0, x1, y1 = grid.board_poly.bounds
    for x in np.arange(x0 + pitch / 2, x1, pitch):
        for y in np.arange(y0 + pitch / 2, y1, pitch):
            near = [q for q in free if abs(q[0] - x) < pitch / 3 and abs(q[1] - y) < pitch / 3
                    and all(math.hypot(q[0] - a, q[1] - b) > 2.5 for a, b in placed)]
            if near:
                put(*min(near, key=lambda q: math.hypot(q[0] - x, q[1] - y)))
    polys = gnd_fills(board)
    joined, lost = gnd_groups(board, polys)
    # GND tracks and vias cut off from the main pours with no pad among them are leftovers
    stray = [it for it in lost if it.kind != "pad"]
    lost_pads = [it for it in lost if it.kind == "pad"]
    for it in stray:
        if not any(touch(it, q) for q in lost_pads):
            drop(board, it.obj)
    if stray:
        polys = gnd_fills(board)
        joined, lost = gnd_groups(board, polys)
    left = [(("F", "B")[k], round(p.area, 2), tuple(round(v, 1) for v in p.representative_point().coords[0]))
            for n, (k, p) in enumerate(polys) if not joined[n]]
    left += [(it.kind, it.obj.GetParentFootprint().Cast().GetReference() if it.kind == "pad" else "",
              tuple(round(v, 1) for v in it.anchors[0][1:])) for it in lost]
    return len(placed), tracks, left


if __name__ == "__main__":
    from make_pcb import project_file
    PRO = PCB.with_suffix(".kicad_pro")
    project_file(PRO)                       # rules and net classes, before the load
    b = pcbnew.LoadBoard(str(PCB))
    assert b.FindNet("VBAT").GetNetClassName() == "Power", "net classes not applied"
    rips = Counter()
    done, failed = finish(b, rips)
    print("joined:", len(done), "| failed:", failed or "none")
    n, tr, left = stitch_gnd(b, rips)
    print("GND vias:", n, "| island tracks:", tr, "| not joined:", left or "none")
    print("pruned:", prune_dangling(b), "| open nets:", open_nets(b) or "none")
    b.Save(str(PCB))
    project_file(PRO)
