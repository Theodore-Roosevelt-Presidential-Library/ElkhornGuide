"""Procedural textures for the detailed interior props (all generated here, no third-party images):
walnut (gunstocks, chairs, camera), antler (ridged, pearled shed-antler surface), graniteware (mottled blue-grey
enamelled iron, common in 1880s ranch kitchens), transferware (blue transfer-printed plate, after Met 6022's
'worm' border and central scene), brass (lightly tarnished)."""
import numpy as np, random, math, os
from PIL import Image, ImageDraw, ImageFilter
M = os.environ.get('ELKHORN_MODEL_DIR', 'model')
OUT = M + '/tex/interior/'
os.makedirs(OUT, exist_ok=True)


def save(name, alb, h=None, strength=2.0):
    Image.fromarray(np.clip(alb, 0, 255).astype(np.uint8)).save(OUT + name + '_albedo.jpg', quality=92)
    if h is not None:
        gy, gx = np.gradient(h * strength)
        n = np.stack([-gx, gy, np.ones_like(h)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
        Image.fromarray(((n * .5 + .5) * 255).astype(np.uint8)).save(OUT + name + '_normal.png')


def noise(N, cells, seed, Ny=None, cy=None):
    Ny = Ny or N; cy = cy or cells
    r = np.random.RandomState(seed)
    return np.asarray(Image.fromarray((r.rand(cy, cells) * 255).astype(np.uint8)).resize((N, Ny), Image.BICUBIC)).astype(np.float32) / 255.


def tileable(a):
    """Blend edges so the texture repeats without a seam."""
    N = a.shape[0]; w = N // 8
    out = a.copy()
    ramp = np.linspace(0, 1, w)
    for axis in (0, 1):
        src = np.roll(out, N // 2, axis=axis)
        sl = [slice(None)] * out.ndim
        for i in range(w):
            sl[axis] = i
            t = ramp[i]
            out[tuple(sl)] = out[tuple(sl)] * t + src[tuple(sl)] * (1 - t)
            sl[axis] = N - 1 - i
            out[tuple(sl)] = out[tuple(sl)] * t + src[tuple(sl)] * (1 - t)
    return out


def walnut(N=1024):
    """Straight-grained black walnut: grain runs along image x (= u, the long axis of boxes and lofts)."""
    y = np.arange(N, dtype=np.float32)[:, None]; x = np.arange(N, dtype=np.float32)[None, :]
    warp = noise(N, 3, 1, cy=24) * 14 + noise(N, 10, 2, cy=60) * 3
    rings = np.sin((y + warp) / N * 2 * math.pi * 26) * 0.5 + 0.5
    rings = rings ** 3
    fine = noise(N, 8, 3, cy=500)
    pores = (noise(N, 300, 4, cy=700) > 0.82).astype(np.float32)
    v = 0.62 + 0.22 * fine - 0.25 * rings - 0.18 * pores
    v = tileable(v)
    base = np.array([118, 78, 50], np.float32)
    a = base[None, None, :] * v[..., None] * 1.25
    a[..., 0] *= 1.0 + 0.08 * (rings - 0.5)
    h = tileable(0.6 * fine - 0.6 * pores + 0.2 * rings)
    save('walnut', a, h, 1.5)


def antler(N=1024):
    """Shed elk/deer antler: deep longitudinal grooves and pearled ridges. Tube UVs run u = along the beam (image x),
    v = around (image y), so grooves are horizontal stripes. Kept light; per-ring vertex colour adds the brown."""
    y = np.arange(N, dtype=np.float32)[:, None]
    warp = noise(N, 5, 11, cy=30) * 30
    groove = np.abs(np.sin((y + warp) / N * math.pi * 9)) ** 0.6
    pearl = noise(N, 160, 12, cy=90)
    pearl = np.clip((pearl - 0.55) * 3, 0, 1)
    streak = noise(N, 4, 13, cy=180)
    h = 0.7 * groove + 0.35 * pearl + 0.15 * streak
    h = tileable(h)
    v = 0.55 + 0.4 * h + 0.1 * noise(N, 40, 14)
    a = np.array([214, 202, 182], np.float32)[None, None, :] * v[..., None]
    a[..., 2] *= 0.95
    save('antler', a, h, 5.0)


def graniteware(N=1024, base=(92, 112, 138), name='graniteware'):
    """Mottled 'agate' enamel: blue-grey ground with white flecks and darker veining (a few flecks chipped black)."""
    a = np.zeros((N, N, 3), np.float32) + np.array(base, np.float32)
    mott = noise(N, 18, 21) * 0.6 + noise(N, 60, 22) * 0.4
    white = np.clip((mott - 0.55) * 4, 0, 1)
    a = a * (1 - white[..., None]) + np.array([232, 234, 236]) * white[..., None]
    fleck = noise(N, 260, 23) > 0.86
    a[fleck] = a[fleck] * 0.35 + 230 * 0.65
    vein = np.abs(noise(N, 10, 24) - 0.5) < 0.003
    a[vein] *= 0.6
    rr = np.random.RandomState(25)
    for _ in range(40):
        cx, cy = rr.randint(0, N, 2); r = rr.randint(2, 6)
        a[max(0, cy - r):cy + r, max(0, cx - r):cx + r] = (24, 22, 22)
    a = tileable(a)
    save(name, a, noise(N, 300, 26) * 0.15, 1.0)


def transferware(N=1024):
    """Blue transfer-printed whiteware plate face, mapped planar (centre at 0.5, 0.5, rim at radius 0.5):
    vermicular ('worm') ground on the marley and rim, four reserve sprays, and a central landscape vignette."""
    rr = random.Random(31)
    im = Image.new('RGB', (N, N), (236, 237, 232)); d = ImageDraw.Draw(im)
    blue = (40, 62, 132); c = N / 2
    # vermicular ground on the rim band (r 0.36..0.49 of N)
    for _ in range(5200):
        ang = rr.uniform(0, 2 * math.pi); r = rr.uniform(0.355, 0.488) * N
        x, y = c + r * math.cos(ang), c + r * math.sin(ang)
        pts = [(x, y)]; a = rr.uniform(0, 2 * math.pi)
        for k in range(5):
            a += rr.uniform(-1.4, 1.4); x += 5 * math.cos(a); y += 5 * math.sin(a); pts.append((x, y))
        d.line(pts, fill=blue, width=2)
    # reserves: four flower sprays breaking the border
    for k in range(4):
        ang = k * math.pi / 2 + math.pi / 4; r = 0.42 * N
        x, y = c + r * math.cos(ang), c + r * math.sin(ang)
        d.ellipse([x - 46, y - 34, x + 46, y + 34], fill=(236, 237, 232))
        for j in range(7):
            aa = j * 2 * math.pi / 7
            d.ellipse([x + 18 * math.cos(aa) - 11, y + 13 * math.sin(aa) - 11, x + 18 * math.cos(aa) + 11, y + 13 * math.sin(aa) + 11], fill=blue)
        d.ellipse([x - 7, y - 7, x + 7, y + 7], fill=(236, 237, 232))
    d.ellipse([c - 0.352 * N, c - 0.352 * N, c + 0.352 * N, c + 0.352 * N], outline=blue, width=5)
    d.ellipse([c - 0.494 * N, c - 0.494 * N, c + 0.494 * N, c + 0.494 * N], outline=blue, width=7)
    # central vignette: hills, a tree, water, a building
    R = 0.27 * N
    for i in range(1400):
        x = rr.uniform(c - R, c + R); yb = c + 0.08 * N + 0.05 * N * math.sin((x - c) / N * 9)
        if (x - c) ** 2 + (yb - c) ** 2 < R * R:
            h = rr.uniform(0, 0.06 * N); d.line([(x, yb), (x + rr.uniform(-3, 3), yb - h * 0.3)], fill=blue, width=1)
    for i in range(900):   # water hatching
        y = rr.uniform(c + 0.1 * N, c + 0.22 * N); x0 = rr.uniform(c - R * 0.9, c + R * 0.6)
        if (x0 - c) ** 2 + (y - c) ** 2 < R * R * 0.8:
            d.line([(x0, y), (x0 + rr.uniform(8, 30), y)], fill=blue, width=1)
    tx, ty = c - 0.12 * N, c - 0.02 * N   # tree
    d.line([(tx, ty + 80), (tx + 4, ty - 40)], fill=blue, width=6)
    for i in range(260):
        a = rr.uniform(0, 2 * math.pi); r = rr.uniform(0, 60)
        x, y = tx + r * math.cos(a), ty - 70 + r * math.sin(a) * 0.8
        d.ellipse([x - 4, y - 4, x + 4, y + 4], fill=blue)
    bx, by = c + 0.06 * N, c + 0.02 * N   # building
    d.rectangle([bx, by, bx + 70, by + 46], outline=blue, width=4)
    d.polygon([(bx - 8, by), (bx + 35, by - 34), (bx + 78, by)], outline=blue, fill=None)
    d.line([(bx - 8, by), (bx + 35, by - 34), (bx + 78, by)], fill=blue, width=4)
    for i in range(3):
        d.rectangle([bx + 10 + i * 20, by + 14, bx + 18 + i * 20, by + 26], fill=blue)
    for i in range(500):   # sky hatching
        y = rr.uniform(c - R * 0.9, c - 0.12 * N); x0 = rr.uniform(c - R, c + R)
        if (x0 - c) ** 2 + (y - c) ** 2 < R * R * 0.85 and rr.random() < 0.5:
            d.line([(x0, y), (x0 + rr.uniform(10, 40), y)], fill=(120, 136, 186), width=1)
    a = np.asarray(im.filter(ImageFilter.GaussianBlur(0.9))).astype(np.float32)
    a *= (0.97 + 0.03 * noise(N, 50, 32))[..., None]
    save('transferware_hd', a, None)


if __name__ == '__main__':
    walnut(); antler(); graniteware(); transferware()
    print(sorted(f for f in os.listdir(OUT) if f.startswith(('walnut', 'antler', 'granite', 'transferware_hd'))))
