"""Veranda props seen in T.R.'s 1886 photograph: elk and deer antlers, Windsor rockers, lumber pile."""
import math
from mathutils import Vector, Matrix
from lib import FT


def m(v):
    return Vector(v) * FT


def _cr(pts, n):
    """Catmull-Rom through pts, n samples."""
    P = [pts[0]] + pts + [pts[-1]]
    out = []
    segs = len(pts) - 1
    for k in range(n + 1):
        u = k / n * segs; i = min(int(u), segs - 1); t = u - i
        p0, p1, p2, p3 = P[i], P[i + 1], P[i + 2], P[i + 3]
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    return out


# beam centre-lines in (side, fwd, up) as fractions of beam length; tines (t on beam, length frac, fwd, up, in)
RACKS = {
    'elk': dict(L=4.6, r0=0.028, beam=[(0.07, 0.03, 0.04), (0.2, -0.04, 0.24), (0.36, -0.18, 0.45), (0.48, -0.33, 0.66),
                                      (0.54, -0.42, 0.85), (0.5, -0.4, 1.0)],
                tines=[(0.04, 0.38, 1.0, 0.3, 0.05), (0.12, 0.33, 1.0, 0.4, 0.1), (0.36, 0.28, 0.9, 0.55, 0.15),
                       (0.56, 0.44, 0.8, 0.7, 0.1), (0.74, 0.3, 0.6, 0.9, 0.05), (0.9, 0.2, 0.5, 1.0, -0.1)]),
    'deer': dict(L=1.9, r0=0.026, beam=[(0.06, 0.02, 0.04), (0.25, -0.05, 0.3), (0.45, 0.08, 0.45), (0.52, 0.32, 0.52), (0.44, 0.52, 0.6)],
                 tines=[(0.08, 0.12, 0.6, 1.0, 0.0), (0.45, 0.45, -0.2, 1.0, 0.1), (0.75, 0.38, 0.1, 1.0, 0.1)]),
}


def antler_rack(b, base, facing, up=(0, 0, 1), scale=1.0, rng=None, kind='elk', tilt=0.0, skull=True):
    """base: skull/burr point (ft). facing: direction the nose points. tilt: rotation about the side axis (rad,
    negative tips the rack backwards so it lies or leans). Beams sweep back and out, tines point forward and up."""
    base = Vector(base); f = Vector(facing).normalized(); upv = Vector(up).normalized()
    upv = (upv - f * f.dot(upv)).normalized()
    side = f.cross(upv).normalized()
    if tilt:
        R = Matrix.Rotation(tilt, 3, side)
        f = R @ f; upv = R @ upv
    spec = RACKS[kind]
    L = spec['L'] * scale * rng.uniform(0.9, 1.08)
    if skull:   # weathered skull plate / cap with nose
        b.tube('bone2', [m(base - upv * 0.1 * scale), m(base + f * 0.35 * scale - upv * 0.25 * scale),
                         m(base + f * 0.9 * scale - upv * 0.45 * scale)], [0.2 * FT * scale, 0.17 * FT * scale, 0.09 * FT * scale], sides=8)
    for s in (-1, 1):
        def W(q, jit=0.0):
            return base + side * (q[0] * s) * L + f * q[1] * L + upv * q[2] * L + Vector((rng.uniform(-jit, jit), rng.uniform(-jit, jit), rng.uniform(-jit, jit)))
        ctrl = [W(q, 0.04 * scale) for q in spec['beam']]
        pts = _cr(ctrl, 18)
        r0 = spec['r0'] * L
        radii = [r0 * FT * (1.15 if i == 0 else 1.0) * (1 - 0.6 * i / 18) for i in range(19)]
        b.tube('bone', [m(p) for p in pts], radii, sides=8)
        # burr ring
        b.tube('bone2', [m(pts[0] - (pts[1] - pts[0]).normalized() * 0.03), m(pts[0] + (pts[1] - pts[0]).normalized() * 0.05)],
               [r0 * 1.45 * FT, r0 * 1.35 * FT], sides=8)
        for (t, lf, fw, uw, inw) in spec['tines']:
            idx = min(17, max(1, int(round(t * 18))))
            p = pts[idx]
            tl = lf * L * rng.uniform(0.85, 1.12)
            d = (f * fw + upv * uw - side * s * inw + Vector((rng.uniform(-.1, .1), rng.uniform(-.1, .1), 0))).normalized()
            q1 = p + d * tl * 0.45
            q2 = p + (d + upv * 0.35).normalized() * tl * 0.8
            q3 = p + (d + upv * 0.8).normalized() * tl
            rt = radii[idx] * 0.78
            b.tube('bone', [m(p), m(q1), m(q2), m(q3)], [rt, rt * 0.7, rt * 0.45, rt * 0.12], sides=7)


