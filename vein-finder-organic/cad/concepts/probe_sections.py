"""Plot key sections of an option's height fields (fast tuning before a full build)."""
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "stone"))
from options import OPTIONS, Z_PART
from organic import Stone
from matplotlib.path import Path as MP

def sections(key, out):
    st = Stone(OPTIONS[key], verbose=False)
    poly = MP(st.boundary)
    fig, ax = plt.subplots(2, 2, figsize=(13, 7))
    def line(p0, p1, n=600):
        t = np.linspace(0, 1, n)[:, None]
        P = (1 - t) * np.array(p0) + t * np.array(p1)
        inside = poly.contains_points(P, radius=-1e-3)
        return P, inside
    cases = [("centre line y=0", (-28, 0), (64, 0), 0), ("horn mid-line y=+21", (-27, 21), (64, 21), 0),
             ("cross-section x=0 (horns)", (0, -30), (0, 30), 1), ("cross-section x=36 (tail)", (36, -30), (36, 30), 1)]
    rep = {}
    for a, (title, p0, p1, axis) in zip(ax.ravel(), cases):
        P, ins = line(p0, p1)
        zt = np.full(len(P), np.nan); zb = np.full(len(P), np.nan)
        zt[ins], zb[ins] = st.probe(P[ins])
        xx = P[:, axis]
        a.fill_between(xx, zb, zt, color="0.75")
        a.plot(xx, zt, "k", lw=1); a.plot(xx, zb, "k", lw=1)
        a.axhline(Z_PART, color="tab:red", lw=0.8, ls="--", label="parting plane")
        a.set_title(title); a.set_aspect("equal"); a.grid(alpha=0.3); a.set_ylim(-2, 28)
        rep[title] = (np.nanmax(zt), np.nanmin(zb))
    fig.tight_layout(); fig.savefig(out, dpi=90)
    e = st.edge_report()
    print(key, {k: tuple(np.round(v, 2)) for k, v in rep.items()})
    print("edge radius r_e range %.1f-%.1f mm, Db %.1f-%.1f, rb %.1f-%.1f" % (e["r_e"].min(), e["r_e"].max(), e["Db"].min(), e["Db"].max(), e["rb"].min(), e["rb"].max()))

if __name__ == "__main__":
    sections(sys.argv[1], sys.argv[2])
