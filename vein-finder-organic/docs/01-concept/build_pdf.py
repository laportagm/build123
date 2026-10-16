"""Convert board renders to JPEG and print concept.html -> concept.pdf (+ PNG preview)."""
import glob
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
REN = HERE / "renders"


def jpegs():
    for png in sorted(REN.glob("*.png")):
        jpg = png.with_suffix(".jpg")
        Image.open(png).convert("RGB").save(jpg, quality=90, optimize=True, progressive=True)
        png.unlink()


def autocrop(img, margin=0.06, thresh=0.07, aspect=None, min_frac=0.004):
    """Crop to the object (difference from the border colour), then pad to `aspect` (w/h)."""
    import numpy as np
    a = np.asarray(img.convert("RGB"), dtype=np.float32) / 255.0
    border = np.concatenate([a[:4].reshape(-1, 3), a[-4:].reshape(-1, 3), a[:, :4].reshape(-1, 3), a[:, -4:].reshape(-1, 3)])
    bg = np.median(border, axis=0)
    m = np.abs(a - bg).max(axis=2) > thresh
    rows = np.where(m.mean(axis=1) > min_frac)[0]
    cols = np.where(m.mean(axis=0) > min_frac)[0]
    H, W = m.shape
    y0, y1, x0, x1 = rows.min(), rows.max(), cols.min(), cols.max()
    my, mx = int(margin * (y1 - y0)), int(margin * (x1 - x0))
    y0, y1, x0, x1 = max(0, y0 - my), min(H, y1 + my), max(0, x0 - mx), min(W, x1 + mx)
    if aspect:
        w, h = x1 - x0, y1 - y0
        if w / h < aspect:
            grow = int((aspect * h - w) / 2); x0, x1 = max(0, x0 - grow), min(W, x1 + grow)
        else:
            grow = int((w / aspect - h) / 2); y0, y1 = max(0, y0 - grow), min(H, y1 + grow)
    return img.crop((x0, y0, x1, y1))


def board_crops():
    out = REN / "board"
    out.mkdir(exist_ok=True)
    for jpg in sorted(REN.glob("*.jpg")):
        im = Image.open(jpg)
        n = jpg.stem
        if n.endswith("_side"):
            im = autocrop(im, margin=0.10, aspect=3.4)
        elif n.endswith("_plan"):
            im = autocrop(im.rotate(-90, expand=True), margin=0.08, aspect=1.62, thresh=0.16, min_frac=0.02)
        elif n.endswith("_hero") or n in ("A_hero_seam",):
            im = autocrop(im, margin=0.05, aspect=1.45)
        elif n == "A_context":
            im = autocrop(im, margin=0.02, aspect=1.62)
        im.convert("RGB").save(out / jpg.name, quality=88, optimize=True, progressive=True)


def chromium():
    c = glob.glob("/opt/pw-browsers/chromium-*/chrome-linux*/chrome")
    return c[0] if c else None


def pdf():
    with sync_playwright() as p:
        exe = chromium()
        b = p.chromium.launch(executable_path=exe) if exe else p.chromium.launch()
        pg = b.new_page(viewport={"width": 1587, "height": 1123})        # A3 @ 96 dpi
        pg.goto((HERE / "concept.html").as_uri())
        pg.wait_for_load_state("networkidle")
        pg.pdf(path=str(HERE / "concept.pdf"), width="420mm", height="297mm", print_background=True,
               margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        pg.set_viewport_size({"width": 1587, "height": 1123})
        png = HERE / "concept_preview.png"
        pg.screenshot(path=str(png), full_page=True, scale="device")
        b.close()
        Image.open(png).convert("RGB").save(HERE / "concept_preview.jpg", quality=88, optimize=True, progressive=True)
        png.unlink()


if __name__ == "__main__":
    jpegs()
    board_crops()
    pdf()
    print("wrote concept.pdf and concept_preview.jpg")