def saddle(b, pos, yaw, rng):
    """Western stock saddle set on its side on the veranda floor (as in the photograph): seat, horn, cantle,
    skirts, fenders and wooden stirrups."""
    c = Vector(pos); R = Matrix.Rotation(yaw, 3, 'Z')
    def P(x, y, z): return m(c + R @ Vector((x, y, z)))
    ax = (R @ Vector((1, 0, 0)), R @ Vector((0, 1, 0)), Vector((0, 0, 1)))
    # skirts (two leather slabs) lying flared
    b.obox('leather', P(0, 0, 0.75), ax, (1.15 * FT, 0.95 * FT, 0.05 * FT), 1.0)
    # tree / seat: arched tube
    seat = [P(-0.9, 0, 1.25), P(-0.5, 0, 1.05), P(0.1, 0, 1.0), P(0.6, 0, 1.15)]
    for off in (-0.3, -0.15, 0, 0.15, 0.3):
        b.tube('leather', [Vector(q) + Vector(R @ Vector((0, off * FT, -abs(off) * 0.3 * FT))) for q in seat], 0.11 * FT, sides=6)
    b.tube('leather', [P(0.65, 0, 1.0), P(0.8, 0, 1.55), P(0.85, 0, 1.75)], [0.17 * FT, 0.1 * FT, 0.12 * FT], sides=7)      # fork + horn
    b.tube('leather', [P(0.85, 0, 1.75), P(0.85, 0, 1.8)], [0.17 * FT, 0.17 * FT], sides=8)
    b.tube('leather', [P(-1.0, -0.4, 1.1), P(-1.05, 0, 1.6), P(-1.0, 0.4, 1.1)], 0.07 * FT, sides=6)                    # cantle
    for sgn in (-1, 1):   # fenders + stirrups
        b.obox('leather', P(0.0, sgn * 0.75, 0.55), (ax[0], (R @ Vector((0, sgn * 0.5, -0.85))).normalized(), (R @ Vector((0, sgn * 0.85, 0.5))).normalized()),
               (0.45 * FT, 0.6 * FT, 0.03 * FT), 1.0)
        b.tube('chair', [P(-0.25, sgn * 1.25, 0.2), P(0, sgn * 1.35, 0.05), P(0.25, sgn * 1.25, 0.2)], 0.06 * FT, sides=6)
    b.tube('leather', [P(0.3, 0.2, 0.9), P(0.6, 0.9, 0.4), P(0.3, 1.4, 0.05)], 0.035 * FT, sides=5)   # cinch strap


def rifle(b, butt, top, rng):
    """Long gun leaning against the wall: walnut stock + octagonal barrel + lever/trigger guard."""
    butt = Vector(butt); top = Vector(top); d = (top - butt).normalized(); L = (top - butt).length
    sidev = d.cross(Vector((0, 0, 1))).normalized(); nv = sidev.cross(d)
    b.tube('chair', [m(butt), m(butt + d * 0.55), m(butt + d * 1.15)], [0.13 * FT, 0.1 * FT, 0.06 * FT], sides=6)
    b.tube('iron', [m(butt + d * 1.1), m(butt + d * 1.65)], [0.07 * FT, 0.07 * FT], sides=6)       # receiver
    b.tube('chair', [m(butt + d * 1.65), m(butt + d * 2.6)], [0.05 * FT, 0.045 * FT], sides=6)     # forend
    b.tube('iron', [m(butt + d * 1.6), m(top)], [0.035 * FT, 0.032 * FT], sides=8)                 # barrel
    b.tube('iron', [m(butt + d * 1.15 + nv * 0.05), m(butt + d * 1.0 + nv * 0.22), m(butt + d * 1.45 + nv * 0.12)], 0.015 * FT, sides=4)


