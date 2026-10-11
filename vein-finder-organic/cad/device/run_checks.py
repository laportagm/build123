"""Run checks.py on the cached BREP parts (build.py must have run)."""
import json
import sys
import time
from pathlib import Path

import build123d as bd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "render"))

import checks  # noqa: E402
from parts import Parts  # noqa: E402

if __name__ == "__main__":
    t = time.time()
    shapes = {p.stem: bd.import_brep(str(p)) for p in sorted((ROOT / "build" / "device" / "brep").glob("*.brep"))}
    pa = Parts(verbose=False)
    only = sys.argv[1:]
    if only:
        rep = {}
        for k in only:
            if k == "membrane":
                rep[k] = checks.membrane_force(pa)
            elif k == "magnets":
                rep[k] = checks.magnet_pull()
            elif k == "walls":
                rep[k] = checks.wall_map(pa)[0]
            elif k == "interference":
                rep[k] = checks.interference(shapes)
            elif k == "mass":
                rep[k] = checks.mass_budget(shapes, pa)
        print(json.dumps(rep, indent=1, default=float))
    else:
        print(json.dumps(checks.run(pa, shapes), indent=1, default=float))
    print("checks", round(time.time() - t, 1), "s")
