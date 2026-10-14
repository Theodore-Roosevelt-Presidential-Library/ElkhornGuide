"""Objective feature detection within 150 m of the house center.
Depressions: (a) fill-sinks difference (priority-flood via morphological reconstruction) >= DEP_T,
             (b) LRM-5 m <= -LRM_T (catches open pits on slopes).
Mounds:      LRM-5 m >= +LRM_T.
Linear:      elongated LRM-10 m components (length >= 12 m, elongation >= 4).
Thresholds tied to measured ground noise (sigma ~2.4 cm): DEP_T = 0.08 m (~3.3 sigma of single points; a TIN
cell averages ~1-2 points so ~3 sigma), min area 1.0 m^2 (4 cells, ~5 ground points)."""
import sys, json, numpy as np
sys.path.insert(0, sys.argv[1])
from common import *
from skimage.morphology import reconstruction
from skimage.measure import label, regionprops
from scipy import ndimage as ndi
from scipy.spatial import cKDTree

G = load(); V = dict(np.load(D + "/derivs.npz"))
dem = G["dem"].astype(float); r = float(G["res"]); x0 = float(G["x0"]); y1 = float(G["y1"])
sig = float(G["noise"])
n = dem.shape[0]
xs = x0 + r * (np.arange(n) + 0.5); ys = y1 - r * (np.arange(n) + 0.5)
GX, GY = np.meshgrid(xs, ys)
dist = np.hypot(GX - HC[0], GY - HC[1])
P = np.load(D + "/dl/pts.npz"); g = P["cls"] == 2
kd = cKDTree(np.c_[P["E"][g], P["N"][g]])
water = np.isnan(dem) | (G["gapd"] > 1.5)

z = np.where(np.isnan(dem), np.nanmax(dem), dem)
seed = z.copy(); seed[1:-1, 1:-1] = z.max()
filled = reconstruction(seed, z, method="erosion")
depth = filled - z

DEP_T, LRM_T, MIN_A = 0.08, 0.10, 1.0
cands = []
def add(mask, kind, method, valfield):
    lab = label(mask, connectivity=2)
    for rp in regionprops(lab):
        area = rp.area * r * r
        if area < MIN_A: continue
        rr, cc = rp.coords[:, 0], rp.coords[:, 1]
        ci, cj = rp.centroid
        E = x0 + r * (cj + 0.5); N = y1 - r * (ci + 0.5)
        d = np.hypot(E - HC[0], N - HC[1])
        if d > 150: continue
        if water[rr, cc].mean() > 0.5: continue
        vals = valfield[rr, cc]
        mag = float(np.max(np.abs(vals)))
        L = rp.major_axis_length * r; W = max(rp.minor_axis_length * r, r)
        npts = len(kd.query_ball_point([E, N], max(np.sqrt(area / np.pi), 0.5)))
        lat, lon = to_ll(E, N)
        brg = (np.degrees(np.arctan2(E - HC[0], N - HC[1])) + 360) % 360
        cands.append(dict(type=kind, method=method, E=round(E, 2), N=round(N, 2), lat=round(lat, 7), lon=round(lon, 7),
                          area_m2=round(area, 2), length_m=round(L, 1), width_m=round(W, 1),
                          orient_deg=round((90 - np.degrees(rp.orientation)) % 180, 0),
                          magnitude_m=round(mag, 3), dist_m=round(d, 1), bearing_deg=round(brg, 0),
                          ground_pts=int(npts), ground_pts_per_m2=round(npts / max(area, np.pi * 0.25), 1),
                          canopy_max_m=round(float(G["chm"][rr, cc].max()), 1),
                          veg_pts_above_0p3m=int(G["vegc"][rr, cc].sum()),
                          mean_slope_deg=round(float(V["slope"][rr, cc].mean()), 1),
                          eccentricity=round(rp.eccentricity, 2)))

add((depth >= DEP_T) & (dist <= 155), "depression", "fill-sinks", depth)
add((V["lrm5"] <= -LRM_T) & (dist <= 155), "depression", "lrm5", V["lrm5"])
add((V["lrm5"] >= LRM_T) & (dist <= 155), "mound", "lrm5", V["lrm5"])
# linear: elongated LRM-10 components
for sgn, kind in ((-1, "linear"), (1, "linear")):
    m = (sgn * V["lrm10"] >= 0.08) & (dist <= 155)
    lab = label(m, connectivity=2)
    for rp in regionprops(lab):
        L = rp.major_axis_length * r; W = max(rp.minor_axis_length * r, r)
        if L >= 12 and L / W >= 4:
            ci, cj = rp.centroid; E = x0 + r * (cj + 0.5); N = y1 - r * (ci + 0.5)
            d = np.hypot(E - HC[0], N - HC[1])
            if d > 150: continue
            lat, lon = to_ll(E, N); brg = (np.degrees(np.arctan2(E - HC[0], N - HC[1])) + 360) % 360
            rr, cc = rp.coords[:, 0], rp.coords[:, 1]
            cands.append(dict(type="linear", method="lrm10 " + ("hollow" if sgn < 0 else "ridge"), E=round(E, 2), N=round(N, 2),
                              lat=round(lat, 7), lon=round(lon, 7), area_m2=round(rp.area * r * r, 1), length_m=round(L, 1),
                              width_m=round(W, 1), orient_deg=round((90 - np.degrees(rp.orientation)) % 180, 0),
                              magnitude_m=round(float(np.abs(V["lrm10"][rr, cc]).max()), 3), dist_m=round(d, 1), bearing_deg=round(brg, 0),
                              ground_pts=None, canopy_max_m=round(float(G["chm"][rr, cc].max()), 1),
                              mean_slope_deg=round(float(V["slope"][rr, cc].mean()), 1)))

# merge fill-sink and lrm5 depressions that coincide (within 1.5 m) -> keep both methods noted
merged = []
for c in sorted(cands, key=lambda c: -c["magnitude_m"]):
    dup = [m for m in merged if m["type"] == c["type"] and c["type"] != "linear" and np.hypot(m["E"] - c["E"], m["N"] - c["N"]) < 1.5]
    if dup:
        if c["method"] not in dup[0]["method"]: dup[0]["method"] += "+" + c["method"]
        continue
    merged.append(c)
merged.sort(key=lambda c: c["dist_m"])
for i, c in enumerate(merged, 1): c["id"] = i
json.dump(dict(noise_sigma_m=sig, thresholds=dict(fill_depth_m=DEP_T, lrm5_m=LRM_T, min_area_m2=MIN_A, lrm10_linear_m=0.08),
               house_center_utm=HC, candidates=merged), open(D + "/candidates_raw.json", "w"), indent=1)
np.save(D + "/filldepth.npy", depth.astype("float32"))
print(len(merged), "candidates;", {t: sum(c["type"] == t for c in merged) for t in ("depression", "mound", "linear")})
for c in merged[:60]:
    print(c["id"], c["type"], c["method"], c["dist_m"], c["bearing_deg"], c["area_m2"], c["length_m"], c["width_m"], c["magnitude_m"], c.get("ground_pts"), c["canopy_max_m"], c["mean_slope_deg"])
