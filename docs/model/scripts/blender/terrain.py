"""Terrain (2021 USGS 3DEP lidar), Little Missouri water surface and trees for the context renders.
Not exported for AR: on site the real ground and trees are there."""
import math, json, random
import numpy as np
import bpy
from mathutils import Vector, Matrix
import lib
from lib import FT

T = lib.M + '/terrain/'

# building pads: (x0, x1, y0, y1) house ft; terrain is flattened to the pad level inside, blended outside
PADS = {
    'house': ((-6, 42, -10, 64), None),
    'barn': ((-116, -58, 178, 202), 'barn'),
    'shed': ((-63, -27, 52, 86), 'shed'),
    'well': ((-40, -30, -12, -3), 'well'),
    'smithy': ((118, 150, -246, -204), 'blacksmith'),
    'dugout': ((150, 182, -268, -240), 'dugout'),
    'corral': ((-200, -125, -392, -316), 'corral'),
}


def load():
    d = np.load(T + 'terrain.npz')
    meta = json.load(open(T + 'terrain_meta.json'))
    return d, meta


def sample(xs, ys, Z, x, y):
    fx = (x - xs[0]) / (xs[1] - xs[0]); fy = (y - ys[0]) / (ys[1] - ys[0])
    i = int(np.clip(fx, 0, len(xs) - 2)); j = int(np.clip(fy, 0, len(ys) - 2))
    tx = fx - i; ty = fy - j
    return float(Z[j, i] * (1 - tx) * (1 - ty) + Z[j, i + 1] * tx * (1 - ty) + Z[j + 1, i] * (1 - tx) * ty + Z[j + 1, i + 1] * tx * ty)


def pad_levels(d):
    xs, ys, Z = d['near_xs'], d['near_ys'], d['near_Z']
    lv = {}
    for k, ((x0, x1, y0, y1), grp) in PADS.items():
        if k == 'house':
            lv[k] = 0.0; continue
        X, Y = np.meshgrid(xs, ys)
        m = (X >= x0) & (X <= x1) & (Y >= y0) & (Y <= y1)
        lv[k] = float(np.median(Z[m]))
    return lv


def flatten(xs, ys, Z, lv):
    Z = Z.copy()
    X, Y = np.meshgrid(xs, ys)
    for k, ((x0, x1, y0, y1), grp) in PADS.items():
        dx = np.maximum(0, np.maximum(x0 - X, X - x1)); dy = np.maximum(0, np.maximum(y0 - Y, Y - y1))
        dist = np.hypot(dx, dy)
        w = np.clip(1 - dist / 25.0, 0, 1) ** 2
        target = lv[k] - 0.15
        Z = Z * (1 - w) + np.minimum(Z, target) * w if k != 'dugout' else Z * (1 - w) + target * w
    return Z


def grid_mesh(name, xs, ys, Z, mat, hole=None, step=1):
    xs = xs[::step]; ys = ys[::step]; Z = Z[::step, ::step]
    nx, ny = len(xs), len(ys)
    V = [(x * FT, y * FT, Z[j, i] * FT) for j, y in enumerate(ys) for i, x in enumerate(xs)]
    F = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            if hole:
                cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
                if hole[0] < cx < hole[1] and hole[2] < cy < hole[3]:
                    continue
            a = j * nx + i
            F.append((a, a + 1, a + nx + 1, a + nx))
    me = bpy.data.meshes.new(name); me.from_pydata(V, [], F)
    uv = me.uv_layers.new(name='UVMap')
    for poly in me.polygons:
        for li in poly.loop_indices:
            v = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = (v.x / 2.0, v.y / 2.0)
    col = me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
    for c in col.data: c.color = (1, 1, 1, 1)
    me.materials.append(mat)
    for p in me.polygons: p.use_smooth = True
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob


