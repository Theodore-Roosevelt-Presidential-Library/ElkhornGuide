"""Assign tiers/labels and interpretations, write candidates.json.
Tier A: compact (L/W<=3), open ground (canopy<3 m), off scarp (10 m context slope<=3.5°), depth/height >=0.15/0.18 m.
Tier B: house-adjacent features failing one Tier-A test, and linear features >=15 m long on the terrace (context<=3.5°).
Tier C: everything else that passed the significance screen (mostly floodplain scroll/gully/cottonwood root forms)."""
import sys, os, json, numpy as np
sys.path.insert(0, sys.argv[1])
from common import *
R = json.load(open(D + "/candidates_raw.json"))
NOTES = json.load(open(D + "/interpretations.json")) if os.path.exists(D + "/interpretations.json") else {}
C = []
for c in R["candidates"]:
    if not c["shortlist"]: continue
    ratio = c["length_m"] / c["width_m"]
    if c["type"] != "linear" and c["canopy_max_m"] < 3 and c["context_slope_deg_10m"] <= 3.5 and ratio <= 3:
        tier = "A"
    elif c["type"] != "linear" and c["dist_m"] <= 12:
        tier = "B"
    elif c["type"] == "linear" and c["context_slope_deg_10m"] <= 3.5 and c["terrace_elev_m"] >= 648.0:
        tier = "B"
    else:
        tier = "C"
    c["tier"] = tier
    C.append(c)
cnt = {}
for c in sorted(C, key=lambda c: c["dist_m"]):
    p = {"depression": "D", "mound": "M", "linear": "L"}[c["type"]]
    if c["tier"] == "C": p = "c" + p
    cnt[p] = cnt.get(p, 0) + 1
    c["label"] = f"{p}{cnt[p]}"
    c["raw_id"] = c.pop("id")
    c["interpretation"] = NOTES.get(c["label"], "")
    c.pop("shortlist", None)
C.sort(key=lambda c: ({"A": 0, "B": 1, "C": 2}[c["tier"]], c["dist_m"]))
out = dict(
    source="USGS 3DEP ND_SouthWest_2021_D21 (work unit ND_SouthWest_1_D21), tile 13tfn040320 extent, read from the public EPT copy (s3 usgs-lidar-public); acquired 2021-11-06 (leaf-off), QL2",
    crs="EPSG:26913 (UTM 13N, NAD83) / NAVD88 (GEOID18) m",
    house_center_utm=R["house_center_utm"], noise_sigma_m=R["noise_sigma_m"], thresholds=R["thresholds"],
    tiers=__doc__, candidates=C)
json.dump(out, open(D + "/candidates.json", "w"), indent=1)
for c in C:
    if c["tier"] in "AB":
        print(c["label"], c["tier"], c["type"], c["method"], c["dist_m"], c["bearing_deg"], c["area_m2"], f"{c['length_m']}x{c['width_m']}", c["magnitude_m"], c.get("ground_pts"), c["canopy_max_m"], c["context_slope_deg_10m"], c["orient_deg"])
print({t: sum(c["tier"] == t for c in C) for t in "ABC"})
