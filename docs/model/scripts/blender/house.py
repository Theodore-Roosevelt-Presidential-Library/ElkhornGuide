"""Elkhorn ranch house, 1886 state. Coordinates: feet in the spec frame (origin SW outside corner,
X east, Y north, Z up from grade) converted to metres here."""
import math, random
from mathutils import Vector
from lib import FT, IN

T = 10 / 12.0           # log thickness ft
LOGH = 12.5 / 12.0      # log face height
PITCH = 13.25 / 12.0    # course pitch
Z0 = 0.5                # sill bottom
PLATE = Z0 + 8 * PITCH  # 9.333
CROWN = 1.0             # corner projection
TAN = math.tan(math.radians(30))
RIDGE_X = 15.0
SHOW_INTERIOR = False   # True: no dark stand-in planes behind windows/doors; interior faces of logs in fresh wood
ROOF_RAISE = 0.5        # rafter depth above plate at the wall face
def roof_z(x):          # roof deck top (ft)
    return PLATE + ROOF_RAISE + (15.0 - abs(x - RIDGE_X)) * TAN

def m(v):  # ft tuple -> m Vector
    return Vector((v[0] * FT, v[1] * FT, v[2] * FT))

# ------------------------------------------------------------------ walls
WALLS = {
    # name: origin (outer corner, ft), u axis (along), n axis (outward), length
    'E': ((30, 0, 0), (0, 1, 0), (1, 0, 0), 60),
    'W': ((0, 0, 0), (0, 1, 0), (-1, 0, 0), 60),
    'S': ((0, 0, 0), (1, 0, 0), (0, -1, 0), 30),
    'N': ((0, 60, 0), (1, 0, 0), (0, 1, 0), 30),
}
WIN = dict(w=2.333, sill=2.708, head=7.125)
DOOR = dict(w=2.83, sill=1.604, head=8.229)
OPENINGS = {
    'E': [('w', 5.6), ('w', 15.5), ('d', 21.0), ('w', 27.0), ('w', 36.0), ('w', 45.2), ('w', 54.9)],
    'S': [('w', 6.5), ('d', 16.0), ('w', 25.0)],
    'W': [('w', 5.5), ('w', 18.0), ('d', 27.0), ('w', 31.5), ('w', 40.0), ('w', 53.0)],
    'N': [('w', 6.5), ('w', 23.5)],
}


def wpt(wall, a, o, z):
    org, u, n, L = WALLS[wall]
    return Vector(org) + Vector(u) * a + Vector(n) * o + Vector((0, 0, z))


def hewn_log(b, mk, p0, p1, up, out, w, h, rng, endmk='logend', segs_per_ft=0.6, tile=1.0, inner=None):
    """Hewn log with waney (chamfered, irregular) corners. p0,p1 centre-line ends in ft."""
    p0, p1 = Vector(p0), Vector(p1)
    L = (p1 - p0).length
    g = rng.uniform(0.78, 1.06); prev_col = b.col
    b.col = (g, g * rng.uniform(0.98, 1.01), g * rng.uniform(0.95, 1.0))
    ax = (p1 - p0).normalized()
    up = Vector(up).normalized(); out = Vector(out).normalized()
    nseg = max(2, int(L * segs_per_ft))
    rings = []
    bow = rng.uniform(-0.04, 0.04); bow2 = rng.uniform(-0.03, 0.03)
    for i in range(nseg + 1):
        t = i / nseg
        c = p0 + (p1 - p0) * t
        s = math.sin(math.pi * t)
        c = c + out * bow * s + up * bow2 * s
        cw = rng.uniform(0.02, 0.16) if rng.random() < 0.6 else rng.uniform(0.0, 0.04)
        ch = rng.uniform(0.02, 0.12)
        ciw = rng.uniform(0.02, 0.08)
        hh = h / 2 * rng.uniform(0.97, 1.0); ww = w / 2
        # octagon in (out, up): start outer-bottom, ccw seen from p1
        sec = [(ww, -hh + ch), (ww, hh - cw), (ww - cw * 0.8, hh), (-ww + ciw, hh),
               (-ww, hh - ciw), (-ww, -hh + ciw), (-ww + ciw, -hh), (ww - ch * 0.8, -hh)]
        rings.append([m(c + out * a + up * bb) for a, bb in sec])
    # faces
    import lib
    perim = []
    for k in range(8):
        a = Vector(rings[0][k]); bq = Vector(rings[0][(k + 1) % 8]); perim.append((bq - a).length)
    acc = [0]
    for pl in perim:
        acc.append(acc[-1] + pl)
    off = rng.random() * 4
    for i in range(nseg):
        d0 = L * FT * i / nseg; d1 = L * FT * (i + 1) / nseg
        for k in range(8):
            k2 = (k + 1) % 8
            pts = [rings[i][k], rings[i + 1][k], rings[i + 1][k2], rings[i][k2]]
            uv = [(d0 / tile + off, acc[k] / tile), (d1 / tile + off, acc[k] / tile),
                  (d1 / tile + off, acc[k + 1] / tile), (d0 / tile + off, acc[k + 1] / tile)]
            fmk = mk
            if inner and k in (3, 4, 5) and inner[0] <= (d0 + d1) / 2 / FT <= inner[1]:
                fmk = 'ilog'
            b.face(fmk, pts, uv)
    b.quad_auto(endmk, list(reversed(rings[0])), 0.4)
    b.quad_auto(endmk, rings[-1], 0.4)
    b.col = prev_col


