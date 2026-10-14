"""Custom hewn-cottonwood log texture: CC0 rough_wood base (Poly Haven), colour-corrected to the 1886
target, plus season checks along the grain and broad-axe scoring, with a matching normal map.
Tile = 1.0 m x 1.0 m, grain along image x."""
import numpy as np, random, math
from PIL import Image, ImageDraw, ImageFilter
M = __import__('os').environ.get('ELKHORN_MODEL_DIR', 'model')
N = 2048
rng = random.Random(4)


def tile2(path, mode):
    im = Image.open(path).convert(mode).resize((N // 2, N // 2), Image.LANCZOS)
    a = np.asarray(im).astype(np.float32)
    return np.tile(a, (2, 2, 1) if a.ndim == 3 else (2, 2))


def smooth_noise(cells, seed, aspect=1):
    r = np.random.RandomState(seed)
    z = r.rand(cells, max(2, cells * aspect)).astype(np.float32)
    im = Image.fromarray((z * 255).astype(np.uint8)).resize((N, N), Image.BICUBIC)
    return np.asarray(im).astype(np.float32) / 255.


def wrapline(d, pts, w, val):
    for ox in (-N, 0, N):
        for oy in (-N, 0, N):
            d.line([(x + ox, y + oy) for x, y in pts], fill=val, width=w, joint='curve')


def make(name, base_alb, base_disp, ncrack=22, nscore=80, dark=0.72, tone_amp=0.3, seed=4):
    global rng
    rng = random.Random(seed)
    alb = tile2(base_alb, 'RGB') / 255.
    hgt = tile2(base_disp, 'L') / 255.
    gx = np.abs(np.diff(hgt, axis=1)).mean(); gy = np.abs(np.diff(hgt, axis=0)).mean()
    if gx > gy:
        alb = np.rot90(alb); hgt = np.rot90(hgt)
    blot = smooth_noise(12, seed + 1, 1) * 0.6 + smooth_noise(48, seed + 2, 1) * 0.4
    streak = smooth_noise(90, seed + 3, 0)  # becomes streaks along x after resize
    streak = np.asarray(Image.fromarray((np.random.RandomState(seed + 3).rand(96, 6) * 255).astype(np.uint8)).resize((N, N), Image.BICUBIC)).astype(np.float32) / 255.
    crack = Image.new('L', (N, N), 0); dc = ImageDraw.Draw(crack)
    score = Image.new('L', (N, N), 0); ds = ImageDraw.Draw(score)
    for i in range(ncrack):
        x = rng.uniform(0, N); y = rng.uniform(0, N); L = rng.uniform(0.12, 0.75) * N
        w = rng.choice([2, 2, 3, 3, 4, 5, 6, 8]); A = rng.uniform(2, 10); ph = rng.uniform(0, 6.3); drift = rng.uniform(-25, 25)
        steps = 60
        pts = [(x + L * k / steps, y + A * math.sin(k * 0.12 + ph) + drift * k / steps) for k in range(steps + 1)]
        for seg in range(4):
            a = int(steps * seg / 8); b = int(steps * (1 - seg / 8))
            wrapline(dc, pts[a:b + 1], max(1, int(round(w * (1 - seg * 0.25)))), 255)
        if rng.random() < 0.4:   # branching hairline
            k0 = rng.randint(10, 50); q = pts[k0]
            pts2 = [(q[0] + 8 * j, q[1] + (j * j) * 0.04 * rng.choice([-1, 1])) for j in range(rng.randint(10, 30))]
            wrapline(dc, pts2, 1, 200)
    for i in range(nscore):
        x = rng.uniform(0, N); y = rng.uniform(0, N); L = rng.uniform(0.03, 0.1) * N
        ang = math.radians(rng.uniform(60, 82)) * rng.choice([1, -1])
        wrapline(ds, [(x, y), (x + math.cos(ang) * L * 0.35, y + math.sin(ang) * L)], rng.choice([3, 4, 6]), rng.randint(80, 170))
    crack = np.asarray(crack.filter(ImageFilter.GaussianBlur(1.0))).astype(np.float32) / 255.
    score = np.asarray(score.filter(ImageFilter.GaussianBlur(3))).astype(np.float32) / 255.
    tone = (1 - tone_amp / 2 + tone_amp * blot)[..., None] * (0.94 + 0.1 * streak)[..., None]
    a = alb * tone * (1 - dark * crack[..., None]) * (1 - 0.1 * score[..., None])
    a = np.clip(a, 0, 1)
    Image.fromarray((a * 255).astype(np.uint8)).save(M + f'/tex/{name}_albedo.jpg', quality=92)
    h = hgt * 0.5 + blot * 0.1 - crack * 0.9 - score * 0.12
    dy, dx = np.gradient(h)
    s = 16.0
    nx = -dx * s; ny = dy * s; nz = np.ones_like(h)
    l = np.sqrt(nx * nx + ny * ny + nz * nz)
    n = np.stack([nx / l, ny / l, nz / l], -1)
    Image.fromarray(((n * 0.5 + 0.5) * 255).astype(np.uint8)).save(M + f'/tex/{name}_normal.png')
    r = np.clip(0.82 + 0.12 * crack - 0.06 * blot, 0, 1)
    Image.fromarray((r * 255).astype(np.uint8)).save(M + f'/tex/{name}_rough.jpg', quality=92)
    Image.fromarray((a * 255).astype(np.uint8)).resize((700, 700)).save(M + f'/tex/{name}_preview.jpg')


if __name__ == '__main__':
    import os
    os.makedirs(M + '/tex', exist_ok=True)
    make('hewn_cottonwood', M + '/materials/pbr_corrected/log_walls_rough_wood_albedo_weathered_1886_2k.jpg',
         M + '/materials/pbr/rough_wood/rough_wood_displacement_2k.jpg')
    # weathered sawn pine shingle surface: finer checks, more tonal variation
    make('pine_shingle', M + '/materials/pbr_corrected/log_walls_rough_wood_albedo_weathered_1886_2k.jpg',
         M + '/materials/pbr/rough_wood/rough_wood_displacement_2k.jpg', ncrack=40, nscore=0, dark=0.6, tone_amp=0.25, seed=9)