def windsor_rocker(b, pos, yaw, rng):
    """Bow-back Windsor rocker ~ as in the photograph. pos ft at floor."""
    c = Vector(pos)
    R = Matrix.Rotation(yaw, 3, 'Z')
    def P(x, y, z):
        return m(c + R @ Vector((x, y, z)))
    seat_h = 1.45
    # seat
    b.obox('chair', P(0, 0, seat_h), (R @ Vector((1, 0, 0)), R @ Vector((0, 1, 0)), (0, 0, 1)), (0.85 * FT, 0.8 * FT, 0.07 * FT), 1.0)
    # legs
    for (x, y) in ((-0.65, -0.55), (0.65, -0.55), (-0.6, 0.55), (0.6, 0.55)):
        b.tube('chair', [P(x * 1.1, y * 1.1, 0.25), P(x, y, seat_h - 0.05)], [0.055 * FT, 0.045 * FT], sides=6)
    # rockers
    for x in (-0.7, 0.7):
        pts = [P(x, -1.3 + 0.25 * i, 0.12 + 0.012 * (i - 5) ** 2) for i in range(11)]
        b.tube('chair', pts, 0.06 * FT, sides=6)
    # back spindles + crest rail
    for i in range(7):
        x = -0.5 + i / 6
        b.tube('chair', [P(x * 0.9, 0.62, seat_h), P(x, 0.85, seat_h + 2.4)], [0.035 * FT, 0.03 * FT], sides=5)
    b.obox('chair', P(0, 0.86, seat_h + 2.45), (R @ Vector((1, 0, 0)), R @ Vector((0, 1, 0)), (0, 0, 1)), (0.65 * FT, 0.12 * FT, 0.12 * FT), 1.0)
    # arms
    for x in (-0.8, 0.8):
        b.tube('chair', [P(x, 0.6, seat_h + 0.85), P(x, -0.6, seat_h + 0.8)], 0.05 * FT, sides=6)
        b.tube('chair', [P(x, -0.55, seat_h), P(x, -0.55, seat_h + 0.8)], 0.035 * FT, sides=5)


def lumber_pile(b, x0, y0, rng, n=9):
    z = 0.0
    for layer in range(n):
        h = 0.08
        for k in range(rng.randint(3, 5)):
            bw = rng.uniform(0.5, 0.8)
            b.box('lumber', m((x0 + k * 0.85 + rng.uniform(-0.05, 0.05), y0 + rng.uniform(-0.2, 0.2), z)),
                  m((x0 + k * 0.85 + bw, y0 + 12 + rng.uniform(-0.3, 0.3), z + h)), 1.4, 1)
        z += h + (0.33 if layer % 3 == 2 else 0.0)
        if layer % 3 == 2:
            for yy in (y0 + 1, y0 + 6, y0 + 11):
                b.box('lumber', m((x0, yy, z - 0.33)), m((x0 + 4, yy + 0.3, z)), 1.4, 0)


def build_props(b, rng):
    b.group = 'props'
    E = (1, 0, 0)
    # antlers, placed from T.R.'s veranda photograph (THRB03304-00217)
    antler_rack(b, (39.55, 13.0, 6.7), E, scale=1.0, rng=rng)                                    # hung on the veranda front beam
    antler_rack(b, (30.45, 2.6, 4.4), E, scale=1.0, rng=rng, kind='deer')                       # mule deer head on wall by corner
    antler_rack(b, (30.5, 7.6, 5.6), E, scale=0.9, rng=rng, kind='deer')
    antler_rack(b, (32.6, 4.5, 0.25), (0.6, -0.8, 0), scale=0.95, rng=rng, tilt=-1.25)          # lying in the foreground
    antler_rack(b, (31.4, 1.6, 0.3), (0.9, 0.2, 0), scale=0.9, rng=rng, tilt=-0.55)             # skull on ground, leaning back to wall
    antler_rack(b, (33.8, 8.2, 0.25), (0.2, -1, 0), scale=1.0, rng=rng, tilt=-1.35)             # lying at veranda edge
    antler_rack(b, (31.2, 13.0, 0.95), (1, 0.15, 0), scale=0.95, rng=rng, tilt=-0.5)            # leaning on wall between windows
    antler_rack(b, (32.5, 19.0, 0.9), (0.5, -1, 0), scale=0.95, rng=rng, tilt=-1.35)            # lying on veranda floor
    antler_rack(b, (31.0, 30.0, 0.95), (1, -0.2, 0), scale=0.9, rng=rng, tilt=-0.6)
    rifle(b, (30.75, 17.3, 0.8), (30.3, 16.6, 5.2), rng)
    rifle(b, (30.9, 18.1, 0.8), (30.35, 18.6, 5.0), rng)
    saddle(b, (32.6, 22.3, 0.8), math.radians(100), rng)
    windsor_rocker(b, (32.0, 25.5, 0.75), math.radians(-70), rng)
    windsor_rocker(b, (32.3, 28.6, 0.75), math.radians(-110), rng)
    lumber_pile(b, 40.5, 33.0, rng)
