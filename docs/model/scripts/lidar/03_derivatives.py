"""Archaeology-style derivatives: multi-direction hillshade, LRM (2/5/10 m), SVF (10 m), openness-neg, slope."""
import sys, numpy as np
sys.path.insert(0, sys.argv[1])
from common import *
from scipy import ndimage as ndi
from scipy.signal import fftconvolve

G = load(); dem = G["dem"].astype("float64"); r = float(G["res"])
z = np.where(np.isnan(dem), np.nanmean(dem), dem)

def disk(rad):
    k = int(round(rad / r)); y, x = np.mgrid[-k:k + 1, -k:k + 1]
    m = (x * x + y * y <= k * k).astype(float); return m / m.sum()

out = {}
out["hs_multi"] = np.mean([hillshade(z, r, a) for a in (0, 60, 120, 180, 240, 300)], axis=0)
out["hs315"] = hillshade(z, r, 315)
for rad in (2, 5, 10):
    out[f"lrm{rad}"] = z - fftconvolve(np.pad(z, 30, mode="edge"), disk(rad), mode="same")[30:-30, 30:-30]
dy, dx = np.gradient(z, r)
out["slope"] = np.degrees(np.arctan(np.hypot(dx, dy)))

# sky-view factor and negative openness, radius 10 m, 16 directions
R = 10.0; nd = 16; steps = int(R / r)
H = np.zeros((nd,) + z.shape); Hn = np.zeros((nd,) + z.shape)
zp = np.pad(z, steps + 1, mode="edge")
n = z.shape[0]
for d in range(nd):
    a = 2 * np.pi * d / nd
    mx = np.full(z.shape, -np.inf); mn = np.full(z.shape, np.inf)
    for s in range(1, steps + 1):
        ox = int(round(s * np.sin(a))); oy = -int(round(s * np.cos(a)))
        dist = r * np.hypot(ox, oy)
        if dist == 0: continue
        sh = zp[steps + 1 + oy: steps + 1 + oy + n, steps + 1 + ox: steps + 1 + ox + n]
        ang = np.arctan((sh - z) / dist)
        mx = np.maximum(mx, ang); mn = np.minimum(mn, ang)
    H[d] = np.maximum(mx, 0); Hn[d] = mn
out["svf"] = 1 - np.mean(np.sin(H), axis=0)
out["neg_open"] = np.degrees(np.mean(np.pi / 2 + Hn, axis=0))  # negative openness (high = in a pit? we use 90+min)
np.savez_compressed(D + "/derivs.npz", **{k: v.astype("float32") for k, v in out.items()})
print("done")
