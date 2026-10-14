"""Elkhorn outbuildings, fences, well and corral.
Dimensions: spec/outbuildings_spec.json. Placement: Beaubien-Taylor 1957/59 site plan registered to the house
outline (spec/site_houseft.json). All coordinates in house feet (origin SW outside corner of the house)."""
import math, random
from mathutils import Vector, Matrix
from lib import FT


def m(v):
    return Vector(v) * FT


class Frame:
    """Local building frame: origin (house ft) + rotation about Z (deg, CCW)."""
    def __init__(self, ox, oy, rot=0.0):
        self.o = Vector((ox, oy, 0)); self.R = Matrix.Rotation(math.radians(rot), 3, 'Z')

    def p(self, x, y, z=0.0):
        return self.o + self.R @ Vector((x, y, z))

    def mp(self, x, y, z=0.0):
        return m(self.p(x, y, z))

    def d(self, v):
        return self.R @ Vector(v)


def round_log(b, F, p0, p1, r, rng, mk='rlog', sag=0.0):
    p0 = Vector(p0); p1 = Vector(p1)
    n = max(2, int((p1 - p0).length / 3))
    pts, rad = [], []
    for i in range(n + 1):
        t = i / n
        q = p0.lerp(p1, t) + Vector((0, 0, -sag * math.sin(math.pi * t)))
        q += Vector((rng.uniform(-.03, .03), rng.uniform(-.03, .03), rng.uniform(-.02, .02)))
        pts.append(F.mp(*q)); rad.append(r * FT * (1.06 - 0.12 * t) * rng.uniform(0.96, 1.04))
    g = rng.uniform(0.82, 1.08); prev = b.col; b.col = (g, g, g * rng.uniform(0.95, 1.0))
    b.tube(mk, pts, rad, sides=9, tile=1.0, jitter=0.05, endmk='logend')
    b.col = prev


