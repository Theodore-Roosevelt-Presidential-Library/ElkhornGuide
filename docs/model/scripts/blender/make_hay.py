"""Hay textures: weathered stacked prairie hay (body, strands run down-slope = image +v) and alpha straw strands for fringe/tufts."""
import numpy as np, random, math
from PIL import Image, ImageDraw, ImageFilter
M = __import__('os').environ.get('ELKHORN_MODEL_DIR', 'model')
rng = random.Random(11)
N = 1024
PAL = [(150, 128, 86), (128, 108, 72), (170, 148, 100), (104, 92, 66), (182, 162, 112), (92, 84, 66), (140, 126, 94)]
def strokes(d, n, lmin, lmax, wmax, alpha=255, vert=True, wrap=True):
    for i in range(n):
        x, y = rng.uniform(0, N), rng.uniform(0, N)
        L = rng.uniform(lmin, lmax); a = math.radians(90 + rng.gauss(0, 22)) if vert else rng.uniform(0, 6.28)
        bend = rng.uniform(-0.3, 0.3)
        pts = [(x + math.cos(a + bend * t) * L * t, y + math.sin(a + bend * t) * L * t) for t in np.linspace(0, 1, 6)]
        c = PAL[rng.randrange(len(PAL))]; g = rng.uniform(0.8, 1.15)
        col = tuple(int(min(255, v * g)) for v in c) + (alpha,)
        w = rng.choice([1, 1, 2, 2, 3][:wmax + 2])
        offs = [(0, 0)] + ([(-N, 0), (N, 0), (0, -N), (0, N)] if wrap else [])
        for ox, oy in offs:
            d.line([(p[0] + ox, p[1] + oy) for p in pts], fill=col, width=w)
# body albedo + height
im = Image.new('RGB', (N, N), (96, 86, 64)); d = ImageDraw.Draw(im)
h = Image.new('L', (N, N), 0); dh = ImageDraw.Draw(h)
for layer in range(3):
    strokes(d, 9000, 25, 110, 2)
# shadowed gaps
for i in range(2500):
    x, y = rng.uniform(0, N), rng.uniform(0, N); L = rng.uniform(20, 70)
    d.line([(x, y), (x + rng.gauss(0, 6), y + L)], fill=(52, 46, 36), width=rng.choice([2, 3]))
im = im.filter(ImageFilter.SMOOTH)
a = np.asarray(im).astype(np.float32)
lum = a.mean(-1) / 255.
# coarse tonal blotches (weathering)
bl = np.asarray(Image.fromarray((np.random.RandomState(2).rand(16, 16) * 255).astype(np.uint8)).resize((N, N), Image.BICUBIC)).astype(np.float32) / 255.
a = a * (0.82 + 0.3 * bl)[..., None]
Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(M + '/tex/hay_albedo.jpg', quality=90)
gy, gx = np.gradient(lum * 3.0)
n = np.stack([-gx, gy, np.ones_like(lum)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
Image.fromarray(((n * .5 + .5) * 255).astype(np.uint8)).save(M + '/tex/hay_normal.png')
# strands with alpha (fringe / tufts): strands hang from top edge downward
st = Image.new('RGBA', (512, 512), (0, 0, 0, 0)); ds = ImageDraw.Draw(st)
for i in range(650):
    x = rng.uniform(20, 492); L = rng.uniform(100, 420); y0 = rng.uniform(0, 160) * (1 + abs(x - 256) / 256)
    bend = rng.gauss(0, 0.45); c = PAL[rng.randrange(len(PAL))]; g = rng.uniform(0.75, 1.1)
    pts = [(x + math.sin(bend * t * 3) * 30 * t, y0 + L * t) for t in np.linspace(0, 1, 8)]
    ds.line(pts, fill=tuple(int(min(255, v * g)) for v in c) + (255,), width=rng.choice([1, 2, 2, 3]))
A = np.asarray(st).astype(np.float32)
yy = np.linspace(0, 1, 512)[:, None]; xx = np.abs(np.linspace(-1, 1, 512))[None, :]
A[..., 3] *= np.clip(yy / 0.12, 0, 1) * np.clip((1 - xx) / 0.3, 0, 1)
Image.fromarray(A.astype(np.uint8)).save(M + '/tex/hay_strands.png')
print('ok')