def walls(b, rng):
    for wall, (org, u, n, L) in WALLS.items():
        end_wall = wall in ('S', 'N')
        ops = []
        for kind, c in OPENINGS[wall]:
            d = WIN if kind == 'w' else DOOR
            ops.append((c - d['w'] / 2, c + d['w'] / 2, d['sill'], d['head']))
        # course list (bottom z, height)
        courses = []
        if end_wall:
            courses.append((Z0, PITCH / 2 - 0.06))          # half log at bottom
            z = Z0 + PITCH / 2
            for i in range(7):
                courses.append((z, LOGH)); z += PITCH
            courses.append((z, PLATE - z))                   # half log at top to plate height
        else:
            z = Z0
            for i in range(8):
                courses.append((z, LOGH)); z += PITCH
        for ci, (zb, hgt) in enumerate(courses):
            zt = zb + hgt
            # extents along wall incl. crowns
            a0 = -CROWN - rng.uniform(0, 0.25); a1 = L + CROWN + rng.uniform(0, 0.25)
            segs = [[a0, a1]]
            for (o0, o1, s, h) in ops:
                if zt > s + 0.02 and zb < h - 0.02:
                    new = []
                    for (s0, s1) in segs:
                        if o1 <= s0 or o0 >= s1:
                            new.append([s0, s1]); continue
                        if o0 > s0: new.append([s0, o0])
                        if o1 < s1: new.append([o1, s1])
                    segs = new
            for (s0, s1) in segs:
                if s1 - s0 < 0.2:
                    continue
                zc = zb + hgt / 2
                # long walls sit at out=-T/2; end walls the same
                p0 = wpt(wall, s0, -T / 2, zc); p1 = wpt(wall, s1, -T / 2, zc)
                hh = hgt * (1 if hgt > 0.8 else 1)
                inner = (max(0.0, T - s0), L - T - s0) if SHOW_INTERIOR else None
                hewn_log(b, 'log', p0, p1, (0, 0, 1), n, T, hh, rng, inner=inner)
        # chink: recessed slab in the wall plane behind the logs (fills gaps between courses)
        for (s0, s1) in [(0, L)]:
            pts_out = -T / 2 - 0.02
            # split chink around openings
            segs = [[0.0, L]]
            for (o0, o1, s, h) in ops:
                new = []
                for (q0, q1) in segs:
                    if o1 <= q0 or o0 >= q1: new.append([q0, q1]); continue
                    if o0 > q0: new.append([q0, o0])
                    if o1 < q1: new.append([o1, q1])
                segs = new
            for (q0, q1) in segs:
                pts = [m(wpt(wall, q0, -0.25, Z0)), m(wpt(wall, q1, -0.25, Z0)),
                       m(wpt(wall, q1, -0.25, PLATE)), m(wpt(wall, q0, -0.25, PLATE))]
                b.quad_auto('chink', pts if wall in ('E', 'S') else pts, 0.8)
            # pieces above/below openings
            for (o0, o1, s, h) in ops:
                for (za, zb2) in ((Z0, s), (h, PLATE)):
                    if zb2 - za > 0.05:
                        pts = [m(wpt(wall, o0, -0.25, za)), m(wpt(wall, o1, -0.25, za)),
                               m(wpt(wall, o1, -0.25, zb2)), m(wpt(wall, o0, -0.25, zb2))]
                        b.quad_auto('chink', pts, 0.8)
        for kind, c in OPENINGS[wall]:
            if kind == 'w':
                window(b, wall, c, rng)
            else:
                door(b, wall, c, rng)


