"""Detailed, smooth-shaded props for the Elkhorn interior (draft 5).

Replaces the blocky first-pass props with turned, lofted and textured versions modelled on period pieces:
kerosene stand lamp and tubular barn lantern (ref 16/17/11), 5x8 field view camera on a split-leg tripod, wolf- and
coon-skin overcoats hung on deer horns (HTR 1885), elk antlers with burrs, grooves and ivory tips, Winchester 1876-
pattern lever rifles (T.R. ordered his 1876 Winchesters with half magazines, half-octagon barrels and pistol grips), spindle-back side chairs (Met 1685) and a
Boston-pattern rocker (NGA 16560), blue transfer-printed plates (after Met 6022), ironstone cups and saucers,
graniteware coffee pot and dish pan, yellowware bowl, tin pie plates, cast-iron kettle and skillet.

All dimensions in feet (house frame); geometry is built through lib.Builder, so it lands in the same per-(group,
material) objects and exports, bakes and renders like everything else."""
import math, random
from mathutils import Vector, Matrix
import bpy
import lib
from lib import FT

IT = lib.M + '/tex/interior/'


def m(v):
    return Vector(v) * FT


# ----------------------------------------------------------------- materials
def build_materials(mats):
    def colm(name, rough, metal=0.0):
        mt = bpy.data.materials.new(name); mt.use_nodes = True
        nt = mt.node_tree; bs = nt.nodes['Principled BSDF']
        va = nt.nodes.new('ShaderNodeVertexColor'); va.layer_name = 'Col'
        nt.links.new(va.outputs['Color'], bs.inputs['Base Color'])
        bs.inputs['Roughness'].default_value = rough; bs.inputs['Metallic'].default_value = metal
        mt['x_flatcol'] = 1
        return mt
    def tex(name, rough, ns=1.0, normal=True, tint=None):
        return lib.pbr_material('hd_' + name, IT + name + '_albedo.jpg', IT + name + '_normal.png' if normal else None, None,
                                rough, normal_strength=ns, tint=tint)
    mats['walnut'] = tex('walnut', 0.5, 0.6)
    mats['antler'] = tex('antler', 0.55, 0.7)
    mats['granite'] = tex('graniteware', 0.12, 0.3)
    mats['transfer2'] = tex('transferware_hd', 0.08, normal=False)
    mats['ironware'] = lib.pbr_material('hd_castiron', IT + 'castiron_albedo.jpg', IT + 'castiron_normal.png', None, 0.55, normal_strength=0.6)
    mats['wolfcoat'] = tex('wolf', 0.95, 1.4); mats['cooncoat'] = tex('coon', 0.95, 1.4)
    mats['duckcoat'] = tex('duck', 0.9, 0.8)
    mats['whiteware'] = colm('hd_ironstone', 0.1)
    mats['yellowware'] = colm('hd_yellowware', 0.14)
    mats['brass'] = colm('hd_brass', 0.28, 1.0)
    mats['tin2'] = colm('hd_tinplate', 0.3, 0.9)
    mats['gunmetal'] = colm('hd_gunmetal', 0.38, 0.6)
    mats['bellows'] = colm('hd_bellows', 0.5)
    mats['drape'] = colm('hd_drape', 0.95)
    mats['felt'] = colm('hd_felt', 0.95)
    mats['clearglass'] = lib.flat_material('hd_clearglass', (0.92, 0.96, 0.94), 0.02, transmission=1.0, ior=1.5)
    if 'flame' not in mats:
        fl = bpy.data.materials.new('hd_flame'); fl.use_nodes = True
        fb = fl.node_tree.nodes['Principled BSDF']; fb.inputs['Emission Color'].default_value = (1.0, 0.6, 0.25, 1)
        fb.inputs['Emission Strength'].default_value = 25.0
        mats['flame'] = fl
    lib.SMOOTH_MK.update({'walnut': 38, 'antler': 70, 'granite': 50, 'transfer2': 50, 'ironware': 50, 'wolfcoat': 75,
                          'cooncoat': 75, 'duckcoat': 75, 'whiteware': 50, 'yellowware': 50, 'brass': 50, 'tin2': 50,
                          'gunmetal': 40, 'bellows': 30, 'drape': 70, 'felt': 60, 'clearglass': 60})


# ----------------------------------------------------------------- geometry helpers
def cr(pts, n):
    """Catmull-Rom through pts (any dimension), n samples per segment, ends included."""
    P = [Vector(p) for p in pts]
    if len(P) < 3 or n <= 1:
        return P
    P = [P[0] + (P[0] - P[1])] + P + [P[-1] + (P[-1] - P[-2])]
    out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n; t2 = t * t; t3 = t2 * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(P[-2])
    return out


def basis(up):
    up = Vector(up).normalized()
    a = (Vector((1, 0, 0)) if abs(up.x) < 0.9 else Vector((0, 1, 0)))
    a = (a - up * a.dot(up)).normalized()
    return a, up.cross(a), up


def loft(b, mk, rings, closed=True, tile=0.5, cols=None, uvfn=None, cap0=False, cap1=False, mkfn=None, uvswap=False, flip=False):
    """Skin consecutive rings (lists of Vectors in ft). cols[i] colours segment i; uvfn(i, k, p) -> uv overrides."""
    if flip:                       # reverse the ring winding so face normals point outward
        rings = [list(reversed(r)) for r in rings]
    n = len(rings[0])
    per = [0.0]
    for k in range(1, n + (1 if closed else 0)):
        per.append(per[-1] + (rings[0][k % n] - rings[0][k - 1]).length)
    cen = [sum(r, Vector()) / len(r) for r in rings]
    dist = [0.0]
    for i in range(1, len(rings)):
        dist.append(dist[-1] + (cen[i] - cen[i - 1]).length)
    prev = b.col
    K = n if closed else n - 1
    for i in range(len(rings) - 1):
        if cols:
            b.col = cols[min(i, len(cols) - 1)]
        mki = mkfn(i) if mkfn else mk
        for k in range(K):
            k2 = (k + 1) % n
            pts = [rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]]
            if uvfn:
                uv = [uvfn(i, k, pts[0]), uvfn(i, k2, pts[1]), uvfn(i + 1, k2, pts[2]), uvfn(i + 1, k, pts[3])]
            else:
                uv = [(dist[i] / tile, per[k] / tile), (dist[i] / tile, per[k + 1] / tile),
                      (dist[i + 1] / tile, per[k + 1] / tile), (dist[i + 1] / tile, per[k] / tile)]
                if uvswap:
                    uv = [(q[1], q[0]) for q in uv]
            b.face(mki, [m(p) for p in pts], uv)
    for flag, idx, rev in ((cap0, 0, True), (cap1, len(rings) - 1, False)):
        if not flag:
            continue
        if cols:
            b.col = cols[0 if idx == 0 else -1]
        r = rings[idx]; c = cen[idx]
        for k in range(K):
            k2 = (k + 1) % n
            tri = [c, r[k2], r[k]] if rev else [c, r[k], r[k2]]
            uv = [(0.5, 0.5), (0.5 + 0.5 * math.cos(2 * math.pi * k2 / n), 0.5 + 0.5 * math.sin(2 * math.pi * k2 / n)),
                  (0.5 + 0.5 * math.cos(2 * math.pi * k / n), 0.5 + 0.5 * math.sin(2 * math.pi * k / n))]
            if not rev:
                uv = [uv[0], uv[2], uv[1]]
            b.face(mkfn(len(rings) - 2) if (mkfn and not rev) else (mkfn(0) if mkfn else mk), [m(p) for p in tri], uv)
    b.col = prev


