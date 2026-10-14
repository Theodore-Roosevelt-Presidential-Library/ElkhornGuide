"""Fetch all points of USGS 3DEP EPT (ND_SouthWest_1_D21) within a box around the Elkhorn house,
reproject EPSG:3857 -> EPSG:26913, save as npz. (rockyweb LAZ download was blocked by network;
EPT on s3 usgs-lidar-public is the same 3DEP point cloud, re-tiled.)"""
import json, os, sys, io, urllib.request, numpy as np, laspy
from pyproj import Transformer
from concurrent.futures import ThreadPoolExecutor

BASE = "https://s3-us-west-2.amazonaws.com/usgs-lidar-public/ND_SouthWest_1_D21/"
OUT = sys.argv[1]
CE, CN = 604269.0, 5232968.0
HALF = float(sys.argv[2]) if len(sys.argv) > 2 else 170.0
MAXD = int(sys.argv[3]) if len(sys.argv) > 3 else 99

def get(url):
    for i in range(5):
        try:
            return urllib.request.urlopen(url, timeout=120).read()
        except Exception as e:
            err = e
    raise err

ept = json.loads(get(BASE + "ept.json"))
b = ept["bounds"]
t_utm2m = Transformer.from_crs(26913, 3857, always_xy=True)
corners = [t_utm2m.transform(CE + dx, CN + dy) for dx in (-HALF, HALF) for dy in (-HALF, HALF)]
qx0 = min(c[0] for c in corners); qx1 = max(c[0] for c in corners)
qy0 = min(c[1] for c in corners); qy1 = max(c[1] for c in corners)
print("query 3857", qx0, qx1, qy0, qy1)

def nb(d, x, y, z):
    s = (b[3] - b[0]) / 2 ** d
    return b[0] + x * s, b[1] + y * s, b[0] + (x + 1) * s, b[1] + (y + 1) * s

hier_cache = {}
def hier(key):
    if key not in hier_cache:
        hier_cache[key] = json.loads(get(BASE + "ept-hierarchy/" + key + ".json"))
    return hier_cache[key]

nodes = []
def walk(key, h):
    d, x, y, z = map(int, key.split("-"))
    x0, y0, x1, y1 = nb(d, x, y, z)
    if x1 < qx0 or x0 > qx1 or y1 < qy0 or y0 > qy1:
        return
    if key not in h or d > MAXD:
        return
    c = h[key]
    if c == -1:
        h = hier(key); c = h[key]
    if c > 0:
        nodes.append(key)
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                walk(f"{d+1}-{2*x+dx}-{2*y+dy}-{2*z+dz}", h)

walk("0-0-0-0", hier("0-0-0-0"))
print(len(nodes), "nodes")

def fetch(k):
    data = get(BASE + "ept-data/" + k + ".laz")
    las = laspy.read(io.BytesIO(data))
    m = (las.x >= qx0) & (las.x <= qx1) & (las.y >= qy0) & (las.y <= qy1)
    p = las.points[m]
    return dict(x=np.asarray(las.x[m]), y=np.asarray(las.y[m]), z=np.asarray(las.z[m]),
                cls=np.asarray(p.classification), rn=np.asarray(p.return_number),
                nr=np.asarray(p.number_of_returns), inten=np.asarray(p.intensity),
                gps=np.asarray(p.gps_time), src=np.asarray(p.point_source_id),
                withheld=np.asarray(p.withheld) if hasattr(p, 'withheld') else np.zeros(m.sum(), bool))

with ThreadPoolExecutor(8) as ex:
    parts = list(ex.map(fetch, nodes))
P = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
t = Transformer.from_crs(3857, 26913, always_xy=True)
E, N = t.transform(P["x"], P["y"])
m = (np.abs(E - CE) <= HALF) & (np.abs(N - CN) <= HALF)
P = {k: v[m] for k, v in P.items()}
P["E"], P["N"] = E[m], N[m]
np.savez_compressed(OUT, **P)
print("points", m.sum())
