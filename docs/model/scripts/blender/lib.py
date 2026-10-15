"""Geometry + material helpers for the Elkhorn reconstruction (Blender 5.x, bpy as module)."""
import bpy, bmesh, math, random
from mathutils import Vector, Matrix

FT = 0.3048
IN = FT / 12.0
M = __import__('os').environ.get('ELKHORN_MODEL_DIR', 'model')
PBR = M + '/materials/pbr/'
COR = M + '/materials/pbr_corrected/'


# ----------------------------------------------------------------- materials
def _img(path, colorspace='sRGB'):
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = colorspace
    return im


def pbr_material(name, albedo, normal=None, rough=None, rough_value=0.85, normal_strength=1.0,
                 tint=None, ao=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat['x_albedo'] = albedo; mat['x_normal'] = normal or ''; mat['x_rough'] = rough or ''
    mat['x_tint'] = list(tint) if tint else [1.0, 1.0, 1.0]; mat['x_rough_value'] = rough_value
    mat['x_normal_strength'] = normal_strength
    nt = mat.node_tree
    bsdf = nt.nodes.get('Principled BSDF')
    out = nt.nodes.get('Material Output')
    tex = nt.nodes.new('ShaderNodeTexImage'); tex.image = _img(albedo)
    col = tex.outputs['Color']
    if tint:
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'
        mix.inputs['Factor'].default_value = 1.0
        nt.links.new(col, mix.inputs[6]); mix.inputs[7].default_value = (*tint, 1)
        col = mix.outputs[2]
    va = nt.nodes.new('ShaderNodeVertexColor'); va.layer_name = 'Col'
    mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'
    mul.inputs['Factor'].default_value = 1.0
    nt.links.new(col, mul.inputs[6]); nt.links.new(va.outputs['Color'], mul.inputs[7])
    col = mul.outputs[2]
    nt.links.new(col, bsdf.inputs['Base Color'])
    if rough:
        rt = nt.nodes.new('ShaderNodeTexImage'); rt.image = _img(rough, 'Non-Color')
        nt.links.new(rt.outputs['Color'], bsdf.inputs['Roughness'])
    else:
        bsdf.inputs['Roughness'].default_value = rough_value
    if normal:
        nm = nt.nodes.new('ShaderNodeTexImage'); nm.image = _img(normal, 'Non-Color')
        nmap = nt.nodes.new('ShaderNodeNormalMap'); nmap.inputs['Strength'].default_value = normal_strength
        nt.links.new(nm.outputs['Color'], nmap.inputs['Color'])
        nt.links.new(nmap.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


def alpha_material(name, path):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    mat['x_albedo'] = path; mat['x_normal'] = ''; mat['x_rough'] = ''; mat['x_tint'] = [1.0, 1.0, 1.0]
    mat['x_rough_value'] = 0.9; mat['x_normal_strength'] = 1.0; mat['x_alpha'] = 1
    nt = mat.node_tree; b = nt.nodes['Principled BSDF']
    tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = _img(path)
    va = nt.nodes.new('ShaderNodeVertexColor'); va.layer_name = 'Col'
    mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    nt.links.new(tx.outputs['Color'], mul.inputs[6]); nt.links.new(va.outputs['Color'], mul.inputs[7])
    nt.links.new(mul.outputs[2], b.inputs['Base Color']); nt.links.new(tx.outputs['Alpha'], b.inputs['Alpha'])
    b.inputs['Roughness'].default_value = 0.9
    return mat


def flat_material(name, rgb, rough=0.8, metal=0.0, transmission=0.0, ior=1.45, alpha=1.0):
    mat = bpy.data.materials.new(name); mat.use_nodes = True
    b = mat.node_tree.nodes.get('Principled BSDF')
    b.inputs['Base Color'].default_value = (*rgb, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    if transmission:
        b.inputs['Transmission Weight'].default_value = transmission
        b.inputs['IOR'].default_value = ior
    return mat


def srgb(hexs):
    h = hexs.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def build_materials():
    S = {}
    def p(set_, f): return PBR + set_ + '/' + f
    TX = M + '/tex/'
    S['log'] = pbr_material('log_walls', TX + 'hewn_cottonwood_albedo.jpg', TX + 'hewn_cottonwood_normal.png',
                            TX + 'hewn_cottonwood_rough.jpg', normal_strength=1.7, tint=(0.68, 0.64, 0.6))
    S['logend'] = pbr_material('log_ends', COR + 'log_walls_rough_wood_albedo_weathered_1886_2k.jpg',
                               p('rough_wood', 'rough_wood_normal_gl_2k.jpg'), None, 0.9, 1.0, tint=(0.82, 0.8, 0.76))
    S['chink'] = pbr_material('chinking', COR + 'chinking_clay_plaster_albedo_weathered_1886_2k.jpg',
                              p('clay_plaster', 'clay_plaster_normal_gl_2k.jpg'), None, 0.95, 1.0, tint=(0.55, 0.52, 0.48))
    S['shingle'] = pbr_material('shingles', TX + 'pine_shingle_albedo.jpg', TX + 'pine_shingle_normal.png',
                                TX + 'pine_shingle_rough.jpg', normal_strength=1.0, tint=(0.72, 0.7, 0.67))
    S['trim'] = pbr_material('trim_boards', COR + 'eaves_fascia_wood_planks_grey_albedo_weathered_1886_2k.jpg',
                             p('wood_planks_grey', 'wood_planks_grey_normal_gl_2k.jpg'), None, 0.7, 1.0, tint=(0.5, 0.48, 0.45))
    S['board'] = pbr_material('boards', COR + 'eaves_fascia_wood_planks_grey_albedo_weathered_1886_2k.jpg',
                              p('wood_planks_grey', 'wood_planks_grey_normal_gl_2k.jpg'), p('wood_planks_grey', 'wood_planks_grey_roughness_2k.jpg'))
    S['soffit'] = pbr_material('soffit_boards', COR + 'eaves_fascia_wood_planks_grey_albedo_weathered_1886_2k.jpg',
                              p('wood_planks_grey', 'wood_planks_grey_normal_gl_2k.jpg'), p('wood_planks_grey', 'wood_planks_grey_roughness_2k.jpg'), tint=(0.15, 0.145, 0.135))
    S['rlog'] = pbr_material('round_logs', TX + 'hewn_cottonwood_albedo.jpg', TX + 'hewn_cottonwood_normal.png',
                             TX + 'hewn_cottonwood_rough.jpg', normal_strength=1.5, tint=(0.62, 0.58, 0.53))
    S['pole'] = pbr_material('poles', TX + 'hewn_cottonwood_albedo.jpg', TX + 'hewn_cottonwood_normal.png',
                             TX + 'hewn_cottonwood_rough.jpg', normal_strength=1.0, tint=(0.55, 0.52, 0.48))
    S['hay'] = pbr_material('hay', TX + 'hay_albedo.jpg', TX + 'hay_normal.png', None, 0.95, normal_strength=1.6, tint=(0.78, 0.74, 0.66))
    S['straw'] = alpha_material('straw', TX + 'hay_strands.png')
    S['door'] = pbr_material('door_boards', COR + 'doors_wood_planks_grey_albedo_weathered_1886_2k.jpg',
                             p('wood_planks_grey', 'wood_planks_grey_normal_gl_2k.jpg'), p('wood_planks_grey', 'wood_planks_grey_roughness_2k.jpg'))
    S['deck'] = pbr_material('porch_floor', COR + 'porch_floor_wood_planks_grey_albedo_weathered_1886_2k.jpg',
                             p('wood_planks_grey', 'wood_planks_grey_normal_gl_2k.jpg'), p('wood_planks_grey', 'wood_planks_grey_roughness_2k.jpg'))
    S['post'] = pbr_material('posts', TX + 'hewn_cottonwood_albedo.jpg', TX + 'hewn_cottonwood_normal.png',
                             TX + 'hewn_cottonwood_rough.jpg', normal_strength=1.2, tint=(0.6, 0.56, 0.5))
    S['sash'] = flat_material('window_sash', srgb('#3b3530'), 0.6)
    S['glass'] = flat_material('glass', (0.02, 0.025, 0.022), 0.05)
    S['glass'].node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = 0.8
    S['interior'] = flat_material('interior_dark', (0.012, 0.011, 0.01), 0.9)
    S['stone'] = pbr_material('foundation', COR + 'foundation_boulders_rock_boulder_dry_albedo_weathered_1886_2k.jpg',
                              p('rock_boulder_dry', 'rock_boulder_dry_normal_gl_2k.jpg'), p('rock_boulder_dry', 'rock_boulder_dry_roughness_2k.jpg'))
    S['brick'] = pbr_material('brick', COR + 'chimney_stovepipe_brick_wall_006_albedo_weathered_1886_2k.jpg',
                              p('brick_wall_006', 'brick_wall_006_normal_gl_2k.jpg'), p('brick_wall_006', 'brick_wall_006_roughness_2k.jpg'), tint=(0.8, 0.72, 0.68))
    S['sod'] = pbr_material('sod_roof', COR + 'stable_roof_withered_grass_albedo_weathered_1886_2k.jpg',
                            p('withered_grass', 'withered_grass_normal_gl_2k.jpg'), p('withered_grass', 'withered_grass_roughness_2k.jpg'), normal_strength=2.5, tint=(0.5, 0.46, 0.33))
    S['ground'] = pbr_material('ground', COR + 'ground_soil_gravelly_sand_albedo_weathered_1886_2k.jpg',
                               p('gravelly_sand', 'gravelly_sand_normal_gl_2k.jpg'), p('gravelly_sand', 'gravelly_sand_roughness_2k.jpg'), tint=(0.78, 0.74, 0.68))
    S['grass'] = pbr_material('grass', PBR + 'sparse_grass/sparse_grass_albedo_2k.jpg',
                              p('sparse_grass', 'sparse_grass_normal_gl_2k.jpg'), p('sparse_grass', 'sparse_grass_roughness_2k.jpg'), tint=(0.95, 0.88, 0.7))
    S['scoria'] = pbr_material('scoria', COR + 'scoria_path_terrain_red_01_albedo_weathered_1886_2k.jpg',
                               p('terrain_red_01', 'terrain_red_01_normal_gl_2k.jpg'), p('terrain_red_01', 'terrain_red_01_roughness_2k.jpg'))
    S['bark'] = pbr_material('bark', COR + 'cottonwood_bark_Bark001_albedo_weathered_1886_2k.jpg',
                             PBR + 'Bark001/Bark001_2K-JPG_NormalGL.jpg', PBR + 'Bark001/Bark001_2K-JPG_Roughness.jpg', normal_strength=1.5, tint=(0.42, 0.4, 0.37))
    S['bone'] = flat_material('antler', srgb('#d8d0bf'), 0.65)
    S['bone2'] = flat_material('antler_base', srgb('#8a7a62'), 0.75)
    S['chair'] = flat_material('chair_wood', srgb('#4a3a2a'), 0.55)
    S['iron'] = flat_material('iron', srgb('#2a2826'), 0.5, 0.6)
    S['leather'] = flat_material('leather', srgb('#5a3b22'), 0.55)
    S['lumber'] = pbr_material('fresh_lumber', COR + 'doors_Planks021_albedo_fresh_1885_2k.jpg',
                               PBR + 'Planks021/Planks021_2K-JPG_NormalGL.jpg', PBR + 'Planks021/Planks021_2K-JPG_Roughness.jpg')
    S['flagstone'] = pbr_material('forge_stone', COR + 'blacksmith_flagstones_old_sandstone_02_albedo_weathered_1886_2k.jpg',
                                  p('old_sandstone_02', 'old_sandstone_02_normal_gl_2k.jpg'), p('old_sandstone_02', 'old_sandstone_02_roughness_2k.jpg'))
    return S


# ----------------------------------------------------------------- mesh builder
SMOOTH_MK = {}      # material key -> crease angle (deg) for smooth-shaded detailed props


class Builder:
    """Accumulates geometry per material, emits one object per (group, material)."""

    def __init__(self, mats, seed=1):
        self.mats = mats
        self.parts = {}          # (group, matkey) -> [verts, faces, uvs]
        self.rng = random.Random(seed)
        self.group = 'house'
        self.col = (1.0, 1.0, 1.0)

    def _bucket(self, mk):
        key = (self.group, mk)
        if key not in self.parts:
            self.parts[key] = ([], [], [], [])
        return self.parts[key]

    def face(self, mk, pts, uvs):
        V, F, U, C = self._bucket(mk)
        i0 = len(V)
        V.extend([tuple(p) for p in pts])
        F.append(tuple(range(i0, i0 + len(pts))))
        U.append([tuple(u) for u in uvs])
        C.append(self.col)

    def quad_auto(self, mk, pts, tile, grain=None, off=(0, 0)):
        """Planar UV: project onto the face plane; U along grain (or first edge)."""
        p = [Vector(x) for x in pts]
        n = (p[1] - p[0]).cross(p[2] - p[0])
        if n.length < 1e-12:
            n = Vector((0, 0, 1))
        n.normalize()
        u = Vector(grain) if grain is not None else (p[1] - p[0])
        u = u - n * u.dot(n)
        if u.length < 1e-9:
            u = (p[1] - p[0]); u = u - n * u.dot(n)
        if u.length < 1e-9:
            u = n.orthogonal()
        u.normalize(); v = n.cross(u)
        uvs = [(q.dot(u) / tile + off[0], q.dot(v) / tile + off[1]) for q in p]
        self.face(mk, pts, uvs)

    # oriented box: center c, unit axes ax=(a0,a1,a2), half sizes h
    def obox(self, mk, c, ax, h, tile=1.0, grain=0, endmk=None, skip=()):
        c = Vector(c); a = [Vector(x).normalized() for x in ax]
        corners = {}
        for sx in (-1, 1):
            for sy in (-1, 1):
                for sz in (-1, 1):
                    corners[(sx, sy, sz)] = c + a[0] * h[0] * sx + a[1] * h[1] * sy + a[2] * h[2] * sz
        g = a[grain]
        off = (self.rng.random() * 5, self.rng.random() * 5)
        faces = {
            '+0': [(1, -1, -1), (1, 1, -1), (1, 1, 1), (1, -1, 1)],
            '-0': [(-1, 1, -1), (-1, -1, -1), (-1, -1, 1), (-1, 1, 1)],
            '+1': [(1, 1, -1), (-1, 1, -1), (-1, 1, 1), (1, 1, 1)],
            '-1': [(-1, -1, -1), (1, -1, -1), (1, -1, 1), (-1, -1, 1)],
            '+2': [(-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1)],
            '-2': [(-1, 1, -1), (1, 1, -1), (1, -1, -1), (-1, -1, -1)],
        }
        for k, f in faces.items():
            if k in skip:
                continue
            m = mk
            if endmk and k[1] == str(grain):
                m = endmk
            self.quad_auto(m, [corners[t] for t in f], tile, grain=None if k[1] == str(grain) else g, off=off)

    def box(self, mk, mn, mx, tile=1.0, grain=0, endmk=None, skip=()):
        c = [(mn[i] + mx[i]) / 2 for i in range(3)]
        h = [(mx[i] - mn[i]) / 2 for i in range(3)]
        self.obox(mk, c, ((1, 0, 0), (0, 1, 0), (0, 0, 1)), h, tile, grain, endmk, skip)

    def tube(self, mk, path, radii, sides=8, tile=0.5, cap=True, jitter=0.0, endmk=None):
        """Generalized cylinder along polyline path with per-point radius."""
        rng = self.rng
        rings = []
        n_prev = None
        for i, p in enumerate(path):
            p = Vector(p)
            if i == 0:
                t = Vector(path[1]) - p
            elif i == len(path) - 1:
                t = p - Vector(path[-2])
            else:
                t = Vector(path[i + 1]) - Vector(path[i - 1])
            t.normalize()
            if n_prev is None:
                n_prev = t.orthogonal().normalized()
            n = (n_prev - t * n_prev.dot(t)).normalized(); n_prev = n
            b = t.cross(n)
            r = radii[i] if isinstance(radii, (list, tuple)) else radii
            ring = []
            for k in range(sides):
                ang = 2 * math.pi * k / sides
                rr = r * (1 + (rng.uniform(-jitter, jitter) if jitter else 0))
                ring.append(p + (n * math.cos(ang) + b * math.sin(ang)) * rr)
            rings.append(ring)
        # along-length distance for UV
        dist = [0.0]
        for i in range(1, len(path)):
            dist.append(dist[-1] + (Vector(path[i]) - Vector(path[i - 1])).length)
        r0 = radii[0] if isinstance(radii, (list, tuple)) else radii
        circ = 2 * math.pi * r0
        off = rng.random() * 3
        for i in range(len(rings) - 1):
            for k in range(sides):
                k2 = (k + 1) % sides
                pts = [rings[i][k], rings[i][k2], rings[i + 1][k2], rings[i + 1][k]]
                uv = [(dist[i] / tile + off, k / sides * circ / tile), (dist[i] / tile + off, (k + 1) / sides * circ / tile),
                      (dist[i + 1] / tile + off, (k + 1) / sides * circ / tile), (dist[i + 1] / tile + off, k / sides * circ / tile)]
                self.face(mk, pts, uv)
        if cap:
            m = endmk or mk
            for ring, rev in ((rings[0], True), (rings[-1], False)):
                pts = list(reversed(ring)) if rev else ring
                cen = sum(pts, Vector()) / len(pts)
                self.quad_auto(m, pts, 0.3)

    def emit(self, collection=None):
        objs = []
        for (grp, mk), (V, F, U, C) in self.parts.items():
            if not F:
                continue
            me = bpy.data.meshes.new(f'{grp}_{mk}')
            me.from_pydata(V, [], F)
            uvl = me.uv_layers.new(name='UVMap')
            li = 0
            for fi, poly in enumerate(me.polygons):
                for j, l in enumerate(poly.loop_indices):
                    uvl.data[l].uv = U[fi][j]
            ca = me.color_attributes.new('Col', 'BYTE_COLOR', 'CORNER')
            for fi, poly in enumerate(me.polygons):
                c = C[fi]
                for l in poly.loop_indices:
                    ca.data[l].color = (c[0], c[1], c[2], 1.0)
            me.validate(); me.update()
            if mk in SMOOTH_MK:          # detailed props: weld coincident vertices, smooth with sharp creases
                import bmesh
                bm = bmesh.new(); bm.from_mesh(me)
                bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0003)
                bm.to_mesh(me); bm.free()
                me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(SMOOTH_MK[mk]))
            ob = bpy.data.objects.new(f'{grp}_{mk}', me)
            ob.data.materials.append(self.mats[mk])
            ob['group'] = grp
            (collection or bpy.context.scene.collection).objects.link(ob)
            if mk not in SMOOTH_MK:
                for p in me.polygons:
                    p.use_smooth = False
            objs.append(ob)
        self.parts = {}
        return objs