def revolve(b, mk, base, prof, sides=32, up=(0, 0, 1), col=None, smooth_n=0, cap0=False, cap1=False,
            tile=0.5, angmod=None, mkfn=None, planar_from=None, cols=None, phase=0.0, uvworld=False):
    """Surface of revolution. prof [(r, z)] in ft along the axis 'up' from 'base'. planar_from=i: segments >= i get
    planar UVs (centre 0.5, rim at r_max -> 0.5) for printed faces. angmod(i, theta) -> radius multiplier."""
    base = Vector(base); a, bb, upv = basis(up)
    P = cr([Vector(p) for p in prof], smooth_n) if smooth_n else [Vector(p) for p in prof]
    if smooth_n and planar_from is not None:
        planar_from *= smooth_n
    if smooth_n and mkfn is not None:
        f0 = mkfn; mkfn = (lambda i, f0=f0: f0(i // smooth_n))
    rmax = max(p.x for p in P) or 1.0
    rings = []
    for i, p in enumerate(P):
        ring = []
        for k in range(sides):
            th = 2 * math.pi * k / sides + phase
            r = p.x * (angmod(i, th) if angmod else 1.0)
            ring.append(base + upv * p.y + (a * math.cos(th) + bb * math.sin(th)) * r)
        rings.append(ring)
    uvfn = None
    circ = 2 * math.pi * rmax
    if planar_from is not None:
        dist = [0.0]
        for i in range(1, len(P)):
            dist.append(dist[-1] + (P[i] - P[i - 1]).length)
        def uvfn(i, k, p):
            if i >= planar_from:
                th = 2 * math.pi * k / sides + phase
                return (0.5 + 0.5 * P[i].x / rmax * math.cos(th), 0.5 + 0.5 * P[i].x / rmax * math.sin(th))
            return (dist[i] / tile, k / sides * circ / tile)
    if uvworld or mk in ('granite', 'ironware'):
        uvfn = lambda i, k, p: ((p.x + 0.6 * p.z) / 0.7, (p.y - 0.6 * p.z) / 0.7)
    prev = b.col
    if col:
        b.col = col
    loft(b, mk, rings, closed=True, tile=tile, uvfn=uvfn, cap0=cap0, cap1=cap1, mkfn=mkfn, cols=cols)
    b.col = prev


def tube(b, mk, path, radii, sides=12, col=None, smooth_n=0, cols=None, cap0=True, cap1=True, tile=0.5, jitter=0.0,
         rng=None, closed_path=False):
    """Swept circle along a path (ft) with parallel-transport frames; per-point radius; optional per-segment colours."""
    P = cr(path, smooth_n) if smooth_n else [Vector(p) for p in path]
    if not isinstance(radii, (list, tuple)):
        radii = [radii] * len(P)
    elif len(radii) != len(P):
        src = list(radii); out = []
        for i in range(len(P)):
            x = i / (len(P) - 1) * (len(src) - 1); j = min(int(x), len(src) - 2); w = x - j
            out.append(src[j] * (1 - w) + src[j + 1] * w)
        radii = out
    rings = []; nprev = None
    rr = rng or random.Random(3)
    for i, p in enumerate(P):
        if i == 0:
            t = P[1] - p
        elif i == len(P) - 1:
            t = p - P[-2]
        else:
            t = P[i + 1] - P[i - 1]
        t.normalize()
        if nprev is None:
            nprev = t.orthogonal().normalized()
        n = (nprev - t * nprev.dot(t)).normalized(); nprev = n
        bn = t.cross(n)
        ring = []
        for k in range(sides):
            th = 2 * math.pi * k / sides
            r = radii[i] * (1 + (rr.uniform(-jitter, jitter) if jitter else 0))
            ring.append(p + (n * math.cos(th) + bn * math.sin(th)) * r)
        rings.append(ring)
    if closed_path:
        rings.append(rings[0])
    prev = b.col
    if col:
        b.col = col
    if cols and len(cols) != len(rings) - 1:
        cols = [cols[min(len(cols) - 1, int(i / (len(rings) - 1) * len(cols)))] for i in range(len(rings) - 1)]
    loft(b, mk, rings, closed=True, tile=tile, cols=cols, cap0=cap0 and not closed_path, cap1=cap1 and not closed_path)
    b.col = prev


def rrect(w, h, n=16, e=3.0):
    """Superellipse cross-section points (x half-width w, y half-height h)."""
    out = []
    for k in range(n):
        th = 2 * math.pi * k / n
        c, s = math.cos(th), math.sin(th)
        out.append((w * math.copysign(abs(c) ** (2 / e), c), h * math.copysign(abs(s) ** (2 / e), s)))
    return out


class Frame:
    """Local frame: origin o (ft), yaw (rad) about Z. f(x, y, z) -> world ft; v(x, y, z) -> world direction."""
    def __init__(self, o, yaw):
        self.o = Vector(o); self.R = Matrix.Rotation(yaw, 3, 'Z'); self.yaw = yaw
    def __call__(self, x, y, z=0.0):
        return self.o + self.R @ Vector((x, y, z))
    def v(self, x, y, z=0.0):
        return self.R @ Vector((x, y, z))


def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(len(a)))


# ----------------------------------------------------------------- lighting fixtures
BRASS = (0.86, 0.66, 0.36)


def lamp(b, base, lit=True):
    """Kerosene stand lamp, c.1880: stamped brass foot and stem, pressed-glass font, brass collar and flat-wick burner
    with thumbwheel, bulb chimney with crimped ('castellated') rim (Taylor found castellated chimney-glass at Elkhorn)."""
    base = Vector(base)
    revolve(b, 'brass', base, [(0.0, 0.0), (0.24, 0.0), (0.25, 0.015), (0.24, 0.04), (0.2, 0.065), (0.13, 0.09), (0.08, 0.14),
                                (0.062, 0.22), (0.056, 0.33), (0.07, 0.37), (0.09, 0.405), (0.075, 0.44)], 36, col=BRASS, smooth_n=3)
    revolve(b, 'clearglass', base, [(0.075, 0.44), (0.13, 0.47), (0.2, 0.53), (0.245, 0.6), (0.252, 0.665), (0.232, 0.725),
                                     (0.17, 0.78), (0.1, 0.82), (0.078, 0.84)], 36, smooth_n=3)
    revolve(b, 'brass', base, [(0.078, 0.83), (0.088, 0.85), (0.088, 0.9), (0.072, 0.92), (0.092, 0.935), (0.112, 0.965),
                                (0.118, 1.0), (0.104, 1.022), (0.098, 1.045), (0.07, 1.05)], 36, col=BRASS, smooth_n=2)
    revolve(b, 'brass', base + Vector((0.115, 0, 0.955)), [(0.0, 0.0), (0.05, 0.0), (0.055, 0.012), (0.055, 0.03), (0.05, 0.042), (0.0, 0.042)],
            20, up=(1, 0, 0), col=BRASS)
    crimp = lambda i, th, n0=None: 1.0
    prof = [(0.088, 1.03), (0.095, 1.06), (0.13, 1.12), (0.155, 1.2), (0.152, 1.28), (0.12, 1.36), (0.085, 1.44), (0.077, 1.54),
            (0.078, 1.66), (0.09, 1.7), (0.092, 1.71)]
    n = (len(prof) - 1) * 3 + 1
    revolve(b, 'clearglass', base, prof, 36, smooth_n=3,
            angmod=lambda i, th: 1.0 + (0.14 * max(0.0, math.sin(10 * th)) if i >= n - 4 else 0.0))
    if lit:
        revolve(b, 'flame', base, [(0.0, 1.05), (0.03, 1.07), (0.045, 1.11), (0.035, 1.17), (0.0, 1.24)], 12, smooth_n=2, cap0=False)


def lantern(b, base, lit=False):
    """Tubular ('dead-flame') barn lantern of the 1880s: tin fount, side air tubes, bulb globe in a wire guard, vented
    top and wire bail."""
    base = Vector(base); T = (0.62, 0.62, 0.58)
    revolve(b, 'tin2', base, [(0.0, 0.0), (0.26, 0.0), (0.275, 0.025), (0.275, 0.17), (0.25, 0.2), (0.14, 0.22), (0.13, 0.26),
                               (0.11, 0.28)], 32, col=T, smooth_n=2)
    revolve(b, 'clearglass', base, [(0.11, 0.28), (0.15, 0.33), (0.2, 0.44), (0.212, 0.55), (0.185, 0.68), (0.12, 0.76), (0.105, 0.785)], 32, smooth_n=3)
    revolve(b, 'tin2', base, [(0.12, 0.775), (0.2, 0.8), (0.225, 0.84), (0.2, 0.88), (0.1, 0.94), (0.07, 0.99), (0.095, 1.01),
                               (0.08, 1.04), (0.0, 1.05)], 32, col=T, smooth_n=2)
    for s in (-1, 1):
        tube(b, 'tin2', [base + Vector((0.26 * s, 0, 0.12)), base + Vector((0.31 * s, 0, 0.2)), base + Vector((0.31 * s, 0, 0.8)),
                         base + Vector((0.2 * s, 0, 0.87))], 0.026, 12, col=T, smooth_n=4)
    for k in range(4):
        th = math.pi / 4 + k * math.pi / 2
        d = Vector((math.cos(th), math.sin(th), 0))
        tube(b, 'tin2', [base + d * 0.15 + Vector((0, 0, 0.27)), base + d * 0.245 + Vector((0, 0, 0.52)), base + d * 0.15 + Vector((0, 0, 0.78))],
             0.008, 6, col=(0.3, 0.3, 0.3), smooth_n=5)
    ring = [base + Vector((0.245 * math.cos(t), 0.245 * math.sin(t), 0.52)) for t in [i * 2 * math.pi / 24 for i in range(24)]]
    tube(b, 'tin2', ring, 0.008, 6, col=(0.3, 0.3, 0.3), closed_path=True)
    bail = [base + Vector((0.31 * math.cos(t), 0, 0.85 + 0.42 * math.sin(t))) for t in [i * math.pi / 14 for i in range(15)]]
    tube(b, 'tin2', bail, 0.012, 6, col=(0.35, 0.35, 0.33))
    if lit:
        revolve(b, 'flame', base, [(0.0, 0.3), (0.025, 0.32), (0.035, 0.36), (0.022, 0.41), (0.0, 0.46)], 12, smooth_n=2)


# ----------------------------------------------------------------- the view camera
CHERRY = (1.15, 0.86, 0.68)


def view_camera(b, c, yaw):
    """5x8 field view camera on a split-leg wooden tripod (generic 1880s American pattern; T.R. photographed the ranch
    and kept a darkroom in the cellar, but his camera's make is not recorded)."""
    F = Frame(c, yaw); H = 4.0
    # tripod: three split legs with brass clamps and iron-shod feet
    for a in (math.radians(90), math.radians(210), math.radians(330)):
        u = Vector((math.cos(a), math.sin(a), 0)); tng = Vector((-u.y, u.x, 0))
        top = Vector((0, 0, H - 0.04)) + u * 0.2; foot = u * 1.25
        mid = top + (foot - top) * 0.55
        for s in (-1, 1):
            tube(b, 'walnut', [F(*(top + tng * 0.055 * s)), F(*(mid + tng * 0.03 * s))], [0.03, 0.026], 8, col=CHERRY)
        low = top + (foot - top) * 0.45
        tube(b, 'walnut', [F(*low), F(*(foot + Vector((0, 0, 0.12))))], [0.028, 0.024], 8, col=CHERRY)
        tube(b, 'brass', [F(*(mid - (foot - top).normalized() * 0.05)), F(*(mid + (foot - top).normalized() * 0.05))], 0.045, 10, col=BRASS)
        tube(b, 'gunmetal', [F(*(foot + Vector((0, 0, 0.13)))), F(*foot)], [0.03, 0.005], 8, col=(0.3, 0.3, 0.3))
    revolve(b, 'walnut', F(0, 0, H - 0.07), [(0.0, 0.0), (0.3, 0.0), (0.32, 0.03), (0.3, 0.07), (0.0, 0.07)], 32, col=CHERRY)
    revolve(b, 'brass', F(0, 0, H), [(0.0, 0.0), (0.06, 0.0), (0.06, 0.03), (0.0, 0.03)], 16, col=BRASS)

    def B(mk, x0, y0, z0, x1, y1, z1, col):
        cc = F((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
        prev = b.col; b.col = col
        b.obox(mk, m(cc), (F.v(1, 0, 0), F.v(0, 1, 0), (0, 0, 1)), ((x1 - x0) / 2 * FT, (y1 - y0) / 2 * FT, (z1 - z0) / 2 * FT), 0.4, 1)
        b.col = prev
    z0 = H + 0.03
    B('walnut', -0.36, -0.62, z0, 0.36, 0.44, z0 + 0.07, CHERRY)                       # bed
    for sx in (-0.22, 0.22):
        B('brass', sx - 0.02, -0.6, z0 + 0.07, sx + 0.02, 0.4, z0 + 0.085, BRASS)      # focusing tracks
    # rear standard: frame + ground glass + brass corners
    zb, zt = z0 + 0.08, z0 + 0.92
    B('walnut', -0.37, 0.3, zb, -0.3, 0.38, zt, CHERRY); B('walnut', 0.3, 0.3, zb, 0.37, 0.38, zt, CHERRY)
    B('walnut', -0.3, 0.3, zb, 0.3, 0.38, zb + 0.07, CHERRY); B('walnut', -0.3, 0.3, zt - 0.07, 0.3, 0.38, zt, CHERRY)
    B('bellows', -0.3, 0.33, zb + 0.07, 0.3, 0.35, zt - 0.07, (0.28, 0.29, 0.27))
    for sx in (-0.35, 0.35):
        for zz in (zb + 0.03, zt - 0.03):
            B('brass', sx - 0.035, 0.37, zz - 0.035, sx + 0.035, 0.39, zz + 0.035, BRASS)
    # pleated bellows from the rear frame to the lens standard
    NP = 16; ys = [0.3 - k * (0.72 / NP) for k in range(NP + 1)]
    rings = []
    for k, yy in enumerate(ys):
        t = k / NP
        hw = 0.29 + (0.2 - 0.29) * t; hh = 0.33 + (0.21 - 0.33) * t; zc = z0 + 0.5 + (0.47 - 0.5) * t
        if k % 2 == 1:
            hw -= 0.028; hh -= 0.028
        rings.append([F(x, yy, zc + z) for x, z in rrect(hw, hh, 24, 8.0)])
    prev = b.col; b.col = (0.06, 0.055, 0.05)
    loft(b, 'bellows', rings, tile=0.3)
    b.col = prev
    # front standard and lens board
    for sx in (-0.27, 0.27):
        B('walnut', sx - 0.03, -0.5, z0 + 0.07, sx + 0.03, -0.44, z0 + 0.8, CHERRY)
    B('walnut', -0.25, -0.5, z0 + 0.24, 0.25, -0.44, z0 + 0.72, CHERRY)
    # brass barrel lens with a glass front element
    lc = F(0, -0.5, z0 + 0.47); ax = F.v(0, -1, 0)
    revolve(b, 'brass', lc, [(0.0, 0.0), (0.13, 0.0), (0.13, 0.02), (0.1, 0.025), (0.09, 0.06), (0.086, 0.19), (0.094, 0.205),
                              (0.096, 0.26), (0.09, 0.3), (0.075, 0.305), (0.072, 0.29)], 32, up=ax, col=BRASS, smooth_n=2)
    revolve(b, 'clearglass', lc, [(0.072, 0.288), (0.04, 0.3), (0.0, 0.304)], 24, up=ax)
    revolve(b, 'bellows', lc, [(0.07, 0.27), (0.0, 0.27)], 24, up=ax, col=(0.02, 0.02, 0.02))
    for sx in (-1, 1):
        revolve(b, 'brass', F(0.38 * sx, 0.05, z0 + 0.04), [(0.0, 0.0), (0.045, 0.0), (0.05, 0.015), (0.05, 0.045), (0.0, 0.05)], 16,
                up=F.v(sx, 0, 0), col=BRASS)
    # dark focusing cloth thrown over the back
    W = 24; Hn = 14
    grid = []
    for j in range(Hn + 1):
        t = j / Hn
        if t < 0.3:
            yy = 0.1 + t / 0.3 * 0.32; zz = zt + 0.04 + 0.03 * math.sin(t / 0.3 * math.pi)
        else:
            tt = (t - 0.3) / 0.7; yy = 0.42 + 0.12 * tt + 0.03 * math.sin(tt * 3); zz = zt + 0.02 - tt * 1.05
        row = []
        for i in range(W + 1):
            s = i / W; x = -0.46 + 0.92 * s
            fold = (0.05 * math.sin(s * 19 + 1.3) + 0.03 * math.sin(s * 31)) * max(0.0, t - 0.25)
            row.append(F(x * (1 + 0.15 * max(0.0, t - 0.3)), yy + fold, zz))
        grid.append(row)
    prev = b.col; b.col = (0.05, 0.045, 0.045)
    for j in range(Hn):
        for i in range(W):
            q = [grid[j][i], grid[j][i + 1], grid[j + 1][i + 1], grid[j + 1][i]]
            uv = [(i / W, j / Hn), ((i + 1) / W, j / Hn), ((i + 1) / W, (j + 1) / Hn), (i / W, (j + 1) / Hn)]
            b.face('drape', [m(p) for p in q], uv)
            b.face('drape', [m(p) for p in reversed(q)], list(reversed(uv)))
    b.col = prev


# ----------------------------------------------------------------- fur coats on horns
def coat(b, mk, top, yaw, length=3.3, width=1.0, rng=None, wall=0.35, collar=True, col=(1, 1, 1)):
    """Overcoat hung by its collar loop from a tine or hook at 'top' (local origin). It collapses as hung coats do:
    bunched at the hook, shoulders sloping steeply, body flattened against the wall (wall plane at local +y = wall),
    sleeves hanging down the front, vertical folds deepening toward the hem, fur collar rolled round the neck."""
    rng = rng or random.Random(1)
    F = Frame(top, yaw)
    def sm(x):
        x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
    def wx(t):
        return width * ((0.1 + 0.52 * (t / 0.16) ** 0.75) if t < 0.16 else (0.62 + 0.16 * (t - 0.16) / 0.84))
    def wy(t):
        return 0.06 + 0.09 * sm(t / 0.16) + 0.05 * t
    def cy(t):
        return (wall - wy(t) - 0.01) * sm(t / 0.28)
    ph1, ph2 = rng.uniform(0, 6), rng.uniform(0, 6)
    NS = 44; NT = 30
    rings = []
    for j in range(NT + 1):
        t = j / NT; z = -length * t
        amp = 0.01 + 0.11 * t ** 1.2
        ring = []
        for k in range(NS):
            th = 2 * math.pi * k / NS
            c, s = math.cos(th), math.sin(th)
            x = wx(t) * math.copysign(abs(c) ** (2 / 2.3), c); y = wy(t) * math.copysign(abs(s) ** (2 / 2.3), s)
            fold = amp * (0.6 * math.sin(6 * th + ph1 + 3 * t) + 0.4 * math.sin(11 * th + ph2 - 2 * t))
            if s > 0:
                fold *= 0.2                       # back lies against the wall
            ring.append(F(x * (1 + 0.3 * fold), cy(t) + y * (1 + 2.2 * fold), z))
        rings.append(ring)
    prev = b.col; b.col = col
    loft(b, mk, rings, tile=0.9, cap0=True, uvswap=True, flip=True)
    cen = F(0, cy(1.0), -length)
    loft(b, mk, [rings[-1], [p + (cen - p) * 0.1 + Vector((0, 0, 0.06)) for p in rings[-1]]], tile=0.9, uvswap=True, flip=True)   # turned-up hem
    # sleeves: from the shoulder seams, falling down the front of the coat
    ts = 0.16; zs = -length * 0.12
    for s in (-1, 1):
        x0 = wx(ts) * 0.8 * s; yf = cy(0.5) - wy(0.5)
        path = [F(x0, cy(ts), zs), F(x0 * 0.92, yf - 0.06, zs - 0.45), F(x0 * 0.82, yf - 0.1, zs - 1.1), F(x0 * 0.78, yf - 0.1, zs - 1.75)]
        tube(b, mk, path, [0.15 * width, 0.17 * width, 0.165 * width, 0.17 * width], 18, smooth_n=5, cap0=False, cap1=True, tile=0.9,
             jitter=0.03, rng=rng)
        cuff = path[-1]
        tube(b, mk, [cuff + Vector((0, 0, 0.03)), cuff - Vector((0, 0, 0.1))], [0.2 * width, 0.19 * width], 18, tile=0.9, jitter=0.1, rng=rng)
    if collar:
        tc = 0.07
        path = [F(wx(tc) * 1.15 * math.cos(2 * math.pi * k / 26), cy(tc) + wy(tc) * 1.3 * math.sin(2 * math.pi * k / 26), -length * tc + 0.04)
                for k in range(26)]
        tube(b, mk, path, 0.12 * width, 14, tile=0.9, closed_path=True, jitter=0.1, rng=rng)
    b.col = prev


def fur_cap(b, mk, base, up=(0, 0, 1)):
    revolve(b, mk, base, [(0.0, 0.0), (0.33, 0.0), (0.36, 0.06), (0.34, 0.18), (0.3, 0.3), (0.2, 0.39), (0.0, 0.42)], 28, up=up, smooth_n=3, tile=0.9)


def coats_on_horns(b, x, y, z, yaw, rng, kinds=('wolf', 'coon')):
    """Deer horns nailed to the wall, hung with wolf-skin and coon-skin overcoats and a fur cap (HTR 1885: 'the deer
    antlers... support fur coats and caps')."""
    import props
    F = Frame((x, y, z), yaw)
    props.antler_rack(b, tuple(F(0, 0, 0)), tuple(F.v(0, -1, 0)), scale=0.45, rng=rng, kind='deer', skull=True, wall=0.1)
    for k, kind in enumerate(kinds):
        sx = -0.4 + k * 0.8 if len(kinds) > 1 else 0.0
        coat(b, kind + 'coat', tuple(F(sx, -0.3, -0.05)), yaw, length=3.4 if kind == 'wolf' else 3.1, width=0.92 if kind == 'wolf' else 0.85,
             rng=rng, wall=0.38, col=(1, 1, 1) if kind == 'wolf' else (0.8, 0.74, 0.68))
    fur_cap(b, 'cooncoat', tuple(F(0.0, -0.42, 0.22)), up=tuple(F.v(0, -0.6, 1)))


# ----------------------------------------------------------------- antlers
def antler_rack(b, base, facing, up=(0, 0, 1), scale=1.0, rng=None, kind='elk', tilt=0.0, skull=True, wall=None):
    """Elk or mule-deer antlers with knobbed burrs, grooved and pearled beams and polished ivory tips, on a skull plate
    (and a walnut shield when 'wall' gives the distance back to the wall). Indoors the beams keep their brown; outdoors
    (any group but 'interior') they are sun-bleached grey-white as in the 1886 piazza photograph."""
    import props
    rng = rng or random.Random(2)
    base = Vector(base); f = Vector(facing).normalized(); upv = Vector(up).normalized()
    upv = (upv - f * f.dot(upv)).normalized(); side = f.cross(upv).normalized()
    if tilt:
        R = Matrix.Rotation(tilt, 3, side); f = R @ f; upv = R @ upv
    spec = props.RACKS[kind]
    L = spec['L'] * scale * rng.uniform(0.92, 1.06)
    inside = b.group == 'interior'
    C0 = (0.2, 0.13, 0.075) if inside else (0.62, 0.58, 0.5)
    C1 = (0.42, 0.31, 0.2) if inside else (0.8, 0.77, 0.7)
    TIP = (0.93, 0.9, 0.82)
    def ccol(t):
        return lerp(C0, C1, t / 0.6) if t < 0.6 else lerp(C1, TIP, (t - 0.6) / 0.4)
    S = scale
    if wall:
        fh = Vector((f.x, f.y, 0)).normalized() if Vector((f.x, f.y, 0)).length > 1e-3 else f
        sh = fh.cross(Vector((0, 0, 1))).normalized()
        c = base - fh * (wall - 0.035)
        prev = b.col; b.col = (0.55, 0.42, 0.32)
        rings = []
        for dz in (-0.03, 0.03):
            rings.append([c + fh * dz + sh * x + Vector((0, 0, z)) for x, z in rrect(0.4 * S + 0.08, 0.5 * S + 0.1, 28, 2.6)])
        loft(b, 'walnut', rings, tile=0.6, cap0=True, cap1=True, flip=True)
        b.col = prev
    if skull:
        secs = [(-0.16, 0.18, 0.09, 0.05), (0.0, 0.25, 0.15, 0.0), (0.18, 0.22, 0.13, -0.06), (0.32, 0.13, 0.08, -0.12), (0.38, 0.05, 0.04, -0.15)]
        rings = []
        for (p, w, h, zo) in secs:
            c = base + f * p * S + upv * zo * S
            rings.append([c + side * x * S + upv * y * S for x, y in rrect(w, h, 20, 2.4)])
        prev = b.col; b.col = (0.86, 0.83, 0.75)
        loft(b, 'antler', rings, tile=1.0, cap0=True, cap1=True, flip=True)
        b.col = prev
    for s in (-1, 1):
        def W(q, jit=0.0):
            return base + side * (q[0] * s) * L + f * q[1] * L + upv * q[2] * L + Vector((rng.uniform(-jit, jit), rng.uniform(-jit, jit), rng.uniform(-jit, jit)))
        ctrl = [W(q, 0.03 * scale) for q in spec['beam']]
        N = 26
        pts = props._cr(ctrl, N)
        r0 = spec['r0'] * L * 0.72
        radii = [r0 * (1.12 if i == 0 else 1.0) * (1 - 0.6 * (i / N) ** 1.15) for i in range(N + 1)]
        radii[-1] *= 0.35
        cols = [ccol(i / N) for i in range(N)]
        tube(b, 'antler', pts, radii, 14, cols=cols, tile=1.0, jitter=0.03, rng=rng, cap0=True, cap1=True)
        d0 = (pts[1] - pts[0]).normalized()
        tube(b, 'antler', [pts[0] - d0 * 0.03 * scale, pts[0] + d0 * 0.05 * scale], [r0 * 1.6, r0 * 1.45], 16, cols=[C0], jitter=0.2, rng=rng)
        for (t, lf, fw, uw, inw) in spec['tines']:
            idx = min(N - 1, max(1, int(round(t * N))))
            p = pts[idx]
            tl = lf * L * rng.uniform(0.85, 1.1)
            d = (f * fw + upv * uw - side * s * inw + Vector((rng.uniform(-.1, .1), rng.uniform(-.1, .1), 0))).normalized()
            q = [p - d * radii[idx] * 0.5, p + d * tl * 0.35, p + (d + upv * 0.35).normalized() * tl * 0.72, p + (d + upv * 0.8).normalized() * tl]
            rt = radii[idx] * 0.85
            tc = ccol(idx / N)
            tube(b, 'antler', q, [rt * 1.05, rt * 0.78, rt * 0.5, rt * 0.08], 12, smooth_n=4, tile=1.0,
                 cols=[lerp(tc, TIP, min(1, (k / 12) ** 1.4)) for k in range(12)], jitter=0.02, rng=rng)


# ----------------------------------------------------------------- rifles
def rifle(b, butt, top, rng, up=None):
    """Winchester Model 1876-pattern lever rifle with the special-order features T.R. generally specified for his
    1876s (American Rifleman, 'Personally, I Prefer the Winchester'): pistol-grip walnut stock with a shotgun butt,
    case-hardened receiver, half-octagon barrel and half magazine. Which rifles hung at Elkhorn is not recorded.
    Overall about 4.1 ft; scaled to the butt->muzzle span given."""
    butt = Vector(butt); top = Vector(top); d = (top - butt); L = d.length; d.normalize()
    if up is None:
        Z = Vector((0, 0, 1))
        if abs(d.z) > 0.7:
            h = Vector((d.x, d.y, 0)); up = h.normalized() if h.length > 1e-3 else Vector((1, 0, 0))
        else:
            up = Z
    upv = (Vector(up) - d * d.dot(Vector(up))).normalized(); sv = d.cross(upv)
    k = L / 4.1
    def P(s, x, z):
        return butt + d * (s * k) + sv * (x * k) + upv * (z * k)
    def section_loft(mk, stations, n=18, e=3.0, col=None, cap0=True, cap1=True, smooth=3, flip=True):
        st = cr([Vector(s_) for s_ in stations], smooth) if smooth else [Vector(s_) for s_ in stations]
        rings = [[P(q.x, x, q.y + z) for x, z in rrect(q.w / 2, q.z / 2, n, e)] for q in st]
        prev = b.col
        if col: b.col = col
        loft(b, mk, rings, tile=0.6, cap0=cap0, cap1=cap1, flip=flip)
        b.col = prev
    WN = (0.95, 0.78, 0.62); GM = (0.025, 0.025, 0.028); CH = (0.07, 0.06, 0.05)
    # stations: (s, centre z, height, width)
    section_loft('walnut', [(0.0, -0.3, 0.4, 0.135), (0.03, -0.297, 0.405, 0.138), (0.35, -0.24, 0.33, 0.13), (0.68, -0.15, 0.2, 0.115),
                            (0.88, -0.085, 0.135, 0.1), (1.0, -0.07, 0.135, 0.1), (1.1, -0.055, 0.17, 0.1)], col=WN)
    section_loft('walnut', [(0.99, -0.1, 0.1, 0.098), (0.95, -0.17, 0.11, 0.1), (0.89, -0.25, 0.12, 0.1), (0.84, -0.3, 0.12, 0.1),
                            (0.82, -0.32, 0.11, 0.095)], col=WN, flip=False)                      # pistol grip (runs downward)
    section_loft('gunmetal', [(0.82, -0.325, 0.112, 0.097), (0.815, -0.335, 0.1, 0.09)], col=GM, smooth=0, flip=False)   # grip cap
    section_loft('gunmetal', [(-0.02, -0.3, 0.405, 0.138), (0.005, -0.3, 0.405, 0.138)], col=GM, smooth=0)   # shotgun buttplate
    section_loft('gunmetal', [(1.08, -0.045, 0.2, 0.098), (1.12, -0.035, 0.225, 0.1), (1.7, -0.035, 0.225, 0.1), (1.76, -0.03, 0.17, 0.095)],
                 n=20, e=7.0, col=CH, smooth=0)
    section_loft('walnut', [(1.76, -0.06, 0.12, 0.088), (2.2, -0.06, 0.118, 0.085), (2.52, -0.058, 0.112, 0.08)], col=WN, smooth=0)
    section_loft('gunmetal', [(2.52, -0.058, 0.118, 0.084), (2.58, -0.058, 0.118, 0.084)], col=GM, smooth=0)
    # half-octagon barrel: octagon breech, round from the forend tip to the muzzle
    rings = []
    for s_ in (1.72, 2.62):
        r = 0.05 if s_ < 2 else 0.046
        rings.append([P(s_, r * math.cos(math.pi / 8 + j * math.pi / 4), r * math.sin(math.pi / 8 + j * math.pi / 4)) for j in range(8)])
    prev = b.col; b.col = GM
    loft(b, 'gunmetal', rings, tile=0.6, cap0=True, cap1=True, flip=True)
    b.col = prev
    tube(b, 'gunmetal', [P(2.6, 0, 0), P(4.1, 0, 0)], [0.044 * k, 0.04 * k], 16, col=GM)
    # half magazine
    tube(b, 'gunmetal', [P(1.76, 0, -0.088), P(2.88, 0, -0.086)], 0.033 * k, 14, col=GM)
    tube(b, 'gunmetal', [P(2.88, 0, -0.086), P(2.93, 0, -0.086)], 0.036 * k, 14, col=GM)
    section_loft('gunmetal', [(2.8, -0.04, 0.17, 0.1), (2.84, -0.04, 0.17, 0.1)], n=16, e=4.0, col=GM, smooth=0)
    # sights
    section_loft('gunmetal', [(2.05, 0.06, 0.04, 0.06), (2.12, 0.06, 0.04, 0.06)], n=8, e=6.0, col=GM, smooth=0)
    section_loft('gunmetal', [(4.02, 0.055, 0.035, 0.012), (4.07, 0.05, 0.025, 0.012)], n=8, e=6.0, col=GM, smooth=0)
    # hammer
    tube(b, 'gunmetal', [P(1.13, 0, 0.05), P(1.1, 0, 0.12), P(1.04, 0, 0.16), P(1.0, 0, 0.15)], 0.02 * k, 8, smooth_n=3, col=CH)
    # pistol-grip lever: trigger guard and a lever bent down along the front of the grip
    lever = [P(1.64, 0, -0.15), P(1.4, 0, -0.17), P(1.22, 0, -0.205), P(1.08, 0, -0.215), P(1.0, 0, -0.25), P(0.95, 0, -0.31),
             P(0.93, 0, -0.35), P(0.96, 0, -0.36)]
    tube(b, 'gunmetal', lever, 0.02 * k, 8, smooth_n=3, col=CH)
    tube(b, 'gunmetal', [P(1.16, 0, -0.14), P(1.15, 0, -0.18), P(1.12, 0, -0.2)], 0.012 * k, 6, smooth_n=3, col=GM)


# ----------------------------------------------------------------- chairs
def bamboo(L, r, rings=(0.3, 0.62), top=0.04):
    """Bamboo-turned leg profile [(r, z)] of length L."""
    pr = [(r * 0.92, 0.0), (r, 0.04 * L)]
    for t in rings:
        pr += [(r * 1.02, (t - 0.04) * L), (r * 0.8, t * L), (r * 1.02, (t + 0.03) * L)]
    pr += [(r * 0.95, (1 - top - 0.03) * L), (r * 0.75, (1 - top) * L), (r * 0.65, L)]
    return pr


def turned(b, mk, p0, p1, prof_fn, col, sides=14):
    p0 = Vector(p0); p1 = Vector(p1); L = (p1 - p0).length
    revolve(b, mk, p0, prof_fn(L), sides, up=(p1 - p0), col=col, smooth_n=2)


def seat(b, F, z, hw_front, hw_back, y_front, y_back, col, roll=False, n=40):
    """Saddle-shaped plank seat: outline tapers front->back, top dished, edges rounded."""
    yc = (y_front + y_back) / 2; hd = (y_back - y_front) / 2
    def outline(sc):
        pts = []
        for k in range(n):
            th = 2 * math.pi * k / n
            c, s = math.cos(th), math.sin(th)
            yy = hd * math.copysign(abs(s) ** (2 / 4.0), s)
            w = hw_front + (hw_back - hw_front) * (yy / hd * 0.5 + 0.5)
            xx = w * math.copysign(abs(c) ** (2 / 4.0), c)
            pts.append((xx * sc, yc + yy * sc))
        return pts
    levels = [(0.95, -0.075), (1.0, -0.035), (1.0, 0.03), (0.97, 0.055), (0.82, 0.04), (0.5, 0.022), (0.2, 0.028), (0.03, 0.03)]
    rings = [[F(x, y, z + dz) for x, y in outline(sc)] for sc, dz in levels]
    def uv(i, k, p):
        lp = F.R.inverted() @ (p - F.o)
        return (lp.x / 0.7, lp.y / 0.7)
    prev = b.col; b.col = col
    loft(b, 'walnut', rings, uvfn=uv, cap0=True, cap1=True)
    b.col = prev


def side_chair(b, x, y, yaw, rng, col=None):
    """Spindle-back kitchen chair, c.1880 (after Met 1685): saddle plank seat 17 in high, bamboo-turned splayed legs,
    H-stretchers, raked turned back posts, five spindles and a bent crest rail."""
    col = (0.82, 0.68, 0.55) if col is None or sum(col) < 1.0 else col
    F = Frame((x, y, 0), yaw); FLz = __import__('interior').FL
    sh = FLz + 1.45
    seat(b, F, sh, 0.66, 0.6, -0.64, 0.56, col)
    legs = {(-1, -1): ((-0.5, -0.44), (-0.62, -0.62)), (1, -1): ((0.5, -0.44), (0.62, -0.62)),
            (-1, 1): ((-0.46, 0.38), (-0.58, 0.58)), (1, 1): ((0.46, 0.38), (0.58, 0.58))}
    P = {}
    for key, (tp, ft) in legs.items():
        p0 = F(ft[0], ft[1], FLz); p1 = F(tp[0], tp[1], sh - 0.07)
        P[key] = (p0, p1)
        turned(b, 'walnut', p0, p1, lambda L: bamboo(L, 0.062), col)
    def at(key, h):
        p0, p1 = P[key]; return p0 + (p1 - p0) * (h / (p1.z - p0.z))
    for (k1, k2, h) in (((-1, -1), (1, -1), 0.5), ((-1, 1), (1, 1), 0.55), ((-1, -1), (-1, 1), 0.38), ((1, -1), (1, 1), 0.38)):
        turned(b, 'walnut', at(k1, h), at(k2, h), lambda L: bamboo(L, 0.034, rings=(0.5,), top=0.02), col, sides=10)
    # back posts (continuing the rear legs' line up through the seat)
    tops = {}
    for sx in (-1, 1):
        p0 = F(0.47 * sx, 0.44, sh); p1 = F(0.5 * sx, 0.72, sh + 1.62)
        tops[sx] = p1
        turned(b, 'walnut', p0, p1, lambda L: [(0.058, 0.0), (0.06, 0.1 * L), (0.05, 0.45 * L), (0.042, 0.5 * L), (0.05, 0.53 * L),
                                               (0.045, 0.9 * L), (0.055, 0.95 * L), (0.03, L)], col)
    # crest rail: bent board between the post tops
    rings = []
    for i in range(13):
        s = -0.56 + i * (1.12 / 12)
        yy = 0.72 + 0.07 * (1 - (s / 0.56) ** 2) - 0.02
        c = F(s, yy, sh + 1.47)
        rings.append([c + F.v(0, py, 0) + Vector((0, 0, pz)) for py, pz in rrect(0.035, 0.16, 16, 3.0)])
    prev = b.col; b.col = col
    def uvc(i, k, p):
        lp = F.R.inverted() @ (p - F.o); return (lp.x / 0.7, lp.z / 0.7)
    loft(b, 'walnut', rings, uvfn=uvc, cap0=True, cap1=True)
    b.col = prev
    for i in range(5):
        s = -0.34 + i * 0.17
        yy = 0.72 + 0.07 * (1 - (s / 0.56) ** 2) - 0.02
        turned(b, 'walnut', F(s * 0.92, 0.42, sh + 0.02), F(s, yy, sh + 1.33),
               lambda L: [(0.026, 0.0), (0.032, 0.25 * L), (0.024, 0.75 * L), (0.02, L)], col, sides=10)


def windsor_rocker(b, pos, yaw, rng):
    """Arm rocker after the Boston rocker (NGA 16560): rolled plank seat, turned legs and arm supports on bent
    rockers, shaped arms, tall spindle back with a broad crest. Natural varnished finish (paint unknown)."""
    pos = Vector(pos); F = Frame((pos.x, pos.y, 0), yaw); z0 = pos.z
    col = (0.72, 0.56, 0.44)
    sh = z0 + 1.42
    seat(b, F, sh, 0.82, 0.72, -0.72, 0.62, col)
    # roll at the front of the seat
    rings = []
    for i in range(13):
        s = -0.74 + i * (1.48 / 12)
        c = F(s * (1 - 0.06 * (s / 0.74) ** 2), -0.66, sh + 0.02)
        rings.append([c + F.v(0, py, 0) + Vector((0, 0, pz)) for py, pz in rrect(0.07, 0.06, 14, 2.0)])
    prev = b.col; b.col = col; loft(b, 'walnut', rings, tile=0.6, cap0=True, cap1=True); b.col = prev
    # rockers
    for sx in (-0.7, 0.7):
        rings = []
        for i in range(25):
            yy = -1.35 + i * (2.55 / 24)
            zz = z0 + 0.09 + 0.2 * ((yy + 0.05) / 1.3) ** 2
            rings.append([F(sx + px, yy, zz + pz) for px, pz in rrect(0.035, 0.085, 12, 4.0)])
        prev = b.col; b.col = col; loft(b, 'walnut', rings, tile=0.6, cap0=True, cap1=True, flip=True); b.col = prev
    for (lx, ly) in ((-0.7, -0.5), (0.7, -0.5), (-0.7, 0.45), (0.7, 0.45)):
        zr = z0 + 0.09 + 0.2 * ((ly + 0.05) / 1.3) ** 2 + 0.06
        turned(b, 'walnut', F(lx, ly, zr), F(lx * 0.86, ly * 0.95, sh - 0.07), lambda L: bamboo(L, 0.06), col)
    for sy in (-0.5, 0.45):
        zz = z0 + 0.5
        turned(b, 'walnut', F(-0.68, sy, zz), F(0.68, sy, zz), lambda L: bamboo(L, 0.033, rings=(0.5,), top=0.02), col, sides=10)
    # back: posts, spindles, crest
    for sx in (-1, 1):
        turned(b, 'walnut', F(0.6 * sx, 0.5, sh), F(0.66 * sx, 0.92, sh + 2.45),
               lambda L: [(0.055, 0.0), (0.06, 0.08 * L), (0.045, 0.5 * L), (0.04, 0.85 * L), (0.05, 0.93 * L), (0.03, L)], col)
    for i in range(7):
        s = -0.42 + i * 0.14
        turned(b, 'walnut', F(s * 0.95, 0.5, sh + 0.02), F(s * 1.15, 0.9, sh + 2.05),
               lambda L: [(0.024, 0.0), (0.03, 0.2 * L), (0.022, 0.8 * L), (0.02, L)], col, sides=10)
    rings = []
    for i in range(15):
        s = -0.82 + i * (1.64 / 14)
        yy = 0.93 + 0.09 * (1 - (s / 0.82) ** 2)
        c = F(s, yy, sh + 2.18)
        hh = 0.2 + 0.03 * math.cos(s / 0.82 * math.pi / 2)
        rings.append([c + F.v(0, py, 0) + Vector((0, 0, pz)) for py, pz in rrect(0.04, hh, 16, 3.5)])
    prev = b.col; b.col = col
    loft(b, 'walnut', rings, uvfn=lambda i, k, p: ((F.R.inverted() @ (p - F.o)).x / 0.7, (F.R.inverted() @ (p - F.o)).z / 0.7), cap0=True, cap1=True)
    b.col = prev
    # arms with scrolled ends, and turned arm supports
    for sx in (-1, 1):
        path = [Vector((0.6 * sx, 0.6, 0.95)), Vector((0.74 * sx, 0.2, 0.9)), Vector((0.8 * sx, -0.3, 0.86)), Vector((0.8 * sx, -0.62, 0.84))]
        P_ = cr(path, 4)
        rings = []
        for q in P_:
            c = F(q.x, q.y, sh + q.z)
            rings.append([c + F.v(px, 0, 0) + Vector((0, 0, pz)) for px, pz in rrect(0.075, 0.03, 14, 3.0)])
        prev = b.col; b.col = col; loft(b, 'walnut', rings, tile=0.6, cap0=True, cap1=True); b.col = prev
        revolve(b, 'walnut', F(0.8 * sx, -0.66, sh + 0.84), [(0.0, -0.03), (0.08, -0.03), (0.09, 0.0), (0.08, 0.03), (0.0, 0.035)], 16, col=col)
        turned(b, 'walnut', F(0.76 * sx, -0.5, sh - 0.02), F(0.8 * sx, -0.55, sh + 0.83),
               lambda L: [(0.035, 0.0), (0.05, 0.3 * L), (0.03, 0.6 * L), (0.04, 0.8 * L), (0.028, L)], col, sides=12)


# ----------------------------------------------------------------- tableware and kitchen ware
WHITE = (0.94, 0.94, 0.9)


def plate(b, c, r, normal=(0, 0, 1)):
    """Blue transfer-printed whiteware plate: foot ring, well, cavetto and marley; printed face, glazed white underside."""
    s = r / 0.4
    prof = [(0.0, 0.012), (0.5, 0.012), (0.515, 0.0), (0.6, 0.0), (0.62, 0.012), (0.7, 0.03), (0.95, 0.058), (1.0, 0.063),
            (1.0, 0.072), (0.975, 0.076), (0.9, 0.071), (0.68, 0.046), (0.62, 0.031), (0.58, 0.027), (0.0, 0.027)]
    prof = [(p[0] * r, p[1] * s) for p in prof]
    revolve(b, 'whiteware', c, prof, 40, up=normal, col=WHITE, mkfn=lambda i: 'transfer2' if i >= 9 else 'whiteware',
            planar_from=9, cols=None)


def saucer(b, c, r=0.27):
    s = r / 0.27
    prof = [(0.0, 0.01), (0.45, 0.01), (0.47, 0.0), (0.55, 0.0), (0.6, 0.015), (0.95, 0.05), (1.0, 0.055), (0.97, 0.062),
            (0.6, 0.03), (0.42, 0.022), (0.0, 0.022)]
    revolve(b, 'whiteware', c, [(p[0] * r, p[1] * s) for p in prof], 32, col=WHITE)


def cup(b, c, col=WHITE, handle_angle=0.0, with_saucer=True):
    """Ironstone cup with handle (and saucer)."""
    c = Vector(c)
    if with_saucer:
        saucer(b, c); c = c + Vector((0, 0, 0.022))
    revolve(b, 'whiteware', c, [(0.0, 0.0), (0.09, 0.0), (0.1, 0.012), (0.095, 0.02), (0.12, 0.045), (0.152, 0.12), (0.162, 0.23),
                                 (0.166, 0.27), (0.158, 0.278), (0.15, 0.26), (0.142, 0.12), (0.1, 0.055), (0.0, 0.05)], 32, col=col, smooth_n=2)
    a = handle_angle; u = Vector((math.cos(a), math.sin(a), 0))
    tube(b, 'whiteware', [c + u * 0.15 + Vector((0, 0, 0.225)), c + u * 0.25 + Vector((0, 0, 0.21)), c + u * 0.265 + Vector((0, 0, 0.14)),
                          c + u * 0.2 + Vector((0, 0, 0.075)), c + u * 0.14 + Vector((0, 0, 0.08))], 0.017, 8, smooth_n=4, col=col)


def coffee_pot(b, c, angle=0.0):
    """Graniteware (mottled enamelled iron) boiler coffee pot with hinged domed lid, spout and strap handle."""
    c = Vector(c); u = Vector((math.cos(angle), math.sin(angle), 0)); G = (1.0, 1.0, 1.0)
    revolve(b, 'granite', c, [(0.0, 0.0), (0.29, 0.0), (0.305, 0.02), (0.3, 0.05), (0.29, 0.3), (0.265, 0.55), (0.232, 0.68),
                               (0.212, 0.72), (0.22, 0.74)], 36, col=G, smooth_n=3, cap0=True)
    revolve(b, 'granite', c, [(0.215, 0.735), (0.2, 0.76), (0.165, 0.81), (0.1, 0.845), (0.05, 0.852), (0.045, 0.88), (0.07, 0.915),
                               (0.0, 0.93)], 36, col=G, smooth_n=3)
    tube(b, 'granite', [c + u * 0.24 + Vector((0, 0, 0.14)), c + u * 0.38 + Vector((0, 0, 0.34)), c + u * 0.47 + Vector((0, 0, 0.6)),
                        c + u * 0.54 + Vector((0, 0, 0.74))], [0.075, 0.055, 0.04, 0.032], 14, smooth_n=4, col=G, cap1=False)
    tube(b, 'granite', [c - u * 0.24 + Vector((0, 0, 0.64)), c - u * 0.42 + Vector((0, 0, 0.62)), c - u * 0.46 + Vector((0, 0, 0.42)),
                        c - u * 0.4 + Vector((0, 0, 0.2)), c - u * 0.28 + Vector((0, 0, 0.14))], 0.026, 10, smooth_n=4, col=G)


def dish_pan(b, c):
    revolve(b, 'granite', c, [(0.0, 0.0), (0.55, 0.0), (0.6, 0.03), (0.74, 0.3), (0.785, 0.335), (0.785, 0.355), (0.755, 0.345),
                               (0.72, 0.31), (0.57, 0.045), (0.0, 0.04)], 40, col=(1, 1, 1), smooth_n=2)


def yellowware_bowl(b, c, r=0.46):
    s = r / 0.46
    prof = [(0.0, 0.0), (0.22, 0.0), (0.235, 0.03), (0.4, 0.22), (0.45, 0.3), (0.462, 0.33), (0.43, 0.332), (0.38, 0.24),
            (0.2, 0.065), (0.0, 0.055)]
    Y = (0.86, 0.66, 0.36); Wb = (0.92, 0.9, 0.84); Bn = (0.35, 0.22, 0.14)
    cols = [Y, Y, Y, Y, Wb, Y, Y, Y, Y]
    revolve(b, 'yellowware', c, [(p[0] * s, p[1] * s) for p in prof], 40, col=Y, cols=[Y, Y, Bn, Y, Wb, Y, Y, Y, Y])


def pie_tins(b, c, n=3):
    c = Vector(c)
    for k in range(n):
        revolve(b, 'tin2', c + Vector((0, 0, 0.016 * k)), [(0.0, 0.0), (0.31, 0.0), (0.41, 0.115), (0.45, 0.125), (0.455, 0.14), (0.44, 0.142),
                                                           (0.405, 0.13), (0.3, 0.014), (0.0, 0.014)], 40, col=(0.7, 0.7, 0.66))


def kettle(b, c):
    """Cast-iron tea kettle with gooseneck spout, lid and bail."""
    c = Vector(c); K = (1, 1, 1)
    revolve(b, 'ironware', c, [(0.0, 0.0), (0.3, 0.0), (0.38, 0.05), (0.42, 0.2), (0.4, 0.34), (0.3, 0.47), (0.17, 0.52), (0.16, 0.56),
                                (0.135, 0.585), (0.05, 0.6), (0.035, 0.66), (0.055, 0.69), (0.0, 0.7)], 36, col=K, smooth_n=3)
    tube(b, 'ironware', [c + Vector((0.36, 0, 0.18)), c + Vector((0.52, 0, 0.28)), c + Vector((0.6, 0, 0.44)), c + Vector((0.66, 0, 0.52))],
         [0.07, 0.055, 0.04, 0.032], 12, smooth_n=4, col=K, cap1=False)
    for s in (-1, 1):
        revolve(b, 'ironware', c + Vector((0, 0.36 * s, 0.38)), [(0.0, 0.0), (0.04, 0.0), (0.04, 0.06), (0.0, 0.06)], 10, up=(0, s, 0), col=K, uvworld=True)
    bail = [c + Vector((0, 0.4 * math.cos(t), 0.42 + 0.48 * math.sin(t))) for t in [i * math.pi / 16 for i in range(17)]]
    tube(b, 'gunmetal', bail, 0.018, 8, col=(0.25, 0.25, 0.25))


def skillet(b, c, r=0.45, angle=0.0):
    c = Vector(c); u = Vector((math.cos(angle), math.sin(angle), 0)); s = r / 0.45
    revolve(b, 'ironware', c, [(0.0, 0.0), (0.42 * s, 0.0), (0.455 * s, 0.03), (0.475 * s, 0.155), (0.495 * s, 0.17), (0.47 * s, 0.172),
                                (0.448 * s, 0.045), (0.0, 0.035)], 40, col=(1, 1, 1), smooth_n=2)
    tube(b, 'ironware', [c + u * 0.46 * s + Vector((0, 0, 0.14)), c + u * 0.8 * s + Vector((0, 0, 0.17)), c + u * 1.15 * s + Vector((0, 0, 0.19))],
         [0.055, 0.048, 0.05], 10, smooth_n=3, col=(1, 1, 1))


def sugar_bowl(b, c):
    revolve(b, 'whiteware', c, [(0.0, 0.0), (0.12, 0.0), (0.13, 0.02), (0.12, 0.04), (0.19, 0.12), (0.21, 0.25), (0.19, 0.33),
                                 (0.2, 0.345), (0.16, 0.36), (0.1, 0.4), (0.05, 0.42), (0.04, 0.46), (0.06, 0.49), (0.0, 0.5)], 32, col=WHITE, smooth_n=2)


def felt_hat(b, base, up=(0, 0, 1), col=(0.075, 0.06, 0.045)):
    """Wide-brimmed felt hat with a pinched crown."""
    revolve(b, 'felt', base, [(0.0, 0.0), (0.7, 0.0), (0.74, 0.025), (0.72, 0.05), (0.36, 0.06), (0.32, 0.1), (0.31, 0.3),
                              (0.27, 0.37), (0.15, 0.38), (0.0, 0.35)], 36, up=up, col=col, smooth_n=2,
            angmod=lambda i, th: 1.0 - (0.12 * max(0.0, math.cos(th)) ** 4 if i > 12 else 0.0))


# ----------------------------------------------------------------- install
def install(interior_ns):
    """Swap the detailed builders into interior.py's namespace and props.py."""
    import props
    for name in ('lamp', 'lantern', 'plate', 'cup', 'side_chair', 'view_camera', 'coats_on_horns', 'kettle', 'skillet'):
        interior_ns[name] = globals()[name]
    props.antler_rack = antler_rack
    props.rifle = rifle
    props.windsor_rocker = windsor_rocker