def wbox(b, mk, wall, a0, a1, o0, o1, z0, z1, tile=1.0, grain=0):
    """Axis box in wall frame: a along wall, o outward, z up."""
    org, u, n, L = WALLS[wall]
    c = wpt(wall, (a0 + a1) / 2, (o0 + o1) / 2, (z0 + z1) / 2)
    b.obox(mk, m(c), (u, n, (0, 0, 1)), ((a1 - a0) / 2 * FT, (o1 - o0) / 2 * FT, (z1 - z0) / 2 * FT), tile, grain)


def window(b, wall, c, rng, w=WIN['w'], sill=WIN['sill'], head=WIN['head'], lights=(3, 2)):
    a0, a1 = c - w / 2, c + w / 2
    cas = 3.5 / 12; ct = 0.9 / 12
    # casing (flat boards on outer face), head + jambs + projecting sill
    wbox(b, 'trim', wall, a0 - cas, a0, 0.0, ct, sill, head, 0.8, 2)
    wbox(b, 'trim', wall, a1, a1 + cas, 0.0, ct, sill, head, 0.8, 2)
    wbox(b, 'trim', wall, a0 - cas, a1 + cas, 0.0, ct, head, head + cas, 0.8, 0)
    wbox(b, 'trim', wall, a0 - cas - 0.08, a1 + cas + 0.08, -0.05, 0.14, sill - 0.12, sill, 0.8, 0)
    # jamb linings (reveal)
    for (x0, x1) in ((a0, a0 + 0.06), (a1 - 0.06, a1)):
        wbox(b, 'board', wall, x0, x1, -T, 0.0, sill, head, 0.8, 2)
    wbox(b, 'board', wall, a0, a1, -T, 0.0, head - 0.06, head, 0.8, 0)
    wbox(b, 'board', wall, a0, a1, -T, 0.0, sill, sill + 0.05, 0.8, 0)
    # two sashes, set back 3 in
    sb = -0.25
    st = 2 / 12; mt = 0.875 / 12
    mid = (sill + head) / 2
    for (z0, z1) in ((sill + 0.05, mid + 0.04), (mid - 0.04, head - 0.06)):
        dz = 0.0 if z1 > mid + 0.1 else 0.06
        o0, o1 = sb - 0.11 - dz, sb - dz
        wbox(b, 'sash', wall, a0 + 0.06, a0 + 0.06 + st, o0, o1, z0, z1)
        wbox(b, 'sash', wall, a1 - 0.06 - st, a1 - 0.06, o0, o1, z0, z1)
        wbox(b, 'sash', wall, a0 + 0.06, a1 - 0.06, o0, o1, z0, z0 + st)
        wbox(b, 'sash', wall, a0 + 0.06, a1 - 0.06, o0, o1, z1 - st, z1)
        ix0, ix1 = a0 + 0.06 + st, a1 - 0.06 - st
        iz0, iz1 = z0 + st, z1 - st
        for k in range(1, lights[0]):
            xx = ix0 + (ix1 - ix0) * k / lights[0]
            wbox(b, 'sash', wall, xx - mt / 2, xx + mt / 2, o0 + 0.02, o1 - 0.02, iz0, iz1)
        for k in range(1, lights[1]):
            zz = iz0 + (iz1 - iz0) * k / lights[1]
            wbox(b, 'sash', wall, ix0, ix1, o0 + 0.02, o1 - 0.02, zz - mt / 2, zz + mt / 2)
        # glass
        org, u, n, L = WALLS[wall]
        go = (o0 + o1) / 2
        pts = [m(wpt(wall, ix0, go, iz0)), m(wpt(wall, ix1, go, iz0)), m(wpt(wall, ix1, go, iz1)), m(wpt(wall, ix0, go, iz1))]
        if wall in ('W', 'N'):
            pts = list(reversed(pts))
        b.quad_auto('glass', pts, 1.0)
    # dark room interior behind (stand-in when the interior is not modelled)
    pts = [m(wpt(wall, a0, -T - 1.5, sill)), m(wpt(wall, a1, -T - 1.5, sill)), m(wpt(wall, a1, -T - 1.5, head)), m(wpt(wall, a0, -T - 1.5, head))]
    if wall in ('W', 'N'):
        pts = list(reversed(pts))
    if not SHOW_INTERIOR:
        b.quad_auto('interior', pts, 1.0)
    # curtain on some windows (white muslin seen in T.R.'s photo of W1)
    if rng.random() < 0.5:
        wbox(b, 'curtain', wall, a0 + 0.1, a0 + 0.1 + (a1 - a0) * rng.uniform(0.25, 0.45), -T - 0.1, -T - 0.05, sill + 0.4, head - 0.15)


