"""Final labelled figures: 300 m overview and 100 m zoom (and 44 m house close-up) for each visualization."""
import sys, json, numpy as np
sys.path.insert(0, sys.argv[1])
from common import *
from PIL import Image
import os

OUT = D + "/images"; os.makedirs(OUT, exist_ok=True)
G = load(); V = dict(np.load(D + "/derivs.npz")); ext = G["extent"]
dep = np.load(D + "/filldepth.npy")
CJ = json.load(open(D + "/candidates.json"))
C = CJ["candidates"]
lab = [dict(c, id=c["label"]) for c in C]
sext = (603969, 604569, 5232668, 5233268)
naip = np.array(Image.open(SCR + "/sat/naip_utm.jpg")); esri = np.array(Image.open(SCR + "/sat/esri_utm.jpg"))
hs = V["hs_multi"]

layers = {
    "hillshade_multidir": dict(a=hs, cmap="gray", lim=(0.47, 0.62), t="Multi-direction hillshade (6 az, 35° alt, z x2)"),
    "hillshade_315": dict(a=V["hs315"], cmap="gray", lim=(0.3, 0.9), t="Hillshade az 315° (z x2)"),
    "lrm2m": dict(a=V["lrm2"], cmap="RdBu_r", lim=(-0.12, 0.12), t="Local relief model, 2 m radius (m)"),
    "lrm5m": dict(a=V["lrm5"], cmap="RdBu_r", lim=(-0.25, 0.25), t="Local relief model, 5 m radius (m)"),
    "lrm10m": dict(a=V["lrm10"], cmap="RdBu_r", lim=(-0.4, 0.4), t="Local relief model, 10 m radius (m)"),
    "svf10m": dict(a=V["svf"], cmap="gray", lim=(0.93, 1.0), t="Sky-view factor (10 m, 16 dirs)"),
    "slope": dict(a=V["slope"], cmap="magma_r", lim=(0, 25), t="Slope (degrees)"),
    "filldepth": dict(a=dep, cmap="viridis", lim=(0, 0.3), t="Closed-depression depth from fill-sinks (m)"),
    "dem": dict(a=G["dem"], cmap="terrain", lim=(643.5, 650.0), t="Ground DEM, 0.5 m TIN (m NAVD88)"),
    "chm": dict(a=G["chm"], cmap="viridis", lim=(0, 18), t="Canopy height model (m above ground)"),
    "groundpts_per_m2": dict(a=G["gcnt1"], cmap="magma", lim=(0, 12), t="Ground points per 1 m cell", ext1=True),
    "naip": dict(img=naip, t="NAIP imagery"),
    "esri": dict(img=esri, t="Esri World Imagery"),
}

def render(key, L, half, fname, cands, grid, lblsize):
    fig, ax = plt.subplots(figsize=(10, 10))
    if "img" in L:
        ax.imshow(L["img"], extent=sext)
    else:
        if key not in ("hillshade_multidir", "hillshade_315", "svf10m", "naip", "esri"):
            ax.imshow(hs, cmap="gray", extent=ext, vmin=0.3, vmax=1)
            alpha = 0.75
        else:
            alpha = 1
        im = ax.imshow(L["a"], cmap=L["cmap"], vmin=L["lim"][0], vmax=L["lim"][1], extent=ext, alpha=alpha, interpolation="nearest")
        cb = plt.colorbar(im, ax=ax, fraction=0.035, pad=0.01)
    decorate(ax, half, cands=cands, grid=grid, label_size=lblsize)
    ax.set_title(f"{L['t']} — {2*half:.0f} m view, grid {grid} m\nYellow = house footprint (panorama-derived, ±12 m abs.), cyan = foundation stones; "
                 "red = depression, green = mound, orange = linear", fontsize=9)
    plt.tight_layout(); plt.savefig(f"{OUT}/{fname}", dpi=110); plt.close()

ov = [c for c in lab if c["tier"] in ("A", "B")]
zm = [c for c in lab if c["tier"] in ("A", "B") and c["dist_m"] <= 75]
for k, L in layers.items():
    render(k, L, 150, f"overview300m_{k}.jpg", ov, 25, 7)
    render(k, L, 50, f"zoom100m_{k}.jpg", zm, 10, 9)
for k in ("hillshade_multidir", "lrm2m", "lrm5m", "filldepth", "chm", "esri"):
    render(k, layers[k], 22, f"house44m_{k}.jpg", zm, 5, 10)
print("ok")