def terrain_material(mats):
    """Prairie grass on gentle ground, bare clay / sandstone on steep faces (slope from the geometry normal)."""
    mt = mats['grass'].copy(); mt.name = 'terrain'
    nt = mt.node_tree; bsdf = nt.nodes['Principled BSDF']
    src = bsdf.inputs['Base Color'].links[0].from_socket
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Normal'], sep.inputs[0])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.80; ramp.color_ramp.elements[0].color = (0, 0, 0, 1)
    ramp.color_ramp.elements[1].position = 0.92; ramp.color_ramp.elements[1].color = (1, 1, 1, 1)
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    clay = nt.nodes.new('ShaderNodeTexNoise'); clay.inputs['Scale'].default_value = 0.8
    tc = nt.nodes.new('ShaderNodeTexCoord'); nt.links.new(tc.outputs['Object'], clay.inputs['Vector'])
    cr = nt.nodes.new('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = (0.22, 0.2, 0.17, 1); cr.color_ramp.elements[1].color = (0.42, 0.38, 0.31, 1)
    sep2 = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sep2.inputs[0])
    band = nt.nodes.new('ShaderNodeMath'); band.operation = 'SINE'
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = 3.0
    nt.links.new(sep2.outputs['Z'], mul.inputs[0]); nt.links.new(mul.outputs[0], band.inputs[0])
    add = nt.nodes.new('ShaderNodeMath'); add.operation = 'MULTIPLY_ADD'; add.inputs[1].default_value = 0.25; add.inputs[2].default_value = 0.5
    nt.links.new(band.outputs[0], add.inputs[0])
    mix0 = nt.nodes.new('ShaderNodeMath'); mix0.operation = 'ADD'
    nt.links.new(clay.outputs['Fac'], mix0.inputs[0]); nt.links.new(add.outputs[0], mix0.inputs[1])
    hm = nt.nodes.new('ShaderNodeMath'); hm.operation = 'MULTIPLY'; hm.inputs[1].default_value = 0.5
    nt.links.new(mix0.outputs[0], hm.inputs[0]); nt.links.new(hm.outputs[0], cr.inputs['Fac'])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    nt.links.new(ramp.outputs['Color'], mix.inputs['Factor'])
    nt.links.new(src, mix.inputs[7]); nt.links.new(cr.outputs['Color'], mix.inputs[6])
    nt.links.new(mix.outputs[2], bsdf.inputs['Base Color'])
    return mt


def water_material():
    mt = bpy.data.materials.new('river'); mt.use_nodes = True
    b = mt.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.20, 0.18, 0.13, 1)    # silty Little Missouri
    b.inputs['Roughness'].default_value = 0.08
    nz = mt.node_tree.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0
    bm = mt.node_tree.nodes.new('ShaderNodeBump'); bm.inputs['Strength'].default_value = 0.08
    mt.node_tree.links.new(nz.outputs['Fac'], bm.inputs['Height']); mt.node_tree.links.new(bm.outputs['Normal'], b.inputs['Normal'])
    return mt


def leaf_texture():
    """Plains cottonwood (Populus deltoides) leaves: deltoid, coarsely toothed, long flattened petiole."""
    from PIL import Image, ImageDraw, ImageFilter
    path = T + 'leaf_cluster.png'
    import os
    if os.path.exists(path):
        return path
    N = 512; im = Image.new('RGBA', (N, N), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    rng = random.Random(3)
    for k in range(170):
        rr = (rng.random() ** 0.6) * (N / 2 - 30); th = rng.uniform(0, 6.28)
        cx, cy = N / 2 + rr * math.cos(th), N / 2 + rr * math.sin(th); s = rng.uniform(11, 17); a = rng.uniform(0, 6.28)
        pts = []
        for t in range(0, 41):
            u = t / 40.0
            # deltoid outline: broad flat base, pointed tip, small teeth
            ang = math.pi * (u - 0.5)
            r = s * (0.55 + 0.45 * math.cos(ang * 1.0)) * (1 + 0.04 * math.sin(t * 2.2))
            x = math.sin(ang * 1.9) * r * 0.75; y = -math.cos(ang) * r * 1.05 + s * 0.2
            pts.append((cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)))
        g = rng.uniform(0.75, 1.1)
        col = (int(68 * g), int(102 * g), int(40 * g), 255)
        d.polygon(pts, fill=col)
        d.line([(cx, cy), (cx - s * 0.9 * math.sin(a), cy + s * 0.9 * math.cos(a))], fill=(int(90 * g), int(110 * g), 50, 255), width=1)
    im = im.filter(ImageFilter.SMOOTH)
    im.save(path)
    return path