def door(b, wall, c, rng, w=DOOR['w'], sill=DOOR['sill'], head=DOOR['head']):
    a0, a1 = c - w / 2, c + w / 2
    cas = 3.5 / 12; ct = 0.9 / 12
    wbox(b, 'trim', wall, a0 - cas, a0, 0.0, ct, sill, head, 0.8, 2)
    wbox(b, 'trim', wall, a1, a1 + cas, 0.0, ct, sill, head, 0.8, 2)
    wbox(b, 'trim', wall, a0 - cas, a1 + cas, 0.0, ct, head, head + cas, 0.8, 0)
    wbox(b, 'board', wall, a0, a1, -T, 0.05, sill - 0.08, sill, 0.8, 0)     # threshold
    for (x0, x1) in ((a0, a0 + 0.06), (a1 - 0.06, a1)):
        wbox(b, 'board', wall, x0, x1, -T, 0.0, sill, head, 0.8, 2)
    wbox(b, 'board', wall, a0, a1, -T, 0.0, head - 0.06, head, 0.8, 0)
    # leaf: vertical matched boards, slight gaps
    x = a0 + 0.06
    leaf_top = head - 0.06
    while x < a1 - 0.07:
        bw = min(rng.uniform(0.42, 0.55), a1 - 0.06 - x)
        wbox(b, 'door', wall, x + 0.008, x + bw - 0.008, -0.42, -0.34, sill, leaf_top, 1.2, 2)
        x += bw
    if not SHOW_INTERIOR:
        wbox(b, 'interior', wall, a0, a1, -0.44, -0.43, sill, leaf_top)
    # strap hinges (iron)
    for zz in (sill + 0.8, leaf_top - 0.8):
        wbox(b, 'iron', wall, a0 + 0.06, a0 + 1.4, -0.34, -0.32, zz - 0.06, zz + 0.06)
    # latch
    wbox(b, 'iron', wall, a1 - 0.45, a1 - 0.2, -0.34, -0.31, sill + 3.2, sill + 3.3)


# ------------------------------------------------------------------ roof + shingles
def shingle_field(b, mk, origin, udir, vdir, ndir, u0, u1, v0, v1, rng, exposure=5 / 12, length=16 / 12,
                  clip=None, butt=0.03, tile=1.27):
    """Lay shingle courses on a plane: origin + u*udir + v*vdir (ft); courses start at v0 going up.
    clip(u, v) -> bool keeps shingle if True. Butt raised along normal."""
    O = Vector(origin); U = Vector(udir).normalized(); Vd = Vector(vdir).normalized(); N = Vector(ndir).normalized()
    v = v0
    row = 0
    while v < v1:
        u = u0 - rng.uniform(0, 0.4)
        top = min(v + length, v1 + 0.05)
        while u < u1:
            wdt = rng.uniform(3, 9) / 12
            ua, ub = max(u, u0), min(u + wdt - 0.012, u1)
            if ub - ua > 0.04 and (clip is None or (clip(ua, v) and clip(ub, v))):
                vb = v + rng.uniform(-0.02, 0.02)
                lift = butt * rng.uniform(0.8, 1.3)
                def P(uu, vv, l):
                    return m(O + U * uu + Vd * vv + N * l)
                a, bq, c, d = P(ua, vb, lift + 0.025), P(ub, vb, lift + 0.025), P(ub, top, 0.012), P(ua, top, 0.012)
                off = rng.random() * 3
                tl = 0.6
                uv = [(vb * FT / tl + off, ua * FT / tl), (vb * FT / tl + off, ub * FT / tl),
                      (top * FT / tl + off, ub * FT / tl), (top * FT / tl + off, ua * FT / tl)]
                g = rng.uniform(0.62, 1.1); prev = b.col
                b.col = (g, g * rng.uniform(0.97, 1.01), g * rng.uniform(0.92, 1.0))
                b.face(mk, [a, bq, c, d], uv)
                # butt edge
                a0, b0 = P(ua, vb, 0.0), P(ub, vb, 0.0)
                b.col = (g * 0.6, g * 0.58, g * 0.55)
                b.face(mk, [a0, b0, bq, a], [(0, 0), (0.05, 0), (0.05, 0.01), (0, 0.01)])
                b.col = prev
            u += wdt
        v += exposure
        row += 1


