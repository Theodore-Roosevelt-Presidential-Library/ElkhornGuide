"""Procedural textures for the Elkhorn interior (albedo + normal), all generated here (no third-party images):
furs and hides, wool blankets, cloth-bound book spines, oilcloth, blue transfer-printed ware, cast iron,
duck canvas, tin, rag/burlap sacking. Tile scale noted per texture (used as `tile` in the builders)."""
import numpy as np, random, math, os
from PIL import Image, ImageDraw, ImageFilter
M = os.environ.get('ELKHORN_MODEL_DIR', 'model')
OUT = M + '/tex/interior/'
os.makedirs(OUT, exist_ok=True)
rng = random.Random(5)


def save(name, alb, h=None, strength=2.0):
    Image.fromarray(np.clip(alb, 0, 255).astype(np.uint8)).save(OUT + name + '_albedo.jpg', quality=90)
    if h is not None:
        gy, gx = np.gradient(h * strength)
        n = np.stack([-gx, gy, np.ones_like(h)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
        Image.fromarray(((n * .5 + .5) * 255).astype(np.uint8)).save(OUT + name + '_normal.png')


def noise(N, cells, seed):
    r = np.random.RandomState(seed)
    return np.asarray(Image.fromarray((r.rand(cells, cells) * 255).astype(np.uint8)).resize((N, N), Image.BICUBIC)).astype(np.float32) / 255.


def fur(name, base, tip, n, lmin, lmax, curl, flow_ang=90, N=1024, wmax=2, seed=1):
    """Hair strokes flowing in one direction (image +v = down the hide), darker at the roots."""
    rr = random.Random(seed)
    im = Image.new('RGB', (N, N), tuple(int(c * 0.55) for c in base)); d = ImageDraw.Draw(im)
    h = Image.new('L', (N, N), 0); dh = ImageDraw.Draw(h)
    for i in range(n):
        x, y = rr.uniform(0, N), rr.uniform(0, N)
        L = rr.uniform(lmin, lmax); a = math.radians(flow_ang + rr.gauss(0, 18))
        c0 = rr.uniform(-curl, curl)
        pts = [(x + math.cos(a + c0 * t * 3) * L * t, y + math.sin(a + c0 * t * 3) * L * t) for t in np.linspace(0, 1, 6)]
        t = rr.random()
        col = tuple(int(base[k] * (1 - t) + tip[k] * t) for k in range(3))
        w = rr.randint(1, wmax)
        for ox in (-N, 0, N):
            for oy in (-N, 0, N):
                q = [(p[0] + ox, p[1] + oy) for p in pts]
                d.line(q, fill=col, width=w); dh.line(q, fill=int(100 + 155 * t), width=w)
    a = np.asarray(im.filter(ImageFilter.SMOOTH)).astype(np.float32)
    a *= (0.85 + 0.3 * noise(N, 8, seed))[..., None]
    hh = np.asarray(h.filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32) / 255.
    save(name, a, hh, 3.0)


def wool_point_blanket(name, N=1024):
    """Wool trade (point) blanket: cream field with bands of indigo, green, red and yellow near the ends;
    texture covers one full blanket length along v."""
    a = np.zeros((N, N, 3), np.float32) + np.array([226, 216, 192])
    bands = [(0.06, 0.035, (40, 52, 92)), (0.105, 0.025, (52, 110, 70)), (0.14, 0.025, (176, 40, 34)), (0.175, 0.025, (214, 170, 40)), (0.21, 0.035, (40, 52, 92))]
    for c0, w, col in bands:
        for cc in (c0, 1 - c0 - w):
            a[int(cc * N):int((cc + w) * N)] = col
    fib = noise(N, 300, 3) * 0.12 + noise(N, 60, 4) * 0.08
    a *= (0.9 + fib)[..., None]
    h = noise(N, 400, 7)
    save(name, a, h, 1.2)


def wool_plaid(name, N=1024):
    a = np.zeros((N, N, 3), np.float32)
    xs = np.arange(N)
    s1 = ((xs // 64) % 2)[None, :]; s2 = ((xs // 64) % 2)[:, None]
    thin = (((xs // 16) % 8) == 0)
    red = np.array([148, 34, 30]); blk = np.array([34, 26, 24])
    m = (s1 + s2) / 2.0
    a[:] = red * (1 - m[..., None] * 0.75) + blk * (m[..., None] * 0.75)
    a[thin[:, None] | thin[None, :]] *= 0.6
    a *= (0.9 + noise(N, 300, 9) * 0.15)[..., None]
    save(name, a, noise(N, 400, 10), 1.0)


def books(name, N=1024):
    """Cloth-bound spines in a row (u across spines, v up the spine): blind-stamped bands, gilt titles."""
    a = np.zeros((N, N, 3), np.float32); h = np.zeros((N, N), np.float32)
    rr = random.Random(12)
    x = 0
    pal = [(98, 34, 26), (40, 60, 40), (70, 46, 30), (32, 36, 56), (120, 92, 60), (82, 20, 18), (150, 130, 96), (56, 40, 30)]
    while x < N:
        w = rr.randint(28, 70); col = np.array(rr.choice(pal), np.float32) * rr.uniform(0.8, 1.15)
        a[:, x:x + w] = col
        a[:, x:x + 2] *= 0.5; a[:, x + w - 2:x + w] *= 0.6
        h[:, x + 3:x + w - 3] = 0.6
        for yb in (0.08, 0.12, 0.85, 0.89):
            a[int(yb * N):int(yb * N) + 5, x + 3:x + w - 3] = (190, 160, 90)
        ty = int(rr.uniform(0.25, 0.4) * N)
        for k in range(rr.randint(3, 6)):
            a[ty + k * 14:ty + k * 14 + 6, x + w // 2 - 6:x + w // 2 + 6] = (196, 166, 96)
        x += w
    a *= (0.9 + noise(N, 200, 13) * 0.15)[..., None]
    save(name, a, h + noise(N, 300, 14) * 0.2, 2.0)


def oilcloth(name, N=1024):
    """Printed table oilcloth: small check in faded red on cream, crazed glossy surface."""
    xs = np.arange(N)
    c = (((xs // 48) % 2)[None, :] + ((xs // 48) % 2)[:, None]).astype(np.float32)
    a = np.zeros((N, N, 3), np.float32) + np.array([222, 210, 180])
    a = a * (1 - 0.35 * (c == 1)[..., None]) + np.array([170, 60, 50]) * 0.35 * (c == 1)[..., None]
    a[c == 2] = np.array([168, 66, 54])
    a *= (0.92 + noise(N, 80, 15) * 0.1)[..., None]
    save(name, a, noise(N, 500, 16) * 0.3, 1.0)


def transferware(name, N=1024):
    """Blue transfer-printed whiteware plate (generic floral border, after Taylor's blue-flowered sherds).
    Mapped planar onto plate discs: centre at (0.5, 0.5)."""
    a = np.zeros((N, N, 3), np.float32) + np.array([236, 236, 230])
    im = Image.fromarray(a.astype(np.uint8)); d = ImageDraw.Draw(im)
    cx = cy = N / 2; blue = (54, 76, 140)
    for r0, r1 in ((0.47, 0.49),):
        d.ellipse([cx - r1 * N, cy - r1 * N, cx + r1 * N, cy + r1 * N], outline=blue, width=6)
    for k in range(24):
        ang = 2 * math.pi * k / 24; r = 0.41 * N
        x, y = cx + r * math.cos(ang), cy + r * math.sin(ang)
        for j in range(5):
            aa = ang + j * 2 * math.pi / 5
            d.ellipse([x + 22 * math.cos(aa) - 12, y + 22 * math.sin(aa) - 12, x + 22 * math.cos(aa) + 12, y + 22 * math.sin(aa) + 12], fill=blue)
        d.ellipse([x - 8, y - 8, x + 8, y + 8], fill=(236, 236, 230))
    for k in range(8):
        ang = 2 * math.pi * k / 8; r = 0.16 * N
        x, y = cx + r * math.cos(ang), cy + r * math.sin(ang)
        d.ellipse([x - 40, y - 18, x + 40, y + 18], fill=blue)
    d.ellipse([cx - 50, cy - 50, cx + 50, cy + 50], outline=blue, width=10)
    a = np.asarray(im.filter(ImageFilter.GaussianBlur(1.5))).astype(np.float32)
    save(name, a, None)


def castiron(name, N=1024):
    a = np.zeros((N, N, 3), np.float32) + 38
    n1 = noise(N, 200, 17); n2 = noise(N, 40, 18)
    a *= (0.75 + 0.5 * n1 * n2)[..., None]
    rust = (noise(N, 24, 19) > 0.78)[..., None]
    a = a * (1 - rust * 0.6) + np.array([92, 52, 32]) * rust * 0.6
    save(name, a, n1 * 0.5 + noise(N, 600, 20) * 0.5, 2.5)


def canvas(name, base, N=1024):
    xs = np.arange(N)
    weave = (np.sin(xs / 2.0)[None, :] * np.sin(xs / 2.0)[:, None]) * 0.5 + 0.5
    a = np.zeros((N, N, 3), np.float32) + np.array(base)
    a *= (0.88 + 0.12 * weave + noise(N, 50, 21)[..., None][..., 0] * 0.1)[..., None]
    save(name, a, weave, 0.8)


def tin_label(name, N=512):
    """Paper labels for tin cans: bands of colour with printed text blocks (illegible at room scale)."""
    a = np.zeros((N, N, 3), np.float32) + np.array([180, 180, 175])
    rr = random.Random(23)
    for k in range(4):
        x0 = k * N // 4
        col = rr.choice([(176, 48, 40), (40, 70, 120), (210, 180, 90), (60, 110, 60), (230, 220, 200)])
        a[int(N * .2):int(N * .8), x0:x0 + N // 4] = col
        for j in range(6):
            y = int(N * (0.3 + j * 0.07)); a[y:y + 8, x0 + 20:x0 + N // 4 - 20] = (30, 30, 30) if j % 2 else (240, 230, 200)
    save(name, a, None)


if __name__ == '__main__':
    fur('buffalo', (28, 18, 10), (92, 62, 34), 60000, 10, 34, 0.9, seed=1, wmax=3)       # curly, dark brown
    fur('bear', (8, 7, 6), (46, 38, 30), 50000, 18, 44, 0.25, seed=2)                   # long, black-brown, glossy
    fur('wolf', (60, 54, 46), (196, 186, 166), 55000, 16, 40, 0.2, seed=3)              # agouti grey
    fur('elkhide', (88, 58, 32), (168, 128, 82), 70000, 6, 14, 0.1, seed=4, wmax=1)      # short, tawny
    fur('coon', (40, 36, 30), (150, 140, 120), 50000, 14, 30, 0.3, seed=5)
    wool_point_blanket('blanket_point'); wool_plaid('blanket_plaid')
    books('books'); oilcloth('oilcloth'); transferware('transferware'); castiron('castiron')
    canvas('duck', (176, 160, 122)); canvas('ticking', (210, 204, 186)); canvas('sacking', (150, 124, 86))
    tin_label('tinlabel')
    print(sorted(os.listdir(OUT)))