def log_walls(b, F, W, D, H, r, rng, openings=(), crown=1.0, skip_walls=(), half_walls=None):
    """Saddle-notched round-log pen W (x) by D (y), courses of diameter 2r up to H.
    openings: (wall, a0, a1, z0, z1) with wall in S,N,W,E and a measured along +x (S/N) or +y (W/E)."""
    pitch = 2 * r * 0.88
    nc = int(math.ceil(H / pitch))
    for i in range(nc):
        for wall in ('S', 'N', 'W', 'E'):
            if wall in skip_walls:
                continue
            ew = wall in ('S', 'N')
            z = r + i * pitch + (0 if ew else pitch / 2)
            if z > H + 0.1:
                continue
            if half_walls and wall in half_walls and half_walls[wall][0] <= 0 and z > half_walls[wall][2]:
                pass
            L = W if ew else D
            segs = [[-crown - rng.uniform(0, .4), L + crown + rng.uniform(0, .4)]]
            cut = [(a0, a1) for (w, a0, a1, z0, z1) in openings if w == wall and z0 - r * .6 < z < z1 + r * .6]
            if half_walls and wall in half_walls:
                a0, a1, zt = half_walls[wall]
                if z > zt:
                    cut.append((a0, a1))
            for (c0, c1) in cut:
                new = []
                for s0, s1 in segs:
                    if c1 <= s0 or c0 >= s1:
                        new.append([s0, s1]); continue
                    if c0 > s0: new.append([s0, c0])
                    if c1 < s1: new.append([c1, s1])
                segs = new
            for s0, s1 in segs:
                if s1 - s0 < 0.6:
                    continue
                if wall == 'S': p0, p1 = (s0, r * .2, z), (s1, r * .2, z)
                elif wall == 'N': p0, p1 = (s0, D - r * .2, z), (s1, D - r * .2, z)
                elif wall == 'W': p0, p1 = (r * .2, s0, z), (r * .2, s1, z)
                else: p0, p1 = (W - r * .2, s0, z), (W - r * .2, s1, z)
                round_log(b, F, p0, p1, r, rng)
    # daubing between the logs (recessed clay plane on the wall centre line)
    for wall in ('S', 'N', 'W', 'E'):
        if wall in skip_walls:
            continue
        ew = wall in ('S', 'N'); L = W if ew else D
        zt = H
        def P(a, z):
            if wall == 'S': return F.mp(a, r * .2, z)
            if wall == 'N': return F.mp(a, D - r * .2, z)
            if wall == 'W': return F.mp(r * .2, a, z)
            return F.mp(W - r * .2, a, z)
        cuts = sorted([(a0, a1, z0, z1) for (w, a0, a1, z0, z1) in openings if w == wall])
        if half_walls and wall in half_walls:
            a0, a1, zh = half_walls[wall]; cuts.append((a0, a1, zh, H + 1)); cuts.sort()
        xs = [0.0]
        for c in cuts: xs += [c[0], c[1]]
        xs.append(L)
        for k in range(0, len(xs) - 1):
            a0, a1 = xs[k], xs[k + 1]
            if a1 - a0 < 0.05: continue
            if k % 2 == 0:
                b.quad_auto('chink', [P(a0, 0.1), P(a1, 0.1), P(a1, zt), P(a0, zt)], 0.8)
            else:
                c = cuts[(k - 1) // 2]
                if c[2] > 0.15: b.quad_auto('chink', [P(a0, 0.1), P(a1, 0.1), P(a1, c[2]), P(a0, c[2])], 0.8)
                if c[3] < zt - 0.1: b.quad_auto('chink', [P(a0, c[3]), P(a1, c[3]), P(a1, zt), P(a0, zt)], 0.8)


def board_door(b, F, wall, a0, a1, z0, z1, W, D, rng, ajar=0.0):
    """Plank door set in the wall opening; dark void behind."""
    def P(a, z, o):
        if wall == 'S': return F.mp(a, o, z)
        if wall == 'N': return F.mp(a, D - o, z)
        if wall == 'W': return F.mp(o, a, z)
        return F.mp(W - o, a, z)
    b.quad_auto('interior', [P(a0, z0, 0.6), P(a1, z0, 0.6), P(a1, z1, 0.6), P(a0, z1, 0.6)], 1.0)
    if ajar >= 1:
        return
    nb = max(2, int((a1 - a0) / 0.6))
    for k in range(nb):
        q0 = a0 + (a1 - a0) * k / nb; q1 = a0 + (a1 - a0) * (k + 1) / nb - 0.02
        b.quad_auto('door', [P(q0, z0 + .05, 0.25), P(q1, z0 + .05, 0.25), P(q1, z1 - .05, 0.25), P(q0, z1 - .05, 0.25)], 1.2, grain=None)


def window_hole(b, F, wall, a0, a1, z0, z1, W, D):
    def P(a, z, o):
        if wall == 'S': return F.mp(a, o, z)
        if wall == 'N': return F.mp(a, D - o, z)
        if wall == 'W': return F.mp(o, a, z)
        return F.mp(W - o, a, z)
    b.quad_auto('glass', [P(a0, z0, 0.3), P(a1, z0, 0.3), P(a1, z1, 0.3), P(a0, z1, 0.3)], 1.0)
    for (q0, q1, s0, s1) in ((a0 - .15, a1 + .15, z0 - .15, z0), (a0 - .15, a1 + .15, z1, z1 + .15),
                             (a0 - .15, a0, z0, z1), (a1, a1 + .15, z0, z1), ((a0 + a1) / 2 - .03, (a0 + a1) / 2 + .03, z0, z1)):
        b.quad_auto('sash', [P(q0, s0, 0.2), P(q1, s0, 0.2), P(q1, s1, 0.2), P(q0, s1, 0.2)], 1.0)


def sod_roof(b, F, x0, x1, y0, y1, ridge_axis, pitch, z_eave, rng, thick=0.7, poles=True, pole_r=0.22, pole_step=2.0):
    """Low gable of poles + brush + sod. ridge_axis 'y': ridge runs along y at x mid; 'x': ridge along x."""
    t = math.tan(math.radians(pitch))
    if ridge_axis == 'y':
        xm = (x0 + x1) / 2; zr = z_eave + (xm - x0) * t
        def Z(x, y): return z_eave + (min(x - x0, x1 - x)) * t
    else:
        ym = (y0 + y1) / 2; zr = z_eave + (ym - y0) * t
        def Z(x, y): return z_eave + (min(y - y0, y1 - y)) * t
    # sod top surface as a lumpy grid
    nx = max(2, int((x1 - x0) / 2)); ny = max(2, int((y1 - y0) / 2))
    grid = {}
    for i in range(nx + 1):
        for j in range(ny + 1):
            x = x0 + (x1 - x0) * i / nx; y = y0 + (y1 - y0) * j / ny
            edge = i in (0, nx) or j in (0, ny)
            z = Z(x, y) + thick + (0 if edge else rng.uniform(-0.08, 0.12))
            grid[(i, j)] = F.mp(x, y, z)
    for i in range(nx):
        for j in range(ny):
            b.quad_auto('sod', [grid[(i, j)], grid[(i + 1, j)], grid[(i + 1, j + 1)], grid[(i, j + 1)]], 2.0)
    # underside (poles / brush) and edge band of sod
    under = 'soffit'
    corners = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
    if ridge_axis == 'y':
        mid = [(xm, y0), (xm, y1)]
        b.quad_auto(under, [F.mp(x0, y0, Z(x0, y0)), F.mp(xm, y0, zr), F.mp(xm, y1, zr), F.mp(x0, y1, Z(x0, y1))][::-1], 1.5)
        b.quad_auto(under, [F.mp(xm, y0, zr), F.mp(x1, y0, Z(x1, y0)), F.mp(x1, y1, Z(x1, y1)), F.mp(xm, y1, zr)][::-1], 1.5)
        prof = [(x0, Z(x0, 0)), (xm, zr), (x1, Z(x1, 0))]
        for yy, s in ((y0, 1), (y1, -1)):
            for (a, za), (c, zc) in zip(prof[:-1], prof[1:]):
                q = [F.mp(a, yy, za), F.mp(c, yy, zc), F.mp(c, yy, zc + thick), F.mp(a, yy, za + thick)]
                b.quad_auto('sod', q if s > 0 else q[::-1], 1.5)
        for xx in (x0, x1):
            q = [F.mp(xx, y0, Z(xx, y0)), F.mp(xx, y1, Z(xx, y1)), F.mp(xx, y1, Z(xx, y1) + thick), F.mp(xx, y0, Z(xx, y0) + thick)]
            b.quad_auto('sod', q, 1.5)
        if poles:   # pole rafters, ends showing under the eaves
            y = y0 + 0.6
            while y < y1 - 0.3:
                for (xa, xb) in ((x0 - 0.15, xm), (xm, x1 + 0.15)):
                    round_log(b, F, (xa, y, Z(max(xa, x0), y) - pole_r), (xb, y, Z(min(xb, x1), y) - pole_r), pole_r, rng, mk='pole')
                y += pole_step * rng.uniform(0.85, 1.15)
    else:
        b.quad_auto(under, [F.mp(x0, y0, Z(x0, y0)), F.mp(x1, y0, Z(x1, y0)), F.mp(x1, ym, zr), F.mp(x0, ym, zr)], 1.5)
        b.quad_auto(under, [F.mp(x0, ym, zr), F.mp(x1, ym, zr), F.mp(x1, y1, Z(x1, y1)), F.mp(x0, y1, Z(x0, y1))], 1.5)
        prof = [(y0, Z(0, y0)), (ym, zr), (y1, Z(0, y1))]
        for xx, s in ((x0, 1), (x1, -1)):
            for (a, za), (c, zc) in zip(prof[:-1], prof[1:]):
                q = [F.mp(xx, a, za), F.mp(xx, c, zc), F.mp(xx, c, zc + thick), F.mp(xx, a, za + thick)]
                b.quad_auto('sod', q, 1.5)
        for yy in (y0, y1):
            q = [F.mp(x0, yy, Z(x0, yy)), F.mp(x1, yy, Z(x1, yy)), F.mp(x1, yy, Z(x1, yy) + thick), F.mp(x0, yy, Z(x0, yy) + thick)]
            b.quad_auto('sod', q, 1.5)
        if poles:
            x = x0 + 0.6
            while x < x1 - 0.3:
                for (ya, yb) in ((y0 - 0.15, ym), (ym, y1 + 0.15)):
                    round_log(b, F, (x, ya, Z(x, max(ya, y0)) - pole_r), (x, yb, Z(x, min(yb, y1)) - pole_r), pole_r, rng, mk='pole')
                x += pole_step * rng.uniform(0.85, 1.15)
    return Z


def gable_fill(b, F, W, D, z_eave, Z, ridge_axis, r):
    """Close the gable triangles above the top log with short vertical logs (shown as a board/daub fill)."""
    if ridge_axis == 'y':
        xm = W / 2
        for yy in (r * .2, D - r * .2):
            pts = [F.mp(0, yy, z_eave), F.mp(W, yy, z_eave), F.mp(xm, yy, Z(xm, 0) - 0.05)]
            b.quad_auto('rlog', pts, 1.2, grain=None)
    else:
        ym = D / 2
        for xx in (r * .2, W - r * .2):
            pts = [F.mp(xx, 0, z_eave), F.mp(xx, D, z_eave), F.mp(xx, ym, Z(0, ym) - 0.05)]
            b.quad_auto('rlog', pts, 1.2, grain=None)


# ------------------------------------------------------------------ buildings
def barn(b, rng):
    """Two 20x16 stables + 12 ft open bay (Sewall, Dec 20 1885). SW corner at house (-113, 183)."""
    F = Frame(-113.0, 183.0, 0.0)
    r, H = 0.46, 7.0
    ops_w = [('S', 3.0, 6.5, 0, 6.5)]
    ops_e = [('S', 15.5, 19.0, 0, 6.5), ('E', 7.0, 9.0, 4.2, 5.7)]
    log_walls(b, Frame(*(F.p(0, 0)[:2]), 0), 20, 16, H, r, rng, ops_w)
    log_walls(b, Frame(*(F.p(32, 0)[:2]), 0), 20, 16, H, r, rng, ops_e)
    board_door(b, F, 'S', 3.0, 6.5, 0, 6.5, 52, 16, rng)
    board_door(b, Frame(*(F.p(32, 0)[:2]), 0), 'S', 15.5, 19.0, 0, 6.5, 20, 16, rng)
    b.quad_auto('interior', [F.mp(52 - 0.4, 7.0, 4.2), F.mp(52 - 0.4, 9.0, 4.2), F.mp(52 - 0.4, 9.0, 5.7), F.mp(52 - 0.4, 7.0, 5.7)][::-1], 1.0)
    # closed back of the bay: close-set vertical posts + a log laid against them
    x = 20.6
    while x < 31.5:
        d = rng.uniform(0.4, 0.9)
        round_log(b, F, (x, 15.6, 0), (x, 15.6, H + 0.3), d / 2, rng, mk='rlog')
        x += d + 0.02
    round_log(b, F, (20.3, 16.1, 0.4), (31.7, 16.1, 0.4), 0.4, rng)
    # roof: low gable, ridge N-S over the centre of the bay; eave sits right on the wall tops
    ze = H + 0.15
    Z = sod_roof(b, F, -1.5, 53.5, -3.0, 17.0, 'y', 4.5, ze + 0.42, rng, pole_step=1.6, thick=0.55, poles=False)
    # big N-S log stringers following the slope (ends show along the south eave every ~8-11 ft)
    for xs in (-1.0, 8.0, 16.5, 21.0, 26.0, 31.0, 35.5, 44.0, 53.0):
        zz = Z(xs, 0) + 0.42 - 0.42
        round_log(b, F, (xs, -3.2, zz), (xs, 17.2, zz), 0.42, rng, sag=0.08)
    # E-W poles under the sod between stringers (visible from inside the bay)
    for ys in [-2.5 + 1.25 * k for k in range(16)]:
        for (xa, xb) in ((-1.5, 26.0), (26.0, 53.5)):
            round_log(b, F, (xa, ys, Z(xa, ys) - 0.16), (xb, ys, Z(xb, ys) - 0.16), 0.15, rng, mk='pole')
    # front plate across the bay and ridge plate/posts at the back
    round_log(b, F, (19.0, 0.2, H - 0.1), (33.0, 0.2, H - 0.1), 0.42, rng)
    for xs in (20.0, 32.0):
        for ys in (0.4, 15.6):
            pass
    # blocking logs closing the triangles between the stable wall tops and the sloping roof (S and N fronts)
    for (x0, x1) in ((0.0, 20.0), (32.0, 52.0)):
        for yy in (0.1, 15.9):
            pts = [F.mp(x0, yy, H), F.mp(x1, yy, H), F.mp(x1, yy, Z(x1, 0) + 0.3), F.mp(x0, yy, Z(x0, 0) + 0.3)]
            b.quad_auto('rlog', pts, 1.0, grain=F.d((1, 0, 0)))
    for xs in (20.0, 32.0):     # bay-side stable walls carried up under the stringers
        for yy in (0.1, 15.9):
            pass
    # wagon in the bay is omitted; hay stack on the roof over the east part
    hay(b, F, (31.0, 7.5, Z(31.0, 7.0) + 0.8), 19, 10, 7.0, rng)
    # pole ladder leaning on the east stable front
    for s in (-0.7, 0.7):
        round_log(b, F, (35 + s, -2.6, 0), (35 + s, -0.6, 12.0), 0.16, rng, mk='pole')
    for k in range(1, 13):
        z = k * 0.88; yy = -2.6 + 2.0 * z / 12
        round_log(b, F, (34.2, yy - .05, z), (35.8, yy - .05, z), 0.07, rng, mk='pole')


def hay(b, F, c, w, d, h, rng):
    """Stacked prairie hay as in T.R.'s stables photograph: a long loaf with steep, shaggy sides, a rounded
    settled top, straw hanging over the eaves of the stack, loose tufts, and the stacking pole left in it."""
    nu, nv = 28, 10
    cx, cy, cz = c
    noise = [[rng.uniform(-1, 1) for i in range(nu)] for j in range(nv + 1)]
    rings = []
    for j in range(nv + 1):
        t = j / nv                                      # 0 = base, 1 = crown
        ring = []
        for i in range(nu):
            ph = 2 * math.pi * i / nu
            # superellipse plan (loaf), bulging just above the base, drawing in to a rounded crown
            bulge = 1.06 if t < 0.25 else 1.0
            prof = (1 - t ** 1.6) ** 0.75 * bulge
            sx = math.copysign(abs(math.cos(ph)) ** 0.6, math.cos(ph)); sy = math.copysign(abs(math.sin(ph)) ** 0.6, math.sin(ph))
            n = 1 + 0.06 * noise[j][i] + 0.03 * math.sin(i * 1.7 + j)
            x = sx * w / 2 * prof * n; y = sy * d / 2 * prof * n
            peak = 1.0 + 0.18 * math.cos(ph) * (1 if math.cos(ph) < 0 else 0.4)   # higher toward the west end, as in the photo
            z = h * t * peak * (1 + 0.05 * noise[j][(i + 3) % nu]) - (0.25 if t == 0 else 0)
            ring.append(Vector((cx + x, cy + y, cz + z)))
        rings.append(ring)
    # body with UVs running down-slope (strands vertical in the texture)
    per = sum((rings[0][i] - rings[0][(i + 1) % nu]).length for i in range(nu))
    for j in range(nv):
        for i in range(nu):
            i2 = (i + 1) % nu
            u0 = i / nu * per / 4.0; u1 = (i + 1) / nu * per / 4.0
            v0 = (nv - j) / nv * h / 3.0; v1 = (nv - j - 1) / nv * h / 3.0
            g = rng.uniform(0.85, 1.1); b.col = (g, g, g * 0.97)
            b.face('hay', [F.mp(*rings[j][i]), F.mp(*rings[j][i2]), F.mp(*rings[j + 1][i2]), F.mp(*rings[j + 1][i])],
                   [(u0, v0), (u1, v0), (u1, v1), (u0, v1)])
    b.col = (1, 1, 1)
    cen = Vector((cx, cy, cz + h)); b.face('hay', [F.mp(*p) for p in reversed(rings[-1])], [(0.5 + 0.5 * math.cos(2 * math.pi * k / nu), 0.5 + 0.5 * math.sin(2 * math.pi * k / nu)) for k in range(nu)][::-1])
    # hanging fringe: strand cards draped over the bulge and below the base
    for j in (0, 1, 2, 3, 4, 5, 6):
        for i in range(nu):
            if rng.random() < 0.15: continue
            p0 = rings[j][i]; p1 = rings[j][(i + 1) % nu]
            out = Vector((p0.x - cx, p0.y - cy, 0)).normalized() * 0.15
            L = rng.uniform(0.9, 2.2) * (1.3 if j <= 1 else 1.0)
            mid = (p0 + p1) / 2; half = (p1 - p0) * rng.uniform(0.6, 0.9)
            top0, top1 = mid - half + out, mid + half + out
            b.face('straw', [F.mp(*(top0 - Vector((0, 0, L)) + out * 1.5)), F.mp(*(top1 - Vector((0, 0, L)) + out * 1.5)), F.mp(*top1), F.mp(*top0)],
                   [(0, 1), (1, 1), (1, 0), (0, 0)])
    # loose tufts sticking out all over
    for k in range(260):
        j = rng.randint(1, nv - 1); i = rng.randrange(nu)
        p = rings[j][i]; nrm = Vector((p.x - cx, p.y - cy, (p.z - cz) * 0.8)).normalized()
        side = nrm.cross(Vector((0, 0, 1))).normalized() if abs(nrm.z) < 0.95 else Vector((1, 0, 0))
        s = rng.uniform(0.15, 0.35); L = rng.uniform(0.9, 1.8)
        tip = p + nrm * L * 0.5 - Vector((0, 0, L))
        b.face('straw', [F.mp(*(tip - side * s)), F.mp(*(tip + side * s)), F.mp(*(p + side * s * 0.6)), F.mp(*(p - side * s * 0.6))],
               [(0, 1), (1, 1), (1, 0), (0, 0)])
    # stacking pole left standing in the stack, leaning, with a fork end
    base = Vector((cx - w * 0.3, cy, cz + h * 0.4)); top = base + Vector((-1.8, -0.5, h * 0.95))
    round_log(b, F, base, top, 0.12, rng, mk='pole')
    for s in (-0.25, 0.25):
        round_log(b, F, top, top + Vector((-0.6, s, 1.3)), 0.06, rng, mk='iron')

def utility_shed(b, rng):
    """Storehouse 16.5 x 25, low sod gable facing south; door S centre (conjectural); woodpile in front."""
    F = Frame(-46.9, 58.1, 0.0)
    W, D, H, r = 16.5, 25.0, 7.0, 0.44
    ops = [('S', 6.75, 9.75, 0, 6.25), ('E', 1.5, 3.5, 3.6, 5.6)]
    log_walls(b, F, W, D, H, r, rng, ops)
    board_door(b, F, 'S', 6.75, 9.75, 0, 6.25, W, D, rng)
    window_hole(b, F, 'E', 1.5, 3.5, 3.6, 5.6, W, D)
    Z = sod_roof(b, F, -2.0, W + 2.0, -2.5, D + 1.0, 'y', 10, H + 0.5, rng)
    gable_fill(b, F, W, D, H + 0.4, Z, 'y', r)
    # pile of cottonwood branches in front (P_CORRALS), ~20 ft long x 8 ft high
    for k in range(70):
        y0 = rng.uniform(-14, -4); x0 = rng.uniform(-3, 17); z0 = rng.uniform(0, 1) ** 1.6 * 6.5
        L = rng.uniform(6, 16); a = rng.uniform(-0.5, 0.5) + (0 if rng.random() < .7 else math.pi / 2)
        dx, dy = math.cos(a) * L, math.sin(a) * L * 0.4
        mid = (x0 + dx / 2, y0 + dy / 2, z0 + rng.uniform(0.3, 1.2))
        r0 = rng.uniform(0.12, 0.35)
        pts = [F.mp(x0, y0, z0), F.mp(*mid), F.mp(x0 + dx, y0 + dy, max(0.1, z0 - rng.uniform(0, 1.5)))]
        b.tube('bark', pts, [r0 * FT, r0 * .7 * FT, r0 * .3 * FT], sides=6, tile=1.0)


def chicken_coop(b, rng):
    """Stockade of close-set cedar posts against the W wall of the shed (TAY59), unroofed."""
    F = Frame(-60.4, 63.6, 0.0)
    W, D = 13.5, 19.5
    for (p0, p1, gap) in (((0, 0), (W, 0), None), ((0, 0), (0, D), None), ((0, D), (W, D), None),
                          ((W, 0), (W, D - 3.33), None)):
        L = math.dist(p0, p1); a = 0.0
        while a < L:
            d = rng.uniform(0.3, 0.55)
            t = (a + d / 2) / L
            x = p0[0] + (p1[0] - p0[0]) * t; y = p0[1] + (p1[1] - p0[1]) * t
            h = rng.uniform(5.0, 6.0)
            b.tube('post', [F.mp(x, y, 0), F.mp(x, y, h)], [d / 2 * FT, d / 2.2 * FT], sides=6, tile=1.0, endmk='logend')
            a += d + 0.03
    # nest boxes against the shed wall
    b.box('board', F.mp(W - 4.2, 12, 0), F.mp(W - 0.1, 15, 2.0), 1.0)


def blacksmith(b, rng):
    """33 x 16 two-room log shop, flat sod gable, brick forge chimney. Map corners -> rotated 17.8 deg."""
    rot = 17.8
    c = Vector((133.3, -225.1, 0))
    R = Matrix.Rotation(math.radians(rot), 3, 'Z')
    o = c - R @ Vector((8.0, 16.5, 0))
    F = Frame(o.x, o.y, rot)
    W, D, H, r = 16.0, 33.0, 6.75, 0.42
    ops = [('S', 11.5, 14.2, 0, 6.0), ('N', 11.0, 14.5, 0, 6.0), ('W', 12.2, 14.0, 0, 6.0),
           ('W', 19.0, 21.0, 3.2, 5.2), ('W', 26.0, 28.0, 3.2, 5.2), ('N', 4.0, 6.0, 3.2, 5.2)]
    log_walls(b, F, W, D, H, r, rng, ops, crown=0.7, half_walls={'E': (0.6, 11.0, 3.4)})
    for (w, a0, a1, z0, z1) in ops:
        if z0 == 0: board_door(b, F, w, a0, a1, z0, z1, W, D, rng)
        else: window_hole(b, F, w, a0, a1, z0, z1, W, D)
    # partition logs 11.5 ft from S, ends visible in E wall
    k = 0
    z = r
    while z < H:
        round_log(b, F, (-0.4, 11.5, z), (W + 0.5, 11.5, z), r * 0.95, rng)
        z += 2 * r * 0.88
    b.quad_auto('interior', [F.mp(0.3, 0.4, 0.05), F.mp(W - .3, 0.4, 0.05), F.mp(W - .3, D - .4, 0.05), F.mp(0.3, D - .4, 0.05)], 1.0)
    Z = sod_roof(b, F, -1.0, W + 1.0, -1.0, D + 1.0, 'y', 8, H + 0.45, rng)
    gable_fill(b, F, W, D, H + 0.35, Z, 'y', r)
    # forge chimney (brick), north room
    zt = Z(8.0, 25.0) + 0.7 + 2.5
    b.box('brick', F.mp(7.33, 24.33, 0), F.mp(8.67, 25.67, zt), 3.0, 2)
    b.box('interior', F.mp(7.6, 24.6, zt - .4), F.mp(8.4, 25.4, zt + .005), 1.0)


def dugout(b, rng):
    """T.R.'s first shack: palisade of upright posts cut into the bank, earth on N/S/W, east front with
    a 5 ft overhang on 3 posts (Beaubien 1957; TAY59 fig.3)."""
    rot = 17.8
    c = Vector((165.4, -255.2, 0)); R = Matrix.Rotation(math.radians(rot), 3, 'Z')
    o = c - R @ Vector((7.7, 6.7, 0))
    F = Frame(o.x, o.y, rot)
    W, D, H = 15.4, 13.4, 6.5     # outside (14 x 12 inside + post walls)
    # palisade walls
    for (p0, p1) in (((0, 0), (W, 0)), ((0, D), (W, D)), ((0, 0), (0, D)), ((W, 0), (W, D))):
        L = math.dist(p0, p1); a = 0.0
        while a < L:
            d = rng.uniform(0.67, 1.0)
            t = min(1, (a + d / 2) / L)
            x = p0[0] + (p1[0] - p0[0]) * t; y = p0[1] + (p1[1] - p0[1]) * t
            if p0[0] == W and p1[0] == W and 5.45 < y < 7.95:
                a += d; continue        # doorway 2'6" in the east wall
            b.tube('rlog', [F.mp(x, y, -0.2), F.mp(x, y, H)], [d / 2 * FT, d / 2.1 * FT], sides=7, tile=1.0, endmk='logend')
            a += d + 0.01
    b.quad_auto('interior', [F.mp(W - .2, 5.45, 0), F.mp(W - .2, 7.95, 0), F.mp(W - .2, 7.95, 6.0), F.mp(W - .2, 5.45, 6.0)][::-1], 1.0)
    board_door(b, F, 'E', 5.45, 7.95, 0, 6.0, W, D, rng, ajar=1)
    # front posts carrying the overhang
    for y in (0.3, 6.7, D - 0.3):
        round_log(b, F, (W + 4.8, y, 0), (W + 4.8, y, H + 0.1), 0.35, rng)
    for y in (0.0, D / 2, D):     # 3 E-W beams
        round_log(b, F, (-1.0, y, H + 0.4 + (0.9 if y == D / 2 else 0)), (W + 5.4, y, H + 0.1 + (0.9 if y == D / 2 else 0)), 0.45, rng)
    sod_roof(b, F, -1.0, W + 5.5, -1.0, D + 1.0, 'x', 12, H + 0.7, rng, thick=0.8)
    # bank: earth berm on N, S and W sides
    berm(b, F, -9.0, W + 0.5, -7.0, D + 7.0, 0.0, W, D, H + 0.3, rng)
    # retaining logs either side of the front
    for k in range(4):
        z = 0.4 + k * 0.75
        round_log(b, F, (W + 0.2, -6.0 + k, z), (W + 0.2, -0.3, z), 0.38, rng)
        round_log(b, F, (W + 0.2, D + 0.3, z), (W + 0.2, D + 6.0 - k, z), 0.38, rng)


def berm(b, F, x0, x1, y0, y1, ix0, ix1, iy1, h, rng):
    """Earth bank around a dugout: flat top at h, sloping down outwards; open to the east."""
    top = [(ix0 - 0.3, -0.3), (ix1, -0.3), (ix1, iy1 + 0.3), (ix0 - 0.3, iy1 + 0.3)]
    out = [(x0, y0), (x1 + 6, y0), (x1 + 6, y1), (x0, y1)]
    nT = [F.mp(x, y, h) for (x, y) in top]
    nO = [F.mp(x, y, 0) for (x, y) in out]
    # west/north/south slopes (outer ring -> ring at h around the walls, offset 2 ft)
    mid = [(ix0 - 3, -3), (ix1 + 1, -3), (ix1 + 1, iy1 + 3), (ix0 - 3, iy1 + 3)]
    nM = [F.mp(x, y, h + rng.uniform(-.2, .2)) for (x, y) in mid]
    for i in (0, 2, 3):
        j = (i + 1) % 4
        b.quad_auto('grass', [nO[i], nO[j], nM[j], nM[i]], 2.0)
        b.quad_auto('grass', [nM[i], nM[j], nT[j], nT[i]], 2.0)


def well(b, rng):
    """Stone-lined oval shaft 4'6" with a rectangular log curb (TAY59 p.33). Map position."""
    F = Frame(-37.9, -10.05, 0.0)
    W, D = 6.0, 5.5
    for k in range(3):
        z = 0.38 + k * 0.72
        if k % 2 == 0:
            round_log(b, F, (-0.6, 0.38, z), (W + 0.6, 0.38, z), 0.38, rng)
            round_log(b, F, (-0.6, D - 0.38, z), (W + 0.6, D - 0.38, z), 0.38, rng)
        else:
            round_log(b, F, (0.38, -0.6, z), (0.38, D + 0.6, z), 0.38, rng)
            round_log(b, F, (W - 0.38, -0.6, z), (W - 0.38, D + 0.6, z), 0.38, rng)
    # shaft: dark disc + stone lip
    cx, cy = W / 2, D / 2
    ring = [F.mp(cx + 2.25 * math.cos(a) * 1.0, cy + 2.0 * math.sin(a), 0.6) for a in [i * math.pi / 8 for i in range(16)]]
    b.quad_auto('interior', ring, 1.0)
    for i in range(16):
        a = i * math.pi / 8
        from house import rock
        rock(b, (F.p(cx + 2.35 * math.cos(a), cy + 2.1 * math.sin(a))[0], F.p(cx + 2.35 * math.cos(a), cy + 2.1 * math.sin(a))[1], 0.45),
             (rng.uniform(.7, 1.0), rng.uniform(.5, .8), .5), rng)
    # plank lid over half the opening
    b.box('deck', F.mp(0.5, cy - 0.1, 2.5), F.mp(W - 0.5, D - 0.5, 2.62), 1.2, 0)


def corral(b, rng):
    """High circular horse corral, 62 ft dia, 15 paired-post sets, snubbing post, 49.5 ft wing on the east
    (T.R. 1888; Beaubien 1957). Paired posts sandwich 6 rails; top rail 7 ft (conjectural)."""
    cx, cy = -163.6, -354.5
    F = Frame(cx, cy, 0.0)
    R = 30.4
    n = 15
    gate_a = 0.0       # gate faces east
    angs = [gate_a + 2 * math.pi * (k + 0.5) / n for k in range(n)]
    rails = [1.3, 2.4, 3.5, 4.6, 5.8, 7.0]
    for a in angs:
        for dr in (-0.35, 0.35):
            x, y = (R + dr) * math.cos(a), (R + dr) * math.sin(a)
            round_log(b, F, (x, y, 0), (x, y, 7.5 + rng.uniform(-.2, .3)), 0.26, rng, mk='post')
    for k in range(n):
        a0, a1 = angs[k], angs[(k + 1) % n] + (2 * math.pi if k == n - 1 else 0)
        if k == n - 1:
            continue   # gate opening between last and first set
        for z in rails:
            pts = []
            for s in range(5):
                a = a0 - 0.02 + (a1 - a0 + 0.04) * s / 4
                pts.append(F.mp(R * math.cos(a), R * math.sin(a), z + rng.uniform(-.06, .06) - 0.15 * math.sin(math.pi * s / 4)))
            b.tube('pole', pts, rng.uniform(.14, .2) * FT, sides=6, tile=1.0)
    # gate (pole gate, closed)
    g0, g1 = angs[-1], angs[0] + 2 * math.pi
    p0 = Vector((R * math.cos(g0), R * math.sin(g0))); p1 = Vector((R * math.cos(g1), R * math.sin(g1)))
    for z in rails[:5]:
        round_log(b, F, (p0.x, p0.y, z), (p1.x, p1.y, z), 0.13, rng, mk='pole')
    # wing: from the north gate post eastward, 3 more pairs of posts
    wx0, wy0 = p1.x, p1.y
    for k in range(1, 4):
        x = wx0 + 49.5 * k / 3 * math.cos(math.radians(18)); y = wy0 + 49.5 * k / 3 * math.sin(math.radians(18))
        for dr in (-0.35, 0.35):
            round_log(b, F, (x, y + dr, 0), (x, y + dr, 6.5), 0.25, rng, mk='post')
    ex, ey = wx0 + 49.5 * math.cos(math.radians(18)), wy0 + 49.5 * math.sin(math.radians(18))
    for z in rails[:5]:
        round_log(b, F, (wx0, wy0, z), (ex, ey, z), 0.15, rng, mk='pole', sag=0.25)
    # snubbing post
    round_log(b, F, (0, 0, 0), (0, 0, 5.0), 0.5, rng, mk='rlog')


def fence_single(b, pts, rng, h=4.5, rails=(1.0, 2.0, 3.0, 4.0), step=10.0, skip=()):
    """House enclosure: single round posts at 10 ft with four bars nailed on the outside face (TAY59)."""
    F = Frame(0, 0, 0)
    for i in range(len(pts) - 1):
        if i in skip:
            continue
        p0, p1 = Vector(pts[i]), Vector(pts[i + 1])
        L = (p1 - p0).length; n = max(1, round(L / step))
        nrm = Vector((-(p1 - p0).y, (p1 - p0).x)).normalized() * 0.25
        for k in range(n + 1):
            q = p0.lerp(p1, k / n)
            round_log(b, F, (q.x, q.y, 0), (q.x, q.y, h + rng.uniform(-.15, .15)), 0.19, rng, mk='post')
        for z in rails:
            for k in range(n):
                a = p0.lerp(p1, k / n) + nrm; c = p0.lerp(p1, (k + 1) / n) + nrm
                round_log(b, F, (a.x, a.y, z), (c.x, c.y, z + rng.uniform(-.08, .08)), 0.12, rng, mk='pole')


def fence_paired(b, pts, rng, h=6.0, rails=(1.2, 2.3, 3.4, 4.5, 5.6), step=10.0, skip=()):
    """Corral fence: pairs of cedar posts at 10 ft, five poles sandwiched between each pair (TAY59 p.57)."""
    F = Frame(0, 0, 0)
    for i in range(len(pts) - 1):
        if i in skip:
            continue
        p0, p1 = Vector(pts[i]), Vector(pts[i + 1])
        L = (p1 - p0).length; n = max(1, round(L / step))
        nrm = Vector((-(p1 - p0).y, (p1 - p0).x)).normalized() * 0.33
        for k in range(n + 1):
            q = p0.lerp(p1, k / n)
            for s in (-1, 1):
                round_log(b, F, (q.x + nrm.x * s, q.y + nrm.y * s, 0), (q.x + nrm.x * s, q.y + nrm.y * s, h + .4 + rng.uniform(-.2, .2)), 0.24, rng, mk='post')
        for z in rails:
            for k in range(n):
                a = p0.lerp(p1, k / n); c = p0.lerp(p1, (k + 1) / n)
                round_log(b, F, (a.x, a.y, z), (c.x, c.y, z + rng.uniform(-.1, .1)), rng.uniform(.13, .19), rng, mk='pole', sag=0.12)


def build_outbuildings(b, rng):
    b.group = 'barn'; barn(b, rng)
    b.group = 'shed'; utility_shed(b, rng); chicken_coop(b, rng)
    b.group = 'blacksmith'; blacksmith(b, rng)
    b.group = 'dugout'; dugout(b, rng)
    b.group = 'well'; well(b, rng)
    b.group = 'corral'; corral(b, rng)
    b.group = 'fences'
    # house enclosure ~110 x 105 ft around house, well, shed (TAY59); gap for the path on the east
    fence_single(b, [(48, -16), (48, 22), (48, 30), (48, 90), (-62, 90), (-62, -16), (48, -16)], rng, skip=(1,))
    # corral fence in front of the barn (~100 ft square in TAY59; fitted between enclosure and barn)
    fence_paired(b, [(-113, 183), (-140, 183), (-140, 96), (-64, 96), (-64, 183), (-61, 183)], rng, skip=(4,))
