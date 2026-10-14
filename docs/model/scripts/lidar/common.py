import json, numpy as np
from pyproj import Transformer
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon

SCR = "/tmp/claude-0/-home-claude/4cec2ed1-e3f9-5b51-a27d-73f13cf5ade5/scratchpad"
D = SCR + "/lidar"
CE, CN = 604269.0, 5232968.0
ll2u = Transformer.from_crs(4326, 26913, always_xy=True)
u2ll = Transformer.from_crs(26913, 4326, always_xy=True)
HOUSE_LL = [(47.2418361, -103.6223395), (47.2419972, -103.6222905), (47.2419806, -103.6221721), (47.2418195, -103.6222211)]
HOUSE_C = (47.2419083, -103.6222558)

def to_utm(lat, lon):
    e, n = ll2u.transform(lon, lat); return e, n

def to_ll(e, n):
    lon, lat = u2ll.transform(e, n); return lat, lon

HC = to_utm(*HOUSE_C)
HOUSE = [to_utm(*p) for p in HOUSE_LL]

def stones():
    d = json.load(open(SCR + "/footprint/results.json"))["stones"]
    return {k: to_utm(v["lat"], v["lon"]) for k, v in d.items()}

def load():
    G = dict(np.load(D + "/grids.npz"))
    n = G["dem"].shape[0]; r = float(G["res"])
    G["extent"] = (float(G["x0"]), float(G["x0"]) + n * r, float(G["y1"]) - n * r, float(G["y1"]))
    return G

def hillshade(z, res, az, alt=35, zf=2.0):
    dy, dx = np.gradient(z * zf, res)
    slope = np.arctan(np.hypot(dx, dy)); aspect = np.arctan2(-dx, dy)
    az = np.radians(az); alt = np.radians(alt)
    return np.clip(np.sin(alt) * np.cos(slope) + np.cos(alt) * np.sin(slope) * np.cos(az - aspect), 0, 1)

def decorate(ax, half, cands=None, grid=10, house=True, stones_on=True, color="red", label_size=8, center=None):
    cx, cy = center if center else HC
    ax.set_xlim(cx - half, cx + half); ax.set_ylim(cy - half, cy + half)
    gx0 = np.floor((cx - half) / grid) * grid
    for v in np.arange(gx0, cx + half + grid, grid):
        ax.axvline(v, color="w", lw=0.3, alpha=0.35)
    gy0 = np.floor((cy - half) / grid) * grid
    for v in np.arange(gy0, cy + half + grid, grid):
        ax.axhline(v, color="w", lw=0.3, alpha=0.35)
    if house:
        ax.add_patch(Polygon(HOUSE, closed=True, fill=False, ec="yellow", lw=1.2))
    if stones_on:
        for k, (e, n) in stones().items():
            ax.plot(e, n, "o", ms=3, mfc="cyan", mec="k", mew=0.4)
    if cands:
        for c in cands:
            if abs(c["E"] - cx) < half and abs(c["N"] - cy) < half:
                col = {"depression": "#ff3b3b", "mound": "#3bff6a", "linear": "#ffa500"}.get(c["type"], color)
                ax.plot(c["E"], c["N"], "+", color=col, ms=6, mew=1)
                ax.text(c["E"] + half * 0.012, c["N"] + half * 0.012, str(c["id"]), color=col, fontsize=label_size,
                        weight="bold", path_effects=[__import__("matplotlib.patheffects", fromlist=["x"]).withStroke(linewidth=2, foreground="k")])
    # scale bar
    L = 50 if half > 80 else 20 if half > 30 else 5
    x0 = cx - half + half * 0.06; y0 = cy - half + half * 0.06
    ax.plot([x0, x0 + L], [y0, y0], color="w", lw=4, solid_capstyle="butt")
    ax.plot([x0, x0 + L], [y0, y0], color="k", lw=2, solid_capstyle="butt")
    ax.text(x0 + L / 2, y0 + half * 0.03, f"{L} m", color="w", ha="center", fontsize=9, weight="bold",
            path_effects=[__import__("matplotlib.patheffects", fromlist=["x"]).withStroke(linewidth=2, foreground="k")])
    # north arrow
    xa = cx + half - half * 0.08; ya = cy + half - half * 0.2
    ax.annotate("N", xy=(xa, ya + half * 0.13), xytext=(xa, ya), ha="center", color="w", fontsize=11, weight="bold",
                arrowprops=dict(arrowstyle="-|>", color="w", lw=2))
    ax.set_xticks([]); ax.set_yticks([])