def roof(b, rng):
    # deck slabs (boards), shingles, fascia, barge boards, rafter tails, ridge boards
    y0, y1 = -0.67, 60.67
    for side in (-1, 1):
        xe = -1.0 if side < 0 else 31.0      # eave x
        ze = roof_z(xe)
        zr = roof_z(RIDGE_X)
        # deck underside (soffit + deck) as thin slab
        e = Vector((xe, 0, ze)); r = Vector((RIDGE_X, 0, zr))
        slope = (r - e)
        Ls = slope.length
        vdir = slope.normalized()
        ndir = Vector((side * math.sin(math.radians(30)) * -1, 0, math.cos(math.radians(30)))) if False else None
        # outward normal of this slope
        ndir = Vector((-vdir.z * (1 if side < 0 else -1) * -1, 0, 0))
        nrm = Vector((xe - RIDGE_X, 0, 0)).normalized() * math.sin(math.radians(30)) + Vector((0, 0, math.cos(math.radians(30))))
        # board deck top surface (under shingles), 1 in thick
        for yy0, yy1 in ((y0, y1),):
            pts = [m(e + Vector((0, yy0, 0))), m(e + Vector((0, yy1, 0))), m(r + Vector((0, yy1, 0))), m(r + Vector((0, yy0, 0)))]
            if side > 0:
                pts = list(reversed(pts))
            b.quad_auto('board', pts, 1.5, grain=(0, 1, 0))
            dn = -nrm * (1 / 12)
            pts2 = [m(e + Vector((0, yy0, 0)) + dn), m(r + Vector((0, yy0, 0)) + dn), m(r + Vector((0, yy1, 0)) + dn), m(e + Vector((0, yy1, 0)) + dn)]
            if side > 0:
                pts2 = list(reversed(pts2))
            b.quad_auto('soffit', pts2, 1.5, grain=(0, 1, 0))
        shingle_field(b, 'shingle', e, (0, 1, 0), vdir, nrm, y0, y1, -0.05, Ls + 0.05, rng)
        # fascia board at eave (1x6), hanging below deck edge
        fx = xe
        b.box('board', m((fx - 0.04 if side < 0 else fx - 0.04, y0, ze - 0.55)), m((fx + 0.04, y1, ze)), 1.5, 1)
        # rafter tails from wall to fascia (open soffit), every 2.5 ft
        yy = 0.5
        while yy < 60:
            xw = 0.0 if side < 0 else 30.0
            zt = roof_z(xw) - 1 / 12
            p0 = Vector((xw, yy, zt - 0.25)); p1 = Vector((fx, yy, ze - 1 / 12 - 0.25))
            d = (p1 - p0)
            c = (p0 + p1) / 2
            b.obox('soffit', m(c), (d.normalized(), (0, 1, 0), d.normalized().cross(Vector((0, 1, 0))) * -1),
                   (d.length / 2 * FT, 1 / 12 * FT, 0.25 * FT), 1.0, 0)
            yy += 2.5
    # barge boards along both rakes (1x6), north and south
    for yb in (y0 - 0.06, y1 + 0.06):
        for side in (-1, 1):
            xe = -1.0 if side < 0 else 31.0
            e = Vector((xe, yb, roof_z(xe) - 0.4)); r = Vector((RIDGE_X, yb, roof_z(RIDGE_X) - 0.4))
            d = r - e; c = (e + r) / 2
            b.obox('board', m(c), (d.normalized(), (0, 1, 0), d.normalized().cross(Vector((0, 1, 0))) * -1),
                   (d.length / 2 * FT, 0.06 * FT, 0.27 * FT), 1.5, 0)
    # ridge saddle boards
    zr = roof_z(RIDGE_X)
    for side in (-1, 1):
        d = Vector((side * math.cos(math.radians(30)), 0, -math.sin(math.radians(30))))
        c = Vector((RIDGE_X, 30, zr + 0.06)) + d * 0.25
        b.obox('board', m(c), ((0, 1, 0), d, d.cross(Vector((0, 1, 0)))), (61.4 / 2 * FT, 0.27 * FT, 0.04 * FT), 1.5, 0)