def leaf_material():
    mt = bpy.data.materials.new('cottonwood_leaves'); mt.use_nodes = True
    nt = mt.node_tree; b = nt.nodes['Principled BSDF']
    tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(leaf_texture())
    va = nt.nodes.new('ShaderNodeVertexColor'); va.layer_name = 'Col'
    mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    nt.links.new(tx.outputs['Color'], mul.inputs[6]); nt.links.new(va.outputs['Color'], mul.inputs[7])
    nt.links.new(mul.outputs[2], b.inputs['Base Color'])
    nt.links.new(tx.outputs['Alpha'], b.inputs['Alpha'])
    b.inputs['Roughness'].default_value = 0.55
    b.inputs['Subsurface Weight'].default_value = 0.0
    try:
        b.inputs['Transmission Weight'].default_value = 0.0
    except KeyError:
        pass
    return mt


def cottonwood(b, base, height, rng, spread=0.55, lean=None):
    """Plains cottonwood: stout furrowed trunk forking low into a few heavy ascending limbs, open irregular crown."""
    base = Vector(base)
    lean = lean or Vector((rng.uniform(-.12, .12), rng.uniform(-.12, .12), 1)).normalized()
    trunk_h = height * rng.uniform(0.22, 0.32)
    r0 = max(0.35, height / 110.0) * rng.uniform(0.85, 1.15)
    top = base + lean * trunk_h
    b.tube('bark', [b_m(base - Vector((0, 0, 1))), b_m(base + lean * trunk_h * 0.5), b_m(top)],
           [r0 * 1.25 * FT, r0 * FT, r0 * 0.8 * FT], sides=10, tile=1.5, jitter=0.08)
    leaves = []
    def branch(p, d, L, r, depth):
        n = 4
        pts = [p]; q = Vector(p); dd = Vector(d)
        for k in range(n):
            dd = (dd + Vector((rng.uniform(-.25, .25), rng.uniform(-.25, .25), rng.uniform(-.05, .2)))).normalized()
            q = q + dd * L / n; pts.append(q.copy())
        b.tube('bark', [b_m(x) for x in pts], [r * FT * (1 - 0.6 * k / n) for k in range(n + 1)], sides=7 if depth < 2 else 5, tile=1.5)
        if depth >= 3 or r < 0.04:
            leaves.append((q, L))
            return
        if depth >= 1:
            leaves.append((pts[n // 2], L * 0.6))
        kids = rng.randint(2, 3) if depth < 2 else rng.randint(2, 4)
        for c in range(kids):
            t = rng.uniform(0.5, 1.0)
            idx = max(1, min(n, int(t * n)))
            nd = (dd + Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(0.1, 0.9))) * spread).normalized()
            branch(pts[idx], nd, L * rng.uniform(0.5, 0.72), r * 0.55, depth + 1)
        leaves.append((q, L * 0.7))
    limbs = rng.randint(2, 4)
    for c in range(limbs):
        a = 2 * math.pi * c / limbs + rng.uniform(-.4, .4)
        d = (lean + Vector((math.cos(a), math.sin(a), 0)) * rng.uniform(0.35, 0.7)).normalized()
        branch(top, d, (height - trunk_h) * rng.uniform(0.55, 0.75), r0 * 0.7, 0)
    # foliage cards around branch tips
    prev = b.col
    for (q, L) in leaves:
        nc = int(np.clip(L * 4.0, 14, 90))
        for k in range(nc):
            c = q + Vector((rng.gauss(0, L * .3), rng.gauss(0, L * .3), rng.gauss(0, L * .22)))
            s = rng.uniform(2.4, 3.6)
            ax = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))).normalized()
            ay = ax.orthogonal().normalized(); ay.rotate(Matrix.Rotation(rng.uniform(0, 6.28), 3, ax))
            az = ax.cross(ay)
            g = rng.uniform(0.75, 1.15); b.col = (g, g * rng.uniform(.95, 1.05), g * 0.9)
            pts = [b_m(c + (ay * -1 + az * -1) * s), b_m(c + (ay - az) * s), b_m(c + (ay + az) * s), b_m(c + (az - ay) * s)]
            b.face('leaf', pts, [(0, 0), (1, 0), (1, 1), (0, 1)])
    b.col = prev


