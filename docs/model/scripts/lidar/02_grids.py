"""Build ground DEM (TIN, 0.5 m), ground-point count, DSM/CHM, derivatives. Output npz + GeoTIFFs."""
import sys, numpy as np, rasterio
from rasterio.transform import from_origin
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import Delaunay, cKDTree
from scipy import ndimage as ndi

D = sys.argv[1]  # lidar folder
P = np.load(f"{D}/dl/pts.npz")
CE, CN = 604269.0, 5232968.0
HALF = 160.0
RES = 0.5
x0, y1 = CE - HALF, CN + HALF
n = int(2 * HALF / RES)
xs = x0 + RES * (np.arange(n) + 0.5)
ys = y1 - RES * (np.arange(n) + 0.5)
GX, GY = np.meshgrid(xs, ys)
T = from_origin(x0, y1, RES, RES)

E, N, Z, C = P["E"], P["N"], P["z"], P["cls"]
g = C == 2
tri = Delaunay(np.c_[E[g], N[g]])
dem = LinearNDInterpolator(tri, Z[g])(GX, GY).astype("float32")

# ground point count per 0.5 m cell and per 1 m cell
def count(mask, res):
    m = int(2 * HALF / res)
    i = ((y1 - N[mask]) / res).astype(int); j = ((E[mask] - x0) / res).astype(int)
    ok = (i >= 0) & (i < m) & (j >= 0) & (j < m)
    a = np.zeros((m, m), np.int32); np.add.at(a, (i[ok], j[ok]), 1); return a
gcnt = count(g, RES)
gcnt1 = count(g, 1.0)
# distance from each cell to nearest ground point (gap map)
kd = cKDTree(np.c_[E[g], N[g]])
gapd, _ = kd.query(np.c_[GX.ravel(), GY.ravel()]); gapd = gapd.reshape(GX.shape).astype("float32")

# DSM from all non-noise returns (max per cell), CHM = DSM - DEM
nn = ~np.isin(C, [7, 18])
i = ((y1 - N[nn]) / RES).astype(int); j = ((E[nn] - x0) / RES).astype(int)
ok = (i >= 0) & (i < n) & (j >= 0) & (j < n)
dsm = np.full((n, n), -np.inf, np.float32)
np.maximum.at(dsm, (i[ok], j[ok]), Z[nn][ok])
dsm[~np.isfinite(dsm)] = np.nan
chm = dsm - dem
chm = np.where(np.isnan(chm), 0, chm)
chm = ndi.maximum_filter(np.clip(chm, 0, None), 3)  # fill pits in canopy
# vegetation class 1 points above 0.5 m count (any canopy above ground)
nong = C == 1
i = ((y1 - N[nong]) / RES).astype(int); j = ((E[nong] - x0) / RES).astype(int)
ok = (i >= 0) & (i < n) & (j >= 0) & (j < n)
hag = Z[nong][ok] - dem[i[ok], j[ok]]
vegc = np.zeros((n, n), np.int32); np.add.at(vegc, (i[ok][hag > 0.3], j[ok][hag > 0.3]), 1)

# noise estimate: residual of ground points to local plane (2 m windows) on flat open ground
def noise():
    res = []
    rng = np.random.default_rng(0)
    pts = np.c_[E[g], N[g]]
    for k in rng.choice(len(pts), 4000, replace=False):
        idx = kd.query_ball_point(pts[k], 1.5)
        if len(idx) < 12: continue
        A = np.c_[pts[idx] - pts[k], np.ones(len(idx))]
        coef, *_ = np.linalg.lstsq(A, Z[g][idx], rcond=None)
        slope = np.hypot(coef[0], coef[1])
        if slope < 0.05:
            r = Z[g][idx] - A @ coef
            res.append(r.std())
    return float(np.median(res)), len(res)
sig, nn_ = noise()
print("ground-point noise (std of residual to 1.5 m local plane, slope<5%):", sig, "from", nn_, "patches")

np.savez_compressed(f"{D}/grids.npz", dem=dem, gcnt=gcnt, gcnt1=gcnt1, gapd=gapd, dsm=dsm, chm=chm, vegc=vegc,
                    x0=x0, y1=y1, res=RES, noise=sig)
prof = dict(driver="GTiff", height=n, width=n, count=1, dtype="float32", crs="EPSG:26913", transform=T, compress="deflate")
for name, arr in [("dem_ground_tin_0p5m", dem), ("chm_0p5m", chm), ("gapdist_0p5m", gapd)]:
    with rasterio.open(f"{D}/{name}.tif", "w", **prof) as f: f.write(arr.astype("float32"), 1)
print("DEM range", np.nanmin(dem), np.nanmax(dem))
print("ground pts/m2 overall", g.sum() / (2*HALF)**2)