def gables(b, rng):
    zp = PLATE
    zr = roof_z(RIDGE_X) - 0.45
    for wall, yface, nsign in (('S', 0.0, -1), ('N', 60.0, 1)):
        # sheathing triangle (boards) flush with log face
        def P(x, z, o=0.0):
            return m((x, yface + nsign * o, z))
        tri = [P(-0.2, zp), P(30.2, zp), P(RIDGE_X, zr)]
        if nsign > 0:
            tri = list(reversed(tri))
        b.quad_auto('board', tri, 1.5)
        # shingles on gable: horizontal courses, clipped to the triangle
        def inside(x, z):
            half = (zr - z) / TAN
            return abs(x - RIDGE_X) <= half - 0.05
        origin = Vector((0, yface + nsign * 0.01, zp + 0.05))
        udir = (1, 0, 0)
        if nsign < 0:
            shingle_field(b, 'shingle', origin, udir, (0, 0, 1), (0, -1, 0), -0.2, 30.2, 0.0, zr - zp - 0.2, rng,
                          clip=lambda u, v: inside(u, v + zp + 0.6), butt=0.03)
        else:
            shingle_field(b, 'shingle', origin + Vector((30, 0, 0)), (-1, 0, 0), (0, 0, 1), (0, 1, 0), -0.2, 30.2, 0.0, zr - zp - 0.2, rng,
                          clip=lambda u, v: inside(30 - u, v + zp + 0.6), butt=0.03)
        if wall == 'S':
            # gable window 6 lights (2 wide x 3 high), single sash, centred X 15, sill 12.0
            gw = 1.83; gs = 12.0; gh = 12.0 + 2.6
            a0, a1 = 15 - gw / 2, 15 + gw / 2
            # frame in south wall frame: wpt uses origin SW, u=+x, n=-y
            wbox(b, 'board', 'S', a0 - 0.25, a1 + 0.25, 0.0, 0.12, gs - 0.12, gh + 0.25, 0.8, 0)
            wbox(b, 'sash', 'S', a0, a1, 0.08, 0.16, gs, gh)
            ix0, ix1, iz0, iz1 = a0 + 0.14, a1 - 0.14, gs + 0.14, gh - 0.14
            for k in (1,):
                xx = (ix0 + ix1) / 2
                wbox(b, 'sash', 'S', xx - 0.04, xx + 0.04, 0.17, 0.2, iz0, iz1)
            for k in (1, 2):
                zz = iz0 + (iz1 - iz0) * k / 3
                wbox(b, 'sash', 'S', ix0, ix1, 0.17, 0.2, zz - 0.04, zz + 0.04)
            pts = [m((ix0, -0.17, iz0)), m((ix1, -0.17, iz0)), m((ix1, -0.17, iz1)), m((ix0, -0.17, iz1))]
            b.quad_auto('glass', pts, 1.0)


def chimney(b, rng):
    x0, x1, y0, y1 = 12.67, 14.0, 22.0, 24.0
    ztop = 20.5
    zb = roof_z(x0) - 0.6
    b.box('brick', m((x0, y0, zb)), m((x1, y1, ztop - 0.3)), 3.0, 2)
    b.box('brick', m((x0 - 0.12, y0 - 0.12, ztop - 0.3)), m((x1 + 0.12, y1 + 0.12, ztop - 0.12)), 3.0, 2)
    b.box('brick', m((x0 - 0.04, y0 - 0.04, ztop - 0.12)), m((x1 + 0.04, y1 + 0.04, ztop)), 3.0, 2)
    b.box('interior', m((x0 + 0.33, y0 + 0.33, ztop - 0.5)), m((x1 - 0.33, y1 - 0.33, ztop + 0.002)), 1.0)


