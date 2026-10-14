"""Score/filter raw candidates into a shortlist, add context flags, write candidates.json."""
import sys, json, numpy as np
sys.path.insert(0, sys.argv[1])
from common import *
from scipy import ndimage as ndi

G = load(); r = float(G["res"]); x0 = float(G["x0"]); y1 = float(G["y1"])
dem = np.where(np.isnan(G["dem"]), np.nanmean(G["dem"]), G["dem"])
sm = ndi.gaussian_filter(dem, 10 / r / 2)
dy, dx = np.gradient(sm, r); cslope = np.degrees(np.arctan(np.hypot(dx, dy)))
R = json.load(open(D + "/candidates_raw.json"))
C = R["candidates"]
def ij(c): return int((y1 - c["N"]) / r), int((c["E"] - x0) / r)
short = []
for c in C:
    i, j = ij(c)
    c["context_slope_deg_10m"] = round(float(cslope[i, j]), 1)
    c["terrace_elev_m"] = round(float(sm[i, j]), 2)
    flags = []
    if c["context_slope_deg_10m"] > 3.5: flags.append("on scarp/gully slope (likely natural erosion form)")
    if c.get("canopy_max_m", 0) > 3: flags.append("under/at tree canopy (tree throw, root mound or sparse ground returns possible)")
    if c["type"] != "linear" and c.get("ground_pts", 99) < 10: flags.append("few ground points (<10)")
    c["flags"] = flags
    keep = False
    if c["type"] == "depression" and c["magnitude_m"] >= 0.15 and c["area_m2"] >= 2: keep = True
    if c["type"] == "mound" and c["magnitude_m"] >= 0.18 and c["area_m2"] >= 3: keep = True
    if c["type"] == "linear" and c["length_m"] >= 15: keep = True
    c["shortlist"] = keep
    if keep: short.append(c)
short.sort(key=lambda c: c["dist_m"])
for k, c in enumerate(short, 1): c["sid"] = k
json.dump(dict(R, candidates=C), open(D + "/candidates_raw.json", "w"), indent=1)
print(len(short), "shortlisted")
for c in short:
    print(c["sid"], c["id"], c["type"], c["method"], c["dist_m"], c["bearing_deg"], c["area_m2"], f'{c["length_m"]}x{c["width_m"]}', c["magnitude_m"],
          c.get("ground_pts"), c.get("canopy_max_m"), c["context_slope_deg_10m"], c["terrace_elev_m"])