def juniper(b, base, height, rng):
    """Rocky Mountain juniper on the slopes: short trunk, dense dark irregular cone."""
    base = Vector(base)
    b.tube('bark', [b_m(base - Vector((0, 0, .5))), b_m(base + Vector((0, 0, height * .3)))], [height / 40 * FT, height / 55 * FT], sides=6)
    prev = b.col; b.col = (0.55, 0.62, 0.55)
    for k in range(int(10 + height)):
        z = rng.uniform(0.15, 1.0) * height; rr = (1 - z / height) * height * 0.32 + 0.4
        c = base + Vector((rng.gauss(0, rr * .5), rng.gauss(0, rr * .5), z))
        s = rng.uniform(1.0, 1.8) * (0.6 + rr / height)
        ax = Vector((rng.uniform(-1, 1), rng.uniform(-1, 1), rng.uniform(-1, 1))).normalized(); ay = ax.orthogonal().normalized(); az = ax.cross(ay)
        b.face('leaf', [b_m(c - ay * s - az * s), b_m(c + ay * s - az * s), b_m(c + ay * s + az * s), b_m(c - ay * s + az * s)], [(0, 0), (1, 0), (1, 1), (0, 1)])
    b.col = prev


def b_m(v):
    return Vector(v) * FT


# Cottonwood grove of 1886, read from T.R.'s photograph of the house from the south-east (THRB03297-00402):
# a stand of tall, slender cottonwoods between the house and the photographer, thickest S and SE of the house.
GROVE_1886 = [(44, -16, 62), (52, -34, 70), (60, -8, 58), (66, -50, 66), (38, -40, 56), (74, -24, 64),
              (30, -58, 60), (82, -64, 54), (90, -40, 50), (18, -30, 52), (56, 6, 48), (48, 24, 46),
              (70, 40, 55), (96, -12, 50), (10, -64, 48), (-10, -40, 44), (-20, 70, 52), (-36, 100, 50),
              (40, 76, 58), (14, 84, 60), (60, 70, 50)]


def build_context(b, rng, d, meta, mats):
    mats['leaf'] = leaf_material()
    b.group = 'trees'
    # modern canopy (2021 lidar) beyond 120 ft of the house: cottonwoods on the bottomland, juniper on the slopes
    xs, ys, Z = d['near_xs'], d['near_ys'], d['near_Z']
    n = 0
    for t in meta['trees']:
        x, y, h, z = t['x'], t['y'], t['h'], t['z']
        dist = math.hypot(x - 15, y - 30)
        if dist < 120 or dist > 1100:
            continue
        if z > 25:          # up on the butte slopes
            if rng.random() < 0.5:
                juniper(b, (x, y, z), min(h, 25), rng); n += 1
        elif h > 25 and rng.random() < 0.55:
            cottonwood(b, (x, y, z), min(h, 85), rng); n += 1
    for (x, y, h) in GROVE_1886:
        z = sample(xs, ys, Z, x, y)
        cottonwood(b, (x, y, min(z, 0.0)), h, rng, spread=0.45); n += 1
    return n
