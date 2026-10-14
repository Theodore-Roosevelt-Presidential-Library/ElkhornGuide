"""Lidar -> house-frame terrain grids (ft). Near: 1 m DEM + canopy height within 450 m; far: 8 m DEM to 2.5 km.
House frame: origin = SW outside corner of house, +Y along the long axis (11.7 deg true), +X at 101.7 deg true, Z ft above house grade."""
import numpy as np, json
from pyproj import Transformer, Geod
from scipy.interpolate import griddata
from scipy import ndimage
S = __import__('os').environ.get('ELKHORN_WORK_DIR', '.')
FT = 0.3048
g = Geod(ellps='WGS84'); t = Transformer.from_crs(4326, 26913, always_xy=True)
lat0, lon0 = 47.2418361, -103.6223395                 # SW corner (footprint.json rectangle_primary)
E0, N0 = t.transform(lon0, lat0)
def along(az, d):
    lo, la, _ = g.fwd(lon0, lat0, az, d); e, n = t.transform(lo, la); return np.array([e - E0, n - N0]) / d
uy = along(11.7, 100.0); ux = along(101.7, 100.0)
A = np.array([ux, uy]).T          # house(m) -> utm offset
Ainv = np.linalg.inv(A)
def to_house_ft(E, N):
    h = Ainv @ np.vstack([E - E0, N - N0]); return h[0] / FT, h[1] / FT
def grid(P, cls_ok, step_ft, x0, x1, y0, y1, stat='min'):
    m = np.isin(P['cls'], cls_ok)
    x, y = to_house_ft(P['E'][m], P['N'][m]); z = P['z'][m] if 'z' in P else None
    return x, y, z
out = {}
for name, f, step, half_ft, cls in (('near', 'wide_450.npz', 3.0, 1300, [2, 9]), ('far', 'far_2500.npz', 26.0, 7800, [2, 9])):
    P = dict(np.load(S + '/lidar/' + f))
    # z in npz is in EPSG:3857 vertical (metres) -> ellipsoidal/orthometric metres as delivered
    x, y, z = grid(P, cls, step, 0, 0, 0, 0)
    z = z / FT
    xs = np.arange(15 - half_ft, 15 + half_ft + 1e-6, step); ys = np.arange(30 - half_ft, 30 + half_ft + 1e-6, step)
    # bin minimum then fill
    ix = np.floor((x - xs[0]) / step).astype(int); iy = np.floor((y - ys[0]) / step).astype(int)
    ok = (ix >= 0) & (ix < len(xs)) & (iy >= 0) & (iy < len(ys))
    Z = np.full((len(ys), len(xs)), np.inf); np.minimum.at(Z, (iy[ok], ix[ok]), z[ok])
    Z[np.isinf(Z)] = np.nan
    msk = np.isnan(Z)
    if msk.any():
        idx = ndimage.distance_transform_edt(msk, return_distances=False, return_indices=True)
        Z = Z[tuple(idx)]
    Z = ndimage.median_filter(Z, 3)
    out[name] = dict(xs=xs, ys=ys, Z=Z)
    if name == 'near':
        # canopy: max of all first returns minus ground
        m = P['cls'] != 7
        xa, ya = to_house_ft(P['E'][m], P['N'][m]); za = P['z'][m] / FT
        ix = np.floor((xa - xs[0]) / step).astype(int); iy = np.floor((ya - ys[0]) / step).astype(int)
        ok = (ix >= 0) & (ix < len(xs)) & (iy >= 0) & (iy < len(ys))
        D = np.full_like(Z, -np.inf); np.maximum.at(D, (iy[ok], ix[ok]), za[ok])
        D[np.isinf(D)] = np.nan
        CHM = np.nan_to_num(D - Z, nan=0.0); CHM[CHM < 0] = 0
        out['chm'] = CHM
# datum: house grade = median ground inside the footprint
xs, ys, Z = out['near']['xs'], out['near']['ys'], out['near']['Z']
X, Y = np.meshgrid(xs, ys)
inside = (X > 0) & (X < 30) & (Y > 0) & (Y < 60)
z0 = float(np.median(Z[inside]))
# water level: lowest 1% of ground in the near grid (river surface / water returns)
wl = float(np.percentile(Z, 0.5))
# trees: local maxima of CHM > 18 ft (5.5 m), min spacing ~ 20 ft
C = ndimage.gaussian_filter(out['chm'], 1.0)
mx = (C == ndimage.maximum_filter(C, size=7)) & (C > 18)
ty, tx = np.nonzero(mx)
trees = [dict(x=float(xs[i]), y=float(ys[j]), h=float(C[j, i]), z=float(Z[j, i] - z0)) for j, i in zip(ty, tx)]
np.savez_compressed(S + '/model/terrain/terrain.npz', near_xs=xs, near_ys=ys, near_Z=Z - z0,
                    far_xs=out['far']['xs'], far_ys=out['far']['ys'], far_Z=out['far']['Z'] - z0, chm=out['chm'])
json.dump(dict(z0_ft=z0, water_ft=wl - z0, trees=trees), open(S + '/model/terrain/terrain_meta.json', 'w'), indent=0)
print('z0 ft', z0, 'water rel ft', wl - z0, 'trees', len(trees), 'near range', np.nanmin(Z - z0), np.nanmax(Z - z0))
# quick check: relief at house, river east
for (px, py, lab) in ((15, 30, 'house'), (-35, -7, 'well'), (-87, 191, 'barn'), (133, -225, 'smithy'), (165, -255, 'dugout'), (-164, -354, 'corral'), (300, 30, '300 E'), (600, -150, 'river cam')):
    i = int((px - xs[0]) / 3); j = int((py - ys[0]) / 3); print(lab, round(float(Z[j, i] - z0), 1))
