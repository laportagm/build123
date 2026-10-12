"""Copy the CAD release files from build/ into docs/02-cad (renders as JPG, STEP zipped), and the
assembly renders into docs/05-build/figures."""
import shutil
import zipfile
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
B = ROOT / "build"

if __name__ == "__main__":
    (HERE / "renders").mkdir(exist_ok=True)
    build_figs = ROOT / "docs" / "05-build" / "figures"
    build_figs.mkdir(parents=True, exist_ok=True)
    for p in sorted((B / "render" / "cad").glob("*.png")):
        im = Image.open(p).convert("RGB")
        if p.stem.startswith("asm_"):                 # assembly steps: the build guide's figures
            im.save(build_figs / f"{p.stem}.jpg", quality=88, optimize=True)
            continue
        im.save(HERE / "renders" / f"{p.stem}.jpg", quality=90, optimize=True)
        if p.stem == "cad_exploded":
            im.save(build_figs / f"{p.stem}.jpg", quality=88, optimize=True)
    with zipfile.ZipFile(HERE / "step.zip", "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for n in ("top_shell", "sole", "seam_mask", "bridge", "assembly"):
            z.write(B / "device" / "step" / f"{n}.step", f"{n}.step")
    (HERE / "3mf").mkdir(exist_ok=True)
    for p in sorted((B / "device" / "3mf").glob("*.3mf")):
        shutil.copy2(p, HERE / "3mf" / p.name)
    (HERE / "pcb").mkdir(exist_ok=True)
    for n in ("pcb_edge_cuts.dxf", "layout.json"):
        shutil.copy2(B / "device" / n, HERE / "pcb" / n)
    for n in ("checks.json", "g2.json"):
        shutil.copy2(B / "device" / n, HERE / n)
    print("packaged ->", HERE)