def porches(b, rng):
    # ---- east veranda
    X0, X1, Y0, Y1 = 30.0, 39.25, 9.5, 31.5   # depth 9.25 ft from camera solve of T.R.'s veranda photo
    deck = 0.75   # photo shows the veranda floor barely above grade
    # sleepers/log edge
    hewn_log(b, 'log', (39.0, Y0 - 0.3, 0.32), (39.0, Y1 + 0.3, 0.32), (0, 0, 1), (1, 0, 0), 0.7, 0.62, rng)
    hewn_log(b, 'log', (34.5, Y0, 0.3), (34.5, Y1, 0.3), (0, 0, 1), (1, 0, 0), 0.6, 0.5, rng)
    # deck boards running N-S
    x = X0
    while x < X1 - 0.05:
        bw = rng.uniform(0.45, 0.6)
        b.box('deck', m((x + 0.01, Y0, deck - 0.12)), m((min(x + bw, X1) - 0.01, Y1, deck)), 1.5, 1)
        x += bw
    # posts
    for py in (9.75, 31.25):
        b.box('post', m((39.0 - 0.29, py - 0.29, deck)), m((39.0 + 0.29, py + 0.29, 7.75)), 0.5, 2, endmk='logend')
        b.box('stone', m((39.0 - 0.6, py - 0.5, -0.2)), m((39.0 + 0.6, py + 0.5, 0.25)), 1.8)
    # front beam (hewn), slightly sagging
    hewn_log(b, 'log', (39.0, Y0 - 1.0, 8.15), (39.0, Y1 + 1.0, 8.15), (0, 0, 1), (1, 0, 0), 0.67, 0.8, rng)
    # roof (shed) from under the main eave to beyond the beam
    zw, zf = 9.15, 8.6
    xf = 40.0
    e = Vector((xf, 0, zf)); r = Vector((30.0, 0, zw))
    vdir = (r - e).normalized()
    nrm = Vector((vdir.z, 0, -vdir.x)).normalized()
    if nrm.z < 0: nrm = -nrm
    yy0, yy1 = Y0 - 0.75, Y1 + 0.75
    b.quad_auto('board', [m(e + Vector((0, yy0, 0))), m(e + Vector((0, yy1, 0))), m(r + Vector((0, yy1, 0))), m(r + Vector((0, yy0, 0)))][::-1], 1.5, grain=(0, 1, 0))
    dn = -nrm * 0.12
    b.quad_auto('soffit', [m(e + Vector((0, yy0, 0)) + dn), m(e + Vector((0, yy1, 0)) + dn), m(r + Vector((0, yy1, 0)) + dn), m(r + Vector((0, yy0, 0)) + dn)], 1.5, grain=(0, 1, 0))
    b.box('board', m((xf - 0.05, yy0, zf - 0.45)), m((xf + 0.03, yy1, zf)), 1.5, 1)
    for yb in (yy0, yy1):
        b.box('board', m((30.0, yb - 0.04, zf - 0.4)), m((xf, yb + 0.04, zw)), 1.5, 0)
    shingle_field(b, 'shingle', e, (0, 1, 0), vdir, nrm, yy0, yy1, -0.05, (r - e).length - 0.3, rng)
    # ---- south piazza
    X0, X1, Y0 = 8.5, 28.5, -7.5
    hewn_log(b, 'log', (X0 - 0.3, -7.25, 0.55), (X1 + 0.3, -7.25, 0.55), (0, 0, 1), (0, -1, 0), 0.6, 0.65, rng)
    y = Y0
    while y < -0.05:
        bw = rng.uniform(0.45, 0.6)
        b.box('deck', m((X0, y + 0.01, deck - 0.12)), m((X1, min(y + bw, 0.0) - 0.01, deck)), 1.5, 0)
        y += bw
    for px in (8.75, 18.5, 28.25):
        b.box('post', m((px - 0.25, -7.25 - 0.25, deck)), m((px + 0.25, -7.25 + 0.25, 8.15)), 0.5, 2, endmk='logend')
    hewn_log(b, 'log', (X0 - 0.75, -7.25, 8.45), (X1 + 0.75, -7.25, 8.45), (0, 0, 1), (0, -1, 0), 0.55, 0.6, rng)
    zw, zf, yf = 11.0, 8.75, -8.25
    e = Vector((0, yf, zf)); r = Vector((0, 0.0, zw))
    vdir = (r - e).normalized()
    nrm = Vector((0, -vdir.z, vdir.y)).normalized()
    if nrm.z < 0: nrm = -nrm
    xx0, xx1 = X0 - 0.75, X1 + 0.75
    b.quad_auto('board', [m(e + Vector((xx0, 0, 0))), m(e + Vector((xx1, 0, 0))), m(r + Vector((xx1, 0, 0))), m(r + Vector((xx0, 0, 0)))], 1.5, grain=(1, 0, 0))
    dn = -nrm * 0.12
    b.quad_auto('soffit', [m(e + Vector((xx0, 0, 0)) + dn), m(r + Vector((xx0, 0, 0)) + dn), m(r + Vector((xx1, 0, 0)) + dn), m(e + Vector((xx1, 0, 0)) + dn)], 1.5, grain=(1, 0, 0))
    b.box('board', m((xx0, yf - 0.03, zf - 0.45)), m((xx1, yf + 0.05, zf)), 1.5, 0)
    shingle_field(b, 'shingle', e + Vector((0, 0, 0)), (1, 0, 0), vdir, nrm, xx0, xx1, -0.05, (r - e).length - 0.2, rng)
    # ---- west back stoop + cellar bulkhead
    hewn_log(b, 'log', (-3.7, 23.0, 0.45), (-3.7, 31.0, 0.45), (0, 0, 1), (-1, 0, 0), 0.6, 0.55, rng)
    yy = 23.0
    while yy < 31.0:
        bw = rng.uniform(0.45, 0.6)
        b.box('deck', m((-4.0, yy + 0.01, 0.85)), m((0.0, min(yy + bw, 31.0) - 0.01, 0.97)), 1.5, 0)
        yy += bw
    # bulkhead: sloping board door
    p = [Vector((-4.0, 8.75, 0.4)), Vector((-4.0, 14.75, 0.4)), Vector((0.0, 14.75, 1.1)), Vector((0.0, 8.75, 1.1))]
    b.quad_auto('door', [m(q) for q in p], 1.2, grain=(1, 0, 0))
    b.box('board', m((-4.05, 8.75, 0.0)), m((0.0, 8.85, 0.45)), 1.0)
    b.box('board', m((-4.05, 14.65, 0.0)), m((0.0, 14.75, 0.45)), 1.0)


def foundation(b, rng):
    stones = [(0.7, 19.9), (1.1, 33.9), (1.6, 57.6), (13.4, 57.2), (29.0, 57.4), (29.1, 46.5), (28.5, 26.5),
              (28.5, 11.6), (28.2, 1.0), (12.9, 1.5), (1.0, 1.0)]
    for (x, y) in stones:
        # snap to wall line
        if x < 3: x = 0.42
        elif x > 27: x = 29.58
        if y < 3: y = 0.42
        elif y > 56: y = 59.58
        rock(b, (x, y, 0.05), (rng.uniform(1.6, 2.4), rng.uniform(1.2, 1.7), rng.uniform(0.7, 1.0)), rng)
    # small shims / packing stones under the sill elsewhere
    for wall, (org, u, n, L) in WALLS.items():
        a = 3.0
        while a < L - 3:
            p = wpt(wall, a, -T / 2, 0.1)
            rock(b, tuple(p), (rng.uniform(0.6, 1.0), rng.uniform(0.5, 0.8), 0.6), rng)
            a += rng.uniform(5, 8)


def rock(b, c, size, rng, mk='stone'):
    """Irregular boulder: jittered UV sphere, flattened."""
    cx, cy, cz = c
    sx, sy, sz = size
    nu, nv = 9, 5
    rings = []
    for j in range(nv + 1):
        th = math.pi * j / nv
        ring = []
        for i in range(nu):
            ph = 2 * math.pi * i / nu
            r = rng.uniform(0.8, 1.1)
            x = math.sin(th) * math.cos(ph) * sx / 2 * r
            y = math.sin(th) * math.sin(ph) * sy / 2 * r
            z = math.cos(th) * sz / 2 * (0.7 if j < nv / 2 else 1.0)
            ring.append(m((cx + x, cy + y, cz + z)))
        rings.append(ring)
    for j in range(nv):
        for i in range(nu):
            i2 = (i + 1) % nu
            pts = [rings[j][i], rings[j][i2], rings[j + 1][i2], rings[j + 1][i]]
            b.quad_auto(mk, pts, 1.2)


def build_house(b, rng):
    b.group = 'house'
    walls(b, rng)
    b.group = 'roof'
    roof(b, rng)
    gables(b, rng)
    b.group = 'house'
    chimney(b, rng)
    porches(b, rng)
    foundation(b, rng)
