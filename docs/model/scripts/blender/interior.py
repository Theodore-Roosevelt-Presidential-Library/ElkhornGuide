"""Elkhorn ranch house interior, c. 1886 — draft interpretation.

Evidence (see spec/interior_evidence.json): T.R., Hunting Trips of a Ranchman (1885) pp.11-12 and Ranch Life and the
Hunting-Trail (1888) p.36; T.R., Autobiography (1913) ch. IV; Hagedorn (1921) p.240; Sewall (1919); Taylor (1959)
house and cellar artifacts; Edith Roosevelt's 1890 room sketch (via Mattison 1960); NPS Furnishing Plan for a
Badlands Ranch House (1969).

Plan decision (interpretive, flagged): Taylor found only one chimney, at X 12.67-14 / Y 22-24, on the line of the
hall's west wall. T.R. wrote of a sitting room with a big fireplace next to his bedroom (SE). The model reconciles the
two with a double-sided stack: the sitting-room fireplace opens EAST from that chimney, and the kitchen cookstove is
piped into its west face. That makes the sitting room the full width east of the kitchen (X 14-30, Y 14-31.5), with
the hall running into it from the south door and out of it to the north rooms.
Coordinates: house feet (origin SW outside corner); floor top FL, ceiling CE."""
import math, random
from mathutils import Vector, Matrix
import bpy
import lib
from lib import FT

FL = 1.6          # floor top (door sills at 1.604 ft)
CE = 9.03         # ceiling underside (7'5" clear)
TW = 10 / 12.0    # log wall thickness
IX0, IX1, IY0, IY1 = TW, 30 - TW, TW, 60 - TW     # interior faces of the log walls


def m(v):
    return Vector(v) * FT


# ----------------------------------------------------------------- materials
def col_material(name, rough=0.7, metal=0.0, spec=0.5):
    """Base colour from the per-face colour attribute (so one material serves many tinted objects)."""
    mt = bpy.data.materials.new(name); mt.use_nodes = True
    nt = mt.node_tree; b = nt.nodes['Principled BSDF']
    va = nt.nodes.new('ShaderNodeVertexColor'); va.layer_name = 'Col'
    nt.links.new(va.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    mt['x_flatcol'] = 1
    return mt


def fur_material(name, rgb, length=0.6):
    """Hair-on hide: noise-modulated colour and a strong fine bump so it reads as fur at room scale."""
    mt = bpy.data.materials.new(name); mt.use_nodes = True
    nt = mt.node_tree; b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 60.0; nz.inputs['Detail'].default_value = 12
    nz2 = nt.nodes.new('ShaderNodeTexNoise'); nz2.inputs['Scale'].default_value = 4.0
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector']); nt.links.new(tc.outputs['Object'], nz2.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].color = (rgb[0] * 0.45, rgb[1] * 0.45, rgb[2] * 0.45, 1)
    ramp.color_ramp.elements[1].color = (min(1, rgb[0] * 1.3), min(1, rgb[1] * 1.3), min(1, rgb[2] * 1.3), 1)
    mix = nt.nodes.new('ShaderNodeMath'); mix.operation = 'MULTIPLY'
    nt.links.new(nz.outputs['Fac'], mix.inputs[0]); nt.links.new(nz2.outputs['Fac'], mix.inputs[1])
    add = nt.nodes.new('ShaderNodeMath'); add.operation = 'MULTIPLY_ADD'; add.inputs[1].default_value = 1.6; add.inputs[2].default_value = 0.0
    nt.links.new(mix.outputs[0], add.inputs[0]); nt.links.new(add.outputs[0], ramp.inputs['Fac'])
    va = nt.nodes.new('ShaderNodeVertexColor'); va.layer_name = 'Col'
    mul = nt.nodes.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    nt.links.new(ramp.outputs['Color'], mul.inputs[6]); nt.links.new(va.outputs['Color'], mul.inputs[7])
    nt.links.new(mul.outputs[2], b.inputs['Base Color'])
    bm = nt.nodes.new('ShaderNodeBump'); bm.inputs['Strength'].default_value = length; bm.inputs['Distance'].default_value = 0.01
    nt.links.new(nz.outputs['Fac'], bm.inputs['Height']); nt.links.new(bm.outputs['Normal'], b.inputs['Normal'])
    b.inputs['Roughness'].default_value = 0.95
    mt['x_flat_rgb'] = list(rgb)
    return mt


def build_materials(mats):
    COR = lib.COR; PBR = lib.PBR
    def p(s, f): return PBR + s + '/' + f
    mats['pine'] = lib.pbr_material('pine_partition', COR + 'doors_Planks021_albedo_fresh_1885_2k.jpg',
                                    PBR + 'Planks021/Planks021_2K-JPG_NormalGL.jpg', PBR + 'Planks021/Planks021_2K-JPG_Roughness.jpg',
                                    normal_strength=0.6, tint=(0.82, 0.74, 0.6))
    mats['floor'] = lib.pbr_material('pine_floor', COR + 'porch_floor_raw_wooden_floor_01_albedo_fresh_1885_2k.jpg',
                                     p('raw_wooden_floor_01', 'raw_wooden_floor_01_normal_gl_2k.jpg'), p('raw_wooden_floor_01', 'raw_wooden_floor_01_rough_2k.jpg') if False else None,
                                     0.7, normal_strength=0.8, tint=(0.78, 0.66, 0.5))
    mats['ilog'] = lib.pbr_material('log_walls_interior', lib.M + '/tex/hewn_cottonwood_fresh_albedo.jpg', lib.M + '/tex/hewn_cottonwood_fresh_normal.png',
                                    lib.M + '/tex/hewn_cottonwood_fresh_rough.jpg', normal_strength=1.0, tint=(0.92, 0.84, 0.7))
    mats['paint'] = col_material('painted_wood', 0.6)
    mats['cloth'] = col_material('cloth', 0.95)
    mats['book'] = col_material('book_cloth', 0.75)
    mats['ware'] = col_material('glazed_ware', 0.15)
    mats['tin'] = col_material('tinware', 0.35, 0.9)
    mats['castiron'] = col_material('cast_iron', 0.55, 0.6)
    mats['nickel'] = col_material('nickel_trim', 0.2, 1.0)
    mats['rubber'] = col_material('india_rubber', 0.4)
    mats['paper'] = col_material('paper', 0.8)
    IT = lib.M + '/tex/interior/'
    def tx(key, name, normal=True, rough=0.9, ns=1.0, tint=None):
        mats[key] = lib.pbr_material(name, IT + name + '_albedo.jpg', IT + name + '_normal.png' if normal else None, None, rough, normal_strength=ns, tint=tint)
    tx('buffalo', 'buffalo', ns=1.4); tx('bear', 'bear', rough=0.6, ns=1.2); tx('wolf', 'wolf', ns=1.2)
    tx('elkhide', 'elkhide', ns=0.8); tx('coon', 'coon', ns=1.2)
    tx('blanket', 'blanket_plaid', ns=0.6); tx('pointblanket', 'blanket_point', ns=0.6)
    tx('books', 'books', rough=0.7, ns=0.8); tx('oilcloth', 'oilcloth', rough=0.25, ns=0.3)
    tx('transfer', 'transferware', normal=False, rough=0.12)
    tx('duck', 'duck', ns=0.6); tx('ticking', 'ticking', ns=0.5); tx('sacking', 'sacking', ns=1.0)
    tx('tinlabel', 'tinlabel', normal=False, rough=0.5)
    mats['castiron'] = lib.pbr_material('cast_iron_tex', IT + 'castiron_albedo.jpg', IT + 'castiron_normal.png', None, 0.6, normal_strength=0.8)
    ember = bpy.data.materials.new('embers'); ember.use_nodes = True
    eb = ember.node_tree.nodes['Principled BSDF']; eb.inputs['Base Color'].default_value = (0.05, 0.02, 0.01, 1)
    eb.inputs['Emission Color'].default_value = (1.0, 0.35, 0.08, 1); eb.inputs['Emission Strength'].default_value = 6.0
    mats['ember'] = ember
    flame = bpy.data.materials.new('lamp_flame'); flame.use_nodes = True
    fb = flame.node_tree.nodes['Principled BSDF']; fb.inputs['Emission Color'].default_value = (1.0, 0.6, 0.25, 1); fb.inputs['Emission Strength'].default_value = 25.0
    mats['flame'] = flame


# ----------------------------------------------------------------- helpers
def box(b, mk, x0, y0, z0, x1, y1, z1, col=None, tile=1.0, grain=0):
    prev = b.col
    if col: b.col = col
    b.box(mk, m((x0, y0, z0)), m((x1, y1, z1)), tile, grain)
    b.col = prev


def obox(b, mk, c, yaw, hx, hy, hz, col=None, tile=1.0, grain=0, tilt=0.0):
    prev = b.col
    if col: b.col = col
    R = Matrix.Rotation(yaw, 3, 'Z') @ Matrix.Rotation(tilt, 3, 'X')
    b.obox(mk, m(c), (R @ Vector((1, 0, 0)), R @ Vector((0, 1, 0)), R @ Vector((0, 0, 1))), (hx * FT, hy * FT, hz * FT), tile, grain)
    b.col = prev


def cyl(b, mk, p0, p1, r, col=None, sides=12, r1=None):
    prev = b.col
    if col: b.col = col
    b.tube(mk, [m(p0), m(p1)], [r * FT, (r1 if r1 is not None else r) * FT], sides=sides, tile=1.0)
    b.col = prev


def lathe(b, mk, base, prof, col=None, sides=16):
    """Turned/raised vessel: prof = [(radius, z)] bottom to top (ft)."""
    prev = b.col
    if col: b.col = col
    base = Vector(base)
    b.tube(mk, [m(base + Vector((0, 0, z))) for r, z in prof], [max(0.002, r) * FT for r, z in prof], sides=sides, tile=0.5)
    b.col = prev


class Local:
    """Local object frame; yaw in RADIANS (all callers pass math.radians(...))."""
    def __init__(self, x, y, z, yaw):
        self.o = Vector((x, y, z)); self.R = Matrix.Rotation(yaw, 3, 'Z'); self.yaw = yaw
    def __call__(self, x, y, z=0.0):
        return tuple(self.o + self.R @ Vector((x, y, z)))


# ----------------------------------------------------------------- architecture
# partitions: (axis, fixed, a0, a1, doors[(c, w)])  axis 'x' = wall runs along X at Y=fixed; 'y' = runs along Y at X=fixed
PARTITIONS = [
    ('y', 14.0, IY0, 14.0, [(7.3, 2.67)]),                 # hall / dining room
    ('y', 18.0, IY0, 14.0, [(10.3, 2.67)]),                # hall / T.R.'s room
    ('x', 14.0, 18.0, IX1, [(21.2, 2.67)]),                # T.R.'s room / sitting room (connecting door)
    ('x', 15.0, IX0, 12.67, [(6.3, 2.67)]),                # dining room / kitchen
    ('y', 13.92, 15.0, 22.0, []),                          # kitchen / sitting room, south of the chimney
    ('y', 13.92, 24.0, 34.0, [(27.3, 2.67)]),              # ... north of the chimney, door kitchen <-> sitting room
    ('x', 31.5, 18.0, IX1, []),                            # sitting room / Bamie's room
    ('x', 31.5, 14.0, 13.92, []),
    ('x', 34.0, IX0, 14.0, []),                            # kitchen / work room
    ('y', 14.0, 34.0, 46.0, [(39.3, 2.67)]),               # hall / work room
    ('y', 18.0, 31.5, 44.0, [(37.3, 2.67)]),               # hall / Bamie's room
    ('x', 44.0, 15.0, IX1, [(16.5, 2.4)]),                 # hall end / NE work room
    ('x', 46.0, IX0, 15.0, [(7.3, 2.67)]),                 # west work room / NW room
    ('y', 15.0, 44.0, IY1, []),                            # NW room / NE work room
]
ROOMS = [
    dict(name='Sitting room', x=(14, IX1), y=(14, 31.5), evidence='strong',
         note="T.R.: 'a sitting-room with a big fire-place' (Autobiography); rifles on elk antlers over the fireplace, deer horns hung with fur coats, rough board book shelves, rocking chair, elk hides and wolf skins on the hearth (HTR 1885; RLHT 1888)."),
    dict(name="T.R.'s bedroom", x=(18, IX1), y=(IY0, 14), evidence='partial',
         note="Hagedorn 1921: his bedroom adjoined the room with the fireplace; Edith's 1890 plan; rubber bathtub (Autobiography); T.R.'s wicker-and-duck trunk (NPS)."),
    dict(name='Kitchen', x=(IX0, 13.92), y=(15, 34), evidence='partial',
         note="Taylor 1959: brick flue with stovepipe thimble; trapdoor to the cellar darkroom. Cookstove form from period catalogs."),
    dict(name='Dining room', x=(IX0, 14), y=(IY0, 15), evidence='conjectural',
         note="Edith 1890 plan; Osterhout c.1895: 'a table and some cupboards'; blue-printed whiteware sherds (Taylor)."),
    dict(name='Hall', x=(14, 18), y=(IY0, 44), evidence='partial', note="Hagedorn: a corridor running north and south; Mattison: about three-quarters of the house's length."),
    dict(name='Work room', x=(IX0, 14), y=(34, 46), evidence='conjectural', note="Edith 1890 'ironing room'; Sewall's room in T.R.'s 1884 sketch."),
    dict(name="Bamie's room (1890)", x=(18, IX1), y=(31.5, 44), evidence='conjectural', note="Edith 1890 plan."),
    dict(name='North rooms (Sewall and Dow families)', x=(IX0, IX1), y=(44, IY1), evidence='conjectural',
         note="Two families 1885-86; twin cradle built by Sewall (NPS 1969); women's and children's items in Taylor's finds."),
]


def floor_and_ceiling(b, rng):
    b.group = 'interior'
    # floor: 6-7 in pine boards running E-W (across the joists that span N-S)
    y = IY0
    while y < IY1:
        w = rng.uniform(0.5, 0.6); g = rng.uniform(0.85, 1.08)
        box(b, 'floor', IX0, y + 0.004, FL - 0.08, IX1, min(y + w, IY1) - 0.004, FL, col=(g, g * 0.98, g * 0.95), tile=1.5, grain=0)
        y += w
    # ceiling: boards on 2x6 joists (joists exposed, as in the "beams and rafters" T.R. hung horns from)
    b.group = 'ceiling'
    x = IX0
    while x < IX1:
        w = rng.uniform(0.5, 0.6); g = rng.uniform(0.82, 1.0)
        box(b, 'pine', x + 0.004, IY0, CE, min(x + w, IX1) - 0.004, IY1, CE + 0.08, col=(g * 0.9, g * 0.86, g * 0.8), tile=1.5, grain=1)
        x += w
    y = IY0 + 1.0
    while y < IY1 - 0.5:
        box(b, 'pine', IX0, y - 0.08, CE - 0.45, IX1, y + 0.08, CE, col=(0.8, 0.74, 0.66), tile=1.5, grain=0)
        y += 2.0
    b.group = 'interior'


def partitions(b, rng):
    """Vertical matched pine boards, planed one side (Sewall 1884), ~1 in thick, on 2x4 plates; plank doors with thumb latches."""
    head = FL + 6.5
    for axis, f, a0, a1, doors in PARTITIONS:
        cuts = sorted([(c - w / 2, c + w / 2) for c, w in doors])
        a = a0
        while a < a1 - 0.01:
            w = min(rng.uniform(0.62, 0.8), a1 - a)
            mid = a + w / 2
            inside = [(c0, c1) for (c0, c1) in cuts if c0 - 0.01 < mid < c1 + 0.01]
            g = rng.uniform(0.88, 1.06); col = (g, g * 0.97, g * 0.92)
            z0 = head if inside else FL
            if axis == 'y':
                box(b, 'pine', f - 0.04, a + 0.006, z0, f + 0.04, a + w - 0.006, CE, col=col, tile=1.2, grain=2)
            else:
                box(b, 'pine', a + 0.006, f - 0.04, z0, a + w - 0.006, f + 0.04, CE, col=col, tile=1.2, grain=2)
            a += w
        for (c0, c1) in cuts:
            # casing + plank door standing ajar
            for (q0, q1) in ((c0 - 0.3, c0), (c1, c1 + 0.3)):
                if axis == 'y': box(b, 'pine', f - 0.07, q0, FL, f + 0.07, q1, head + 0.3, col=(0.8, 0.72, 0.6), tile=1.0, grain=2)
                else: box(b, 'pine', q0, f - 0.07, FL, q1, f + 0.07, head + 0.3, col=(0.8, 0.72, 0.6), tile=1.0, grain=2)
            if axis == 'y': box(b, 'pine', f - 0.07, c0, head, f + 0.07, c1, head + 0.3, col=(0.8, 0.72, 0.6))
            else: box(b, 'pine', c0, f - 0.07, head, c1, f + 0.07, head + 0.3, col=(0.8, 0.72, 0.6))
            ang = math.radians(rng.uniform(55, 100))
            L = c1 - c0
            if axis == 'y':
                hinge = Vector((f, c0, 0)); d = Vector((math.sin(ang), math.cos(ang), 0))
            else:
                hinge = Vector((c0, f, 0)); d = Vector((math.cos(ang), math.sin(ang), 0))
            c = hinge + d * L / 2
            obox(b, 'door', (c.x, c.y, FL + 3.25), math.atan2(d.y, d.x), L / 2, 0.06, 3.22, col=(0.95, 0.9, 0.85), tile=1.2, grain=2)


def fireplace(b, rng):
    """Brick fireplace opening east into the sitting room from Taylor's chimney (X 12.67-14, Y 22-24); flat
    sandstone hearthstone; plank mantel; Dow's andirons forged from a steel rail found in the river (Hagedorn p.240)."""
    x0 = 13.92                                    # sitting-room face of the kitchen partition
    xf = x0 + 1.6                                 # face of the breast
    y0, y1, top = 21.9, 24.1, FL + 2.4            # opening
    box(b, 'brick', x0, 20.6, FL, x0 + 0.45, 25.4, CE, tile=1.1)                 # back of the firebox
    box(b, 'brick', x0, 20.6, FL, xf, y0, CE, tile=1.1)                          # left pier
    box(b, 'brick', x0, y1, FL, xf, 25.4, CE, tile=1.1)                          # right pier
    box(b, 'brick', x0, y0, top, xf, y1, CE, tile=1.1)                           # breast above the opening
    box(b, 'iron', xf - 0.12, y0 - 0.05, top - 0.05, xf + 0.02, y1 + 0.05, top + 0.08)   # iron lintel bar
    box(b, 'interior', x0 + 0.45, y0, FL, x0 + 0.47, y1, top)                   # sooty back
    box(b, 'interior', x0 + 0.45, y0, top - 0.02, xf - 0.12, y1, top)           # sooty throat
    for yy in (y0, y1 - 0.02):
        box(b, 'interior', x0 + 0.45, yy, FL, xf - 0.05, yy + 0.02, top)        # sooty cheeks
    box(b, 'flagstone', x0 + 0.45, y0, FL - 0.02, xf, y1, FL + 0.02, tile=1.5)   # firebox floor
    # hearthstone (the State Historical Society recovered a hearthstone from the site; size not known)
    box(b, 'flagstone', xf, 20.9, FL - 0.02, xf + 2.0, 25.1, FL + 0.07, tile=2.5)
    # mantel shelf on two brackets
    box(b, 'pine', xf - 0.1, 20.4, FL + 4.4, xf + 0.55, 25.6, FL + 4.55, col=(0.7, 0.6, 0.48), tile=1.2, grain=1)
    for yy in (20.9, 25.1):
        box(b, 'pine', xf, yy - 0.08, FL + 3.9, xf + 0.4, yy + 0.08, FL + 4.4, col=(0.66, 0.56, 0.44))
    # andirons: crude, from a rail
    for yy in (22.4, 23.6):
        box(b, 'iron', x0 + 0.6, yy - 0.06, FL + 0.05, xf, yy + 0.06, FL + 0.32)
        box(b, 'iron', xf - 0.15, yy - 0.12, FL + 0.05, xf, yy + 0.12, FL + 1.0)
    # pine logs on the andirons and embers beneath
    for k, (z, yb) in enumerate(((0.5, 0.0), (0.68, 0.12), (0.86, -0.05))):
        cyl(b, 'bark', (x0 + 0.75 + k * 0.18, y0 + 0.1 + yb, FL + z), (x0 + 0.8 + k * 0.16, y1 - 0.1 + yb, FL + z + 0.04), 0.2 - 0.03 * k)
    box(b, 'ember', x0 + 0.6, y0 + 0.2, FL + 0.03, x0 + 1.35, y1 - 0.2, FL + 0.2)
    # fire irons: poker and shovel leaning on the pier
    cyl(b, 'iron', (xf + 0.15, 25.2, FL + 0.05), (xf + 0.05, 25.35, FL + 3.0), 0.03)
    cyl(b, 'iron', (xf + 0.25, 25.1, FL + 0.05), (xf + 0.1, 25.3, FL + 2.9), 0.03)
    box(b, 'iron', xf + 0.2, 25.0, FL + 0.05, xf + 0.32, 25.25, FL + 0.4)
    # mantel things: lamp, clock-less shelf with tobacco jar, clay pipe (Taylor), cartridge boxes, candlestick
    lamp(b, (xf + 0.2, 21.2, FL + 4.55), lit=False)
    detail.revolve(b, 'yellowware', (xf + 0.2, 24.6, FL + 4.55), [(0.0, 0.0), (0.15, 0.0), (0.18, 0.04), (0.2, 0.2), (0.18, 0.32), (0.15, 0.35),
                   (0.155, 0.37), (0.12, 0.4), (0.04, 0.42), (0.035, 0.45), (0.0, 0.46)], 32, col=(0.42, 0.3, 0.2), smooth_n=2)   # salt-glazed tobacco jar
    cyl(b, 'ware', (xf + 0.25, 23.6, FL + 4.6), (xf + 0.32, 24.0, FL + 4.62), 0.02, col=(0.92, 0.9, 0.86), sides=6)
    for k in range(3):
        box(b, 'paper', xf + 0.05, 22.3 + k * 0.32, FL + 4.55, xf + 0.35, 22.55 + k * 0.32, FL + 4.75, col=(0.6, 0.35, 0.2) if k % 2 else (0.75, 0.62, 0.3))
    # elk antlers jutting out over the fireplace, two rifles across them (HTR 1885)
    import props
    props.antler_rack(b, (xf + 0.1, 23.0, FL + 5.6), (1, 0, 0.35), scale=1.0, rng=rng, skull=True, wall=0.1)
    props.rifle(b, (xf + 0.55, 20.9, FL + 6.4), (xf + 0.55, 25.6, FL + 6.25), rng)
    props.rifle(b, (xf + 0.75, 21.3, FL + 6.8), (xf + 0.75, 25.3, FL + 6.7), rng)


def stovepipe(b, x, y, z0, xz):
    """Pipe rising from a stove and turning into the chimney thimble at height xz."""
    cyl(b, 'castiron', (x, y, z0), (x, y, xz), 0.25, col=(1.1, 1.1, 1.1))
    cyl(b, 'castiron', (x, y, xz), (12.67, y, xz), 0.25, col=(1.1, 1.1, 1.1))


def cookstove(b, x, y, yaw, rng):
    """Cast-iron wood range with reservoir and warming closet, c.1880 (Abendroth 'Norfolk' pattern): body ~30 in to the
    cooktop, 40 in wide with the reservoir, 26 in deep, on cabriole legs, nickel trim."""
    L = Local(x, y, FL, yaw)
    K = (1.0, 1.0, 1.0); NI = (0.75, 0.75, 0.72)
    def B(x0, y0, z0, x1, y1, z1, mk='castiron', col=K):
        c = L((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)
        obox(b, mk, c, L.yaw, (x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2, col=col)
    B(-1.4, -1.05, 0.55, 1.4, 1.05, 2.45)                    # firebox + oven body
    B(-1.5, -1.12, 2.45, 1.5, 1.12, 2.55, col=(0.8, 0.8, 0.8))   # cooktop
    for i, xx in enumerate((-0.9, -0.1, 0.7)):
        for yy in (-0.45, 0.45):
            cyl(b, 'castiron', L(xx, yy, 2.55), L(xx, yy, 2.57), 0.33, col=(0.7, 0.7, 0.7), sides=16)
    B(1.4, -1.0, 0.75, 2.2, 1.0, 2.5, col=(1.1, 1.1, 1.1))        # reservoir
    B(2.2, -1.02, 2.45, 2.25, 1.02, 2.55, mk='nickel', col=NI)
    B(-1.5, -1.12, 0.55, 2.25, -1.08, 0.62, mk='nickel', col=NI)      # nickel apron rail
    B(-1.0, -1.1, 1.0, 0.9, -1.06, 2.2, col=(1.25, 1.25, 1.25))      # oven door
    cyl(b, 'nickel', L(-0.8, -1.16, 1.9), L(0.6, -1.16, 1.9), 0.04, col=NI)
    for sx in (-1.32, 1.32):                                         # cast brackets carrying the warming closet
        B(sx - 0.05, 0.72, 2.55, sx + 0.05, 0.9, 3.6)
    B(-1.3, 0.3, 3.6, 1.3, 0.9, 4.25, col=(1.0, 1.0, 1.0))           # raised warming closet over the back of the top
    B(-1.4, 0.2, 4.25, 1.4, 0.95, 4.35, col=(0.9, 0.9, 0.9))
    B(-1.3, 0.26, 3.6, 1.3, 0.3, 3.65, mk='nickel', col=NI)
    for sx in (-1.3, 1.3):
        for sy in (-0.95, 0.95):
            cyl(b, 'castiron', L(sx, sy, 0.0), L(sx * 1.05, sy * 1.05, 0.55), 0.09, col=K, r1=0.12)
    p = L(-0.9, 0.62, 2.55)
    stovepipe(b, p[0], p[1], p[2], FL + 6.4)


def plate_rack_cupboard(b, x, y, yaw, rng):
    """Painted pine cupboard, glazed-less open shelves with blue-printed whiteware (Taylor's sherds), tin pans."""
    L = Local(x, y, FL, yaw)
    W, D, H = 3.4, 1.3, 6.0
    col = (0.34, 0.15, 0.1)        # red-brown milk paint (period colour; actual paint unknown)
    def B(x0, y0, z0, x1, y1, z1, mk='paint', c=col):
        obox(b, mk, L((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2), L.yaw, (x1 - x0) / 2, (y1 - y0) / 2, (z1 - z0) / 2, col=c)
    B(-W / 2, 0, 0, -W / 2 + 0.07, D, H); B(W / 2 - 0.07, 0, 0, W / 2, D, H); B(-W / 2, D - 0.05, 0, W / 2, D, H)
    B(-W / 2, 0, H - 0.1, W / 2, D, H)
    B(-W / 2, -0.02, 0.05, W / 2, D, 2.6, c=(0.3, 0.13, 0.09))               # lower doors
    for z in (2.6, 3.7, 4.8):
        B(-W / 2, 0.1, z, W / 2, D, z + 0.07)
    for z in (3.75, 4.85):
        for k in range(6):
            xx = -1.3 + k * 0.5
            c = L(xx, D - 0.35, z + 0.42)
            plate(b, (c[0], c[1], c[2]), 0.36, normal=tuple(Matrix.Rotation(L.yaw, 3, 'Z') @ Vector((0, -1, 0.25))))
    for k in range(5):
        c = L(-1.3 + k * 0.6, 0.5, 2.67)
        if k % 2:
            cup(b, c, handle_angle=L.yaw + math.pi / 2, with_saucer=False)
        else:
            detail.revolve(b, 'whiteware', c, [(0.0, 0.0), (0.1, 0.0), (0.11, 0.02), (0.2, 0.15), (0.23, 0.22), (0.215, 0.225), (0.18, 0.16), (0.1, 0.04), (0.0, 0.035)], 32, col=(0.94, 0.94, 0.9))


def plate(b, c, r, normal=(0, 0, 1)):
    """Plate with a printed face (planar UV, print centred) and a thin rim."""
    c = Vector(c); n = Vector(normal).normalized()
    a1 = n.orthogonal().normalized(); a2 = n.cross(a1)
    N = 20
    ring = [c + (a1 * math.cos(2 * math.pi * k / N) + a2 * math.sin(2 * math.pi * k / N)) * r + n * 0.02 for k in range(N)]
    for k in range(N):
        k2 = (k + 1) % N
        b.face('transfer', [m(c + n * 0.008), m(ring[k]), m(ring[k2])],
               [(0.5, 0.5), (0.5 + 0.5 * math.cos(2 * math.pi * k / N), 0.5 + 0.5 * math.sin(2 * math.pi * k / N)),
                (0.5 + 0.5 * math.cos(2 * math.pi * k2 / N), 0.5 + 0.5 * math.sin(2 * math.pi * k2 / N))])
    prev = b.col; b.col = (0.93, 0.93, 0.9)
    b.tube('ware', [m(ring[k] - n * 0.03) for k in list(range(N)) + [0]], 0.012 * FT, sides=4, cap=False)
    b.col = prev


def cup(b, c, col=(0.93, 0.92, 0.88)):
    lathe(b, 'ware', c, [(0.1, 0), (0.13, 0.05), (0.16, 0.28), (0.165, 0.3)], col=col, sides=14)


def table(b, x, y, yaw, Lx, Ly, H=2.42, col=(0.62, 0.5, 0.36), cloth=None):
    L = Local(x, y, FL, yaw)
    obox(b, 'pine', L(0, 0, H - 0.05), L.yaw, Lx / 2, Ly / 2, 0.06, col=col, tile=1.2, grain=0)
    if cloth:
        obox(b, 'oilcloth', L(0, 0, H + 0.015), L.yaw, Lx / 2 + 0.15, Ly / 2 + 0.15, 0.01, col=(1, 1, 1), tile=0.9)
        for sx in (-1, 1):   # oilcloth hanging over the edge
            obox(b, 'oilcloth', L(sx * (Lx / 2 + 0.16), 0, H - 0.3), L.yaw, 0.01, Ly / 2 + 0.15, 0.32, col=(1, 1, 1), tile=0.9)
    for sx in (-1, 1):
        for sy in (-1, 1):
            obox(b, 'pine', L(sx * (Lx / 2 - 0.2), sy * (Ly / 2 - 0.2), (H - 0.1) / 2), L.yaw, 0.08, 0.08, (H - 0.1) / 2, col=col)
    obox(b, 'pine', L(0, Ly / 2 - 0.2, H - 0.3), L.yaw, Lx / 2 - 0.2, 0.04, 0.18, col=col)
    obox(b, 'pine', L(0, -Ly / 2 + 0.2, H - 0.3), L.yaw, Lx / 2 - 0.2, 0.04, 0.18, col=col)


def face_yaw(x, y, tx, ty):
    """Yaw that turns an object's front (local -y) toward (tx, ty)."""
    return math.atan2(tx - x, -(ty - y))


def side_chair(b, x, y, yaw, rng, col=(0.32, 0.22, 0.15)):
    """Plain spindle-back kitchen chair, c.1880 (cf. Met 1685): plank seat 17 in high, bamboo-turned legs."""
    L = Local(x, y, FL, yaw)
    obox(b, 'paint', L(0, 0, 1.42), L.yaw, 0.7, 0.68, 0.06, col=col)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cyl(b, 'paint', L(sx * 0.62, sy * 0.58, 0), L(sx * 0.55, sy * 0.5, 1.38), 0.05, col=col, sides=6)
    for k in range(6):
        xx = -0.45 + k * 0.18
        cyl(b, 'paint', L(xx * 0.9, 0.58, 1.48), L(xx, 0.68, 2.75), 0.028, col=col, sides=5)
    obox(b, 'paint', L(0, 0.7, 2.78), L.yaw, 0.62, 0.06, 0.12, col=col)
    for sy in (-1, 1):
        cyl(b, 'paint', L(-0.6, sy * 0.52, 0.5), L(0.6, sy * 0.52, 0.5), 0.03, col=col, sides=5)


def bookshelf(b, x, y, yaw, rng, W=4.0, n=3):
    """Rough board shelves on cleats (HTR: 'Rough board shelves hold a number of books'; Autobiography: 'enough books to
    fill two or three shelves')."""
    L = Local(x, y, FL, yaw)
    for k in range(n):
        z = 3.3 + k * 1.15
        obox(b, 'pine', L(0, 0.45, z), L.yaw, W / 2, 0.45, 0.05, col=(0.75, 0.64, 0.5), tile=1.2, grain=0)
        for sx in (-1, 1):
            obox(b, 'pine', L(sx * (W / 2 - 0.15), 0.1, z - 0.15), L.yaw, 0.06, 0.08, 0.12, col=(0.7, 0.6, 0.45))
        xx = -W / 2 + 0.15
        while xx < W / 2 - 0.25:
            t = rng.uniform(0.09, 0.2); h = rng.uniform(0.62, 0.95); dpt = rng.uniform(0.45, 0.7)
            c = rng.choice([(0.35, 0.12, 0.08), (0.18, 0.22, 0.14), (0.25, 0.16, 0.1), (0.12, 0.13, 0.18), (0.42, 0.32, 0.2), (0.3, 0.08, 0.06), (0.5, 0.42, 0.3)])
            lean = rng.uniform(-0.08, 0.08) if rng.random() < 0.2 else 0.0
            g = rng.uniform(0.75, 1.15)
            obox(b, 'books', L(xx + t / 2, 0.85 - dpt / 2, z + 0.05 + h / 2), L.yaw, t / 2, dpt / 2, h / 2, col=(g, g, g), tile=0.27, grain=2)
            xx += t + 0.005
            if rng.random() < 0.04: xx += 0.4


def writing_table(b, x, y, yaw, rng):
    """Small pine writing table (the park holds a small wooden writing desk said to have stood at Elkhorn)."""
    table(b, x, y, yaw, 3.2, 2.0, H=2.45, col=(0.48, 0.34, 0.22))
    L = Local(x, y, FL, yaw)
    obox(b, 'pine', L(0, -0.95, 2.15), L.yaw, 0.8, 0.04, 0.12, col=(0.42, 0.3, 0.2))     # drawer front
    lamp(b, L(1.0, 0.5, 2.45))
    lathe(b, 'ware', L(-0.6, 0.45, 2.45), [(0.12, 0), (0.12, 0.12), (0.05, 0.16), (0.03, 0.18)], col=(0.08, 0.08, 0.1), sides=10)   # inkwell
    for k in range(5):
        obox(b, 'paper', L(-0.1 + k * 0.03, -0.1 + k * 0.02, 2.47 + k * 0.004), L.yaw + rng.uniform(-.2, .2), 0.36, 0.46, 0.002, col=(0.86, 0.83, 0.74))
    obox(b, 'book', L(0.3, 0.55, 2.52), L.yaw + 0.3, 0.32, 0.45, 0.07, col=(0.2, 0.1, 0.07))


def lamp(b, base, lit=True):
    """Kerosene table lamp with crimped clear chimney (Taylor: 'castellated rim' chimney glass)."""
    base = Vector(base)
    lathe(b, 'tin', tuple(base), [(0.22, 0), (0.24, 0.05), (0.08, 0.15), (0.06, 0.45), (0.2, 0.6), (0.25, 0.8), (0.12, 0.98), (0.07, 1.02)], col=(0.6, 0.5, 0.3))
    lathe(b, 'glass', tuple(base + Vector((0, 0, 1.02))), [(0.07, 0), (0.13, 0.15), (0.1, 0.45), (0.09, 0.7), (0.11, 0.72)], sides=14)
    if lit:
        lathe(b, 'flame', tuple(base + Vector((0, 0, 1.05))), [(0.01, 0), (0.04, 0.05), (0.03, 0.1), (0.002, 0.16)], sides=8)


def lantern(b, base):
    base = Vector(base)
    lathe(b, 'tin', tuple(base), [(0.25, 0), (0.25, 0.25), (0.18, 0.3)], col=(0.45, 0.45, 0.42))
    lathe(b, 'glass', tuple(base + Vector((0, 0, 0.3))), [(0.16, 0), (0.22, 0.25), (0.16, 0.5)], sides=12)
    lathe(b, 'tin', tuple(base + Vector((0, 0, 0.8))), [(0.18, 0), (0.12, 0.15), (0.04, 0.2)], col=(0.45, 0.45, 0.42))


def skin(b, mk, cx, cy, z, L, W, yaw, rng, legs=True, head=False):
    """A hide laid flat: irregular outline with leg flaps; slight drape at the edges."""
    pts = []
    n = 28
    for k in range(n):
        a = 2 * math.pi * k / n
        r = 1.0 + 0.08 * math.sin(a * 5 + rng.uniform(0, 6))
        if legs:
            r += 0.22 * max(0, math.cos(2 * (a - math.pi / 4))) ** 6 + 0.22 * max(0, math.cos(2 * (a + math.pi / 4))) ** 6
        pts.append((math.cos(a) * L / 2 * r, math.sin(a) * W / 2 * r))
    R = Matrix.Rotation(yaw, 3, 'Z')
    cen = Vector((cx, cy, z + 0.03))
    ring = [Vector((cx, cy, z)) + R @ Vector((px, py, 0.0)) for px, py in pts]
    for k in range(n):
        a, c = ring[k], ring[(k + 1) % n]
        b.face(mk, [m(cen), m(a + Vector((0, 0, 0.01))), m(c + Vector((0, 0, 0.01)))], [(0.5, 0.5), (0.5 + pts[k][0] / L, 0.5 + pts[k][1] / W), (0.5 + pts[(k + 1) % n][0] / L, 0.5 + pts[(k + 1) % n][1] / W)])
    if head:
        hd = Vector((cx, cy, z)) + R @ Vector((L / 2 * 1.05, 0, 0.18))
        lathe(b, mk, tuple(hd - Vector((0, 0, 0.18))), [(0.35, 0), (0.42, 0.12), (0.3, 0.3), (0.0, 0.36)], sides=10)


def bed(b, x, y, yaw, rng, W=4.2, Lb=6.4, blanket=(0.55, 0.1, 0.08), robe=True):
    """Plain turned-post bedstead, straw tick + wool blankets; buffalo robe thrown over (T.R.: 'buffalo robes')."""
    L = Local(x, y, FL, yaw)
    wood = (0.38, 0.26, 0.16)
    for sx in (-1, 1):
        for sy, h in ((-1, 3.2), (1, 2.4)):
            cyl(b, 'paint', L(sx * W / 2, sy * Lb / 2, 0), L(sx * W / 2, sy * Lb / 2, h), 0.11, col=wood, sides=8)
    obox(b, 'paint', L(0, -Lb / 2, 2.4), L.yaw, W / 2, 0.06, 0.6, col=wood)
    obox(b, 'paint', L(0, Lb / 2, 1.8), L.yaw, W / 2, 0.06, 0.45, col=wood)
    for sx in (-1, 1):
        obox(b, 'paint', L(sx * W / 2, 0, 1.0), L.yaw, 0.06, Lb / 2, 0.25, col=wood)
    obox(b, 'ticking', L(0, 0.1, 1.45), L.yaw, W / 2 - 0.1, Lb / 2 - 0.1, 0.25, col=(1, 1, 1), tile=0.6)    # straw tick
    bk = 'pointblanket' if blanket == 'point' else 'blanket'
    obox(b, bk, L(0, 0.5, 1.75), L.yaw, W / 2 + 0.05, Lb / 2 - 0.5, 0.06, col=(1, 1, 1), tile=1.9, grain=1)   # wool blanket
    for sx in (-1, 1):   # blanket hanging down the sides
        obox(b, bk, L(sx * (W / 2 + 0.08), 0.5, 1.35), L.yaw, 0.03, Lb / 2 - 0.5, 0.42, col=(1, 1, 1), tile=1.9, grain=1)
    obox(b, 'ticking', L(0, -Lb / 2 + 0.75, 1.86), L.yaw, W / 2 - 0.6, 0.4, 0.12, col=(1, 1, 1), tile=0.5)     # pillow
    if robe:
        c = L(0.2, 1.4, 1.84)
        skin(b, 'buffalo', c[0], c[1], c[2], 4.6, 3.6, L.yaw + 0.3, rng)


def washstand(b, x, y, yaw):
    L = Local(x, y, FL, yaw)
    col = (0.44, 0.32, 0.2)
    obox(b, 'paint', L(0, 0, 2.45), L.yaw, 1.25, 0.7, 0.05, col=col)
    for sx in (-1, 1):
        for sy in (-1, 1):
            obox(b, 'paint', L(sx * 1.15, sy * 0.6, 1.2), L.yaw, 0.06, 0.06, 1.2, col=col)
    obox(b, 'paint', L(0, 0, 0.6), L.yaw, 1.15, 0.6, 0.04, col=col)
    obox(b, 'paint', L(0, 0.68, 2.8), L.yaw, 1.25, 0.04, 0.3, col=col)
    lathe(b, 'ware', L(-0.2, 0, 2.5), [(0.0, 0), (0.45, 0.04), (0.6, 0.3), (0.62, 0.32)], col=(0.93, 0.92, 0.88), sides=20)   # basin
    lathe(b, 'ware', L(-0.2, 0, 2.54), [(0.2, 0), (0.28, 0.35), (0.22, 0.7), (0.16, 0.85), (0.24, 1.0)], col=(0.93, 0.92, 0.88), sides=16)  # ironstone pitcher
    obox(b, 'cloth', L(0.85, 0.1, 2.52), L.yaw, 0.3, 0.45, 0.03, col=(0.9, 0.88, 0.82))


def trunk(b, x, y, yaw, lettered=True):
    """T.R.'s trunk: wicker body covered in duck, lettered 'T.R.' (NPS; survives at TRNP). Size estimated."""
    L = Local(x, y, FL, yaw)
    obox(b, 'duck', L(0, 0, 0.8), L.yaw, 1.3, 0.8, 0.8, col=(0.95, 0.95, 0.95), tile=0.5)
    obox(b, 'duck', L(0, 0, 1.65), L.yaw, 1.32, 0.82, 0.08, col=(0.85, 0.85, 0.85), tile=0.5)
    for sx in (-0.8, 0.8):
        obox(b, 'rubber', L(sx, 0, 0.82), L.yaw, 0.06, 0.82, 0.82, col=(0.25, 0.17, 0.1))
    if lettered:
        for k, w in ((-0.25, 0.08), (0.05, 0.08)):
            obox(b, 'paint', L(k, -0.81, 1.0), L.yaw, w, 0.01, 0.2, col=(0.1, 0.1, 0.1))


def rubber_tub(b, x, y):
    """India-rubber folding bathtub (T.R., Autobiography). Form is conjecture: a collapsible rubber sitz-bath on a frame."""
    lathe(b, 'rubber', (x, y, FL), [(0.0, 0.0), (1.2, 0.02), (1.35, 0.6), (1.45, 0.95), (1.5, 1.0)], col=(0.12, 0.09, 0.07), sides=20)


def coats_on_horns(b, x, y, z, yaw, rng, kinds=('wolf', 'coon')):
    """Deer horns nailed to the wall/joists hung with wolf-skin and coon-skin overcoats and fur caps (HTR 1885)."""
    import props
    L = Local(x, y, z, yaw)
    props.antler_rack(b, L(0, 0, 0), tuple(Matrix.Rotation(L.yaw, 3, 'Z') @ Vector((0, -1, 0))), scale=0.45, rng=rng, kind='deer', skull=False)
    for k, kind in enumerate(kinds):
        c = Vector(L(-0.4 + k * 0.8, -0.35, -2.0))
        lathe(b, kind, tuple(c), [(0.55, 0.0), (0.6, 0.8), (0.5, 1.6), (0.32, 2.0), (0.12, 2.15)], sides=12)
    lathe(b, 'wolf', L(0.0, -0.3, 0.1), [(0.3, 0), (0.32, 0.25), (0.0, 0.4)], sides=12)


def cradle(b, x, y, yaw):
    """Sewall built a cradle big enough for both babies, born August 1886 (NPS 1969)."""
    L = Local(x, y, FL, yaw)
    col = (0.55, 0.42, 0.28)
    for sx in (-1, 1):
        obox(b, 'pine', L(sx * 1.25, 0, 0.9), L.yaw, 0.05, 1.6, 0.6, col=col)
    for sy in (-1, 1):
        obox(b, 'pine', L(0, sy * 1.6, 1.0), L.yaw, 1.25, 0.05, 0.7, col=col)
    obox(b, 'pine', L(0, 0, 0.35), L.yaw, 1.25, 1.6, 0.04, col=col)
    for sy in (-1.1, 1.1):
        obox(b, 'pine', L(0, sy, 0.15), L.yaw, 1.5, 0.1, 0.15, col=col)
    obox(b, 'cloth', L(0, 0, 0.55), L.yaw, 1.15, 1.5, 0.12, col=(0.85, 0.82, 0.74))


def saddle_rack(b, x, y, yaw, rng):
    import props
    L = Local(x, y, FL, yaw)
    obox(b, 'pine', L(0, 0, 2.6), L.yaw, 1.6, 0.12, 0.08, col=(0.6, 0.5, 0.36))
    for sx in (-1.4, 1.4):
        obox(b, 'pine', L(sx, 0, 1.3), L.yaw, 0.08, 0.6, 1.3, col=(0.6, 0.5, 0.36))
    c = L(-0.3, 0, 1.2)
    props.saddle(b, c, L.yaw + math.pi / 2, rng)


def bench(b, x, y, yaw, Lx=5.0):
    L = Local(x, y, FL, yaw)
    obox(b, 'pine', L(0, 0, 1.45), L.yaw, Lx / 2, 0.5, 0.06, col=(0.6, 0.48, 0.34))
    for sx in (-1, 1):
        obox(b, 'pine', L(sx * (Lx / 2 - 0.3), 0, 0.7), L.yaw, 0.05, 0.45, 0.7, col=(0.6, 0.48, 0.34))


def bucket(b, x, y, col=(0.5, 0.48, 0.45), mk='tin'):
    lathe(b, mk, (x, y, FL), [(0.0, 0), (0.42, 0.01), (0.5, 0.9), (0.52, 0.92)], col=col, sides=16)


def checkerboard(b, x, y, z, yaw):
    L = Local(x, y, z, yaw)
    for i in range(8):
        for j in range(8):
            c = (0.12, 0.08, 0.06) if (i + j) % 2 else (0.75, 0.62, 0.45)
            obox(b, 'paint', L((i - 3.5) * 0.15, (j - 3.5) * 0.15, 0.01), L.yaw, 0.075, 0.075, 0.01, col=c)
    for k in range(10):
        i, j = k % 4 * 2 + (k // 4) % 2, k // 4
        lathe(b, 'paint', L((i - 3.5) * 0.15, (j - 3.5) * 0.15, 0.02), [(0.055, 0), (0.055, 0.03), (0.0, 0.035)], col=(0.6, 0.1, 0.06), sides=10)


def trapdoor(b, x0, y0):
    """Trapdoor in the kitchen floor to the cellar passage and T.R.'s darkroom (Taylor 1959)."""
    box(b, 'door', x0, y0, FL + 0.001, x0 + 2.5, y0 + 3.0, FL + 0.02, col=(0.85, 0.8, 0.72), tile=1.2, grain=1)
    box(b, 'iron', x0 + 1.1, y0 + 2.6, FL + 0.02, x0 + 1.4, y0 + 2.7, FL + 0.05)


# ----------------------------------------------------------------- rooms
def sitting_room(b, rng):
    import props
    fireplace(b, rng)
    # elk hides and wolf skins on the floor in front of the hearthstone (RLHT p.36)
    skin(b, 'elkhide', 19.6, 23.1, FL, 6.5, 5.2, 0.15, rng)
    skin(b, 'wolf', 21.8, 21.0, FL + 0.03, 4.6, 2.4, 1.1, rng)
    skin(b, 'bear', 24.0, 26.0, FL, 5.8, 4.6, -0.4, rng, head=True)
    # T.R.'s rocking chair by the fire, a second rocker
    props.windsor_rocker(b, (19.5, 20.6, FL), math.radians(-120), rng)
    props.windsor_rocker(b, (20.0, 26.4, FL), math.radians(-60), rng)
    # writing table under the east window (E window at Y 27.0) where he wrote by day
    writing_table(b, 27.6, 27.0, math.radians(-90), rng)
    side_chair(b, 26.2, 27.0, face_yaw(26.2, 27.0, 27.6, 27.0), rng)
    # rough board book shelves on the south partition
    bookshelf(b, 24.0, 14.05, 0.0, rng, W=4.6, n=3)
    # small table with the checkerboard (HTR: 'the men play checkers or chess, in the fire light')
    table(b, 22.6, 18.0, 0.2, 2.2, 2.2, H=2.35, col=(0.5, 0.38, 0.26))
    checkerboard(b, 22.6, 18.0, FL + 2.38, 0.2)
    side_chair(b, 21.3, 17.8, face_yaw(21.3, 17.8, 22.6, 18.0), rng)
    side_chair(b, 23.9, 18.3, face_yaw(23.9, 18.3, 22.6, 18.0), rng)
    # deer horns on the walls and thrust into the joists, hung with fur coats and caps
    coats_on_horns(b, 18.6, 31.4, FL + 6.4, 0.0, rng)
    coats_on_horns(b, 28.9, 16.8, FL + 6.2, math.radians(-90), rng, kinds=('wolf',))
    for yy in (18.5, 29.5):
        props.antler_rack(b, (28.95, yy, FL + 6.6), (-1, 0, 0), scale=0.42, rng=rng, kind='deer', skull=True, wall=0.22)
    # rifles standing in the corners
    props.rifle(b, (28.9, 30.9, FL + 0.05), (28.75, 31.25, FL + 4.4), rng)
    props.rifle(b, (28.9, 14.6, FL + 0.05), (28.7, 14.2, FL + 4.3), rng)
    lamp(b, (22.6 + 0.6, 18.0 - 0.5, FL + 2.37))


def tr_bedroom(b, rng):
    bed(b, 25.0, 5.3, 0.0, rng, W=4.2, Lb=6.4)
    washstand(b, 19.4, 4.0, math.radians(90))
    trunk(b, 22.0, 12.6, 0.0)
    rubber_tub(b, 20.3, 9.8)
    side_chair(b, 28.2, 11.5, face_yaw(28.2, 11.5, 25.0, 8.0), rng)
    lantern(b, (19.5, 4.6, FL + 2.5))
    # clothes hooks (Taylor: 'metal clothes hooks, fancy') with a canvas hunting coat and hat
    for k, yy in enumerate((9.6, 11.1)):                                 # clear of the east window
        box(b, 'iron', 29.12, yy - 0.03, FL + 5.5, 29.17, yy + 0.03, FL + 5.6)
    detail.coat(b, 'duckcoat', (28.98, 9.6, FL + 5.52), math.radians(-90), length=2.7, width=0.8, rng=rng, wall=0.17, collar=False)
    detail.felt_hat(b, (29.12, 11.1, FL + 5.15), up=(-1, 0, 0))


def kitchen(b, rng):
    cookstove(b, 11.0, 23.0, math.radians(-90), rng)                       # backed against the chimney, pipe into the thimble
    table(b, 5.0, 25.0, 0.0, 6.0, 3.0, H=2.45, col=(0.66, 0.55, 0.4))
    bench(b, 5.0, 23.0, 0.0, 5.0)
    plate_rack_cupboard(b, 5.2, 16.4, math.radians(180), rng)
    detail.pie_tins(b, (4.5, 24.3, FL + 2.45))
    detail.yellowware_bowl(b, (5.5, 25.7, FL + 2.45))
    bucket(b, 1.5, 31.5); bucket(b, 2.6, 31.8, col=(0.4, 0.3, 0.2), mk='paint')
    lathe(b, 'ware', (1.4, 29.5, FL), [(0.0, 0), (0.6, 0.02), (0.7, 1.6), (0.55, 1.75)], col=(0.6, 0.55, 0.45), sides=16)   # crock
    lathe(b, 'tin', (2.6, 29.0, FL), [(0.0, 0), (0.42, 0.01), (0.45, 0.85), (0.47, 0.9)], col=(0.65, 0.6, 0.45), sides=14)   # Fairbank lard pail
    trapdoor(b, 7.0, 29.5)
    lantern(b, (6.4, 24.1, FL + 2.45), lit=True)                          # on the table (was floating off its end)
    # wood box by the stove
    box(b, 'pine', 11.0, 26.0, FL, 13.6, 27.8, FL + 2.0, col=(0.6, 0.48, 0.34))
    for k in range(8):
        cyl(b, 'bark', (11.3 + k * 0.28, 26.3, FL + 1.6 + (k % 2) * 0.2), (11.3 + k * 0.28, 27.5, FL + 1.6 + (k % 2) * 0.2), 0.14)


def dining_room(b, rng):
    table(b, 7.0, 7.5, math.radians(90), 7.0, 3.4, H=2.45, col=(0.6, 0.48, 0.34), cloth=(0.7, 0.65, 0.5))
    for k, (dx, dy, yaw) in enumerate(((-1.5, -2.2, 0), (1.5, -2.2, 0), (-1.5, 2.2, 180), (1.5, 2.2, 180), (-3.6, 0, -90), (3.6, 0, 90))):
        side_chair(b, 7.0 + dy, 7.5 + dx, face_yaw(7.0 + dy, 7.5 + dx, 7.0, 7.5), rng)
    for k in range(6):
        a = k * math.pi / 3
        px, py = 7.0 + 1.0 * math.cos(a) * 1.2, 7.5 + 2.2 * math.sin(a) * 0.9
        plate(b, (px, py, FL + 2.47), 0.37)
        cup(b, (px - 0.62 * math.sin(a), py + 0.62 * math.cos(a), FL + 2.47), handle_angle=a)
    plate_rack_cupboard(b, 2.18, 11.0, math.radians(90), rng)


def north_rooms(b, rng):
    # Bamie's room (1890) / guest room
    bed(b, 25.5, 37.5, 0.0, rng, blanket='point', robe=False)
    washstand(b, 19.3, 41.5, math.radians(90))
    # NW room: Sewall family — bed, twin cradle, trunk
    bed(b, 4.4, 52.0, math.radians(-90), rng, blanket='point', robe=False)
    cradle(b, 10.0, 55.5, 0.0)
    trunk(b, 10.5, 48.0, 0.0, lettered=False)
    # NE work room: saddle rack, tack, lumber
    saddle_rack(b, 25.0, 57.5, 0.0, rng)
    bench(b, 20.0, 46.0, 0.0, 6.0)
    # west work room: ironing table, sad irons on a shelf, wash tub
    table(b, 7.0, 40.0, 0.0, 5.0, 2.2, H=2.6, col=(0.65, 0.55, 0.42), cloth=(0.85, 0.83, 0.78))
    for k in range(3):
        box(b, 'castiron', 6.0 + k * 0.6, 40.2, FL + 2.62, 6.4 + k * 0.6, 40.45, FL + 2.85, col=(1, 1, 1))
    lathe(b, 'paint', (3.0, 36.5, FL), [(0.0, 0), (1.0, 0.02), (1.15, 1.0), (1.18, 1.05)], col=(0.45, 0.35, 0.22), sides=18)


# ----------------------------------------------------------------- small things that make the rooms lived in
def can(b, c, r=0.17, h=0.38):
    """Tin can with a paper label (Taylor: oyster, milk, sardine and tomato cans; a Fairbank lard pail)."""
    c = Vector(c)
    b.tube('tinlabel', [m(c), m(c + Vector((0, 0, h)))], r * FT, sides=12, tile=0.33, cap=False)
    lathe(b, 'tin', tuple(c), [(r, 0), (r, 0.02)], col=(0.7, 0.7, 0.68), sides=12)
    lathe(b, 'tin', tuple(c + Vector((0, 0, h - 0.02))), [(r, 0), (r, 0.02), (0.0, 0.025)], col=(0.7, 0.7, 0.68), sides=12)


def shelf_with(b, x0, y0, x1, y1, z, rng, items=8):
    box(b, 'pine', x0, y0, z - 0.06, x1, y1, z, col=(0.72, 0.62, 0.48), tile=1.2, grain=0 if abs(x1 - x0) > abs(y1 - y0) else 1)
    for k in range(items):
        t = (k + 0.5) / items
        x = x0 + (x1 - x0) * t; y = y0 + (y1 - y0) * t
        cx = (x0 + x1) / 2 if abs(x1 - x0) < abs(y1 - y0) else x; cy = (y0 + y1) / 2 if abs(x1 - x0) > abs(y1 - y0) else y
        if rng.random() < 0.65:
            can(b, (cx, cy, z), r=rng.choice([0.14, 0.17, 0.2]), h=rng.choice([0.3, 0.38, 0.45]))
        else:
            lathe(b, 'ware', (cx, cy, z), [(0.12, 0), (0.17, 0.1), (0.17, 0.45), (0.1, 0.55), (0.06, 0.62)], col=rng.choice([(0.55, 0.45, 0.32), (0.3, 0.42, 0.3), (0.85, 0.83, 0.78)]), sides=12)


def skillet(b, c, r=0.45):
    c = Vector(c)
    lathe(b, 'castiron', tuple(c), [(r - 0.04, 0), (r, 0.12), (r + 0.02, 0.16)], col=(0.9, 0.9, 0.9), sides=18)
    cyl(b, 'castiron', tuple(c + Vector((r, 0, 0.12))), tuple(c + Vector((r + 0.6, 0, 0.18))), 0.05, col=(0.9, 0.9, 0.9), sides=6)


def kettle(b, c):
    c = Vector(c)
    lathe(b, 'castiron', tuple(c), [(0.3, 0), (0.42, 0.25), (0.38, 0.45), (0.2, 0.55), (0.12, 0.6)], col=(1, 1, 1), sides=16)
    cyl(b, 'castiron', tuple(c + Vector((0.35, 0, 0.25))), tuple(c + Vector((0.6, 0, 0.5))), 0.05, col=(1, 1, 1), sides=6)
    b.tube('iron', [m(c + Vector((-0.3, 0, 0.55))), m(c + Vector((0, 0, 0.95))), m(c + Vector((0.3, 0, 0.55)))], 0.02 * FT, sides=4)


def coffee_mill(b, c):
    """Box coffee mill (lap/wall mill) — standard in ranch kitchens; coffee came as green or roasted beans."""
    c = Vector(c)
    box(b, 'pine', c.x - 0.25, c.y - 0.25, c.z, c.x + 0.25, c.y + 0.25, c.z + 0.45, col=(0.55, 0.38, 0.22))
    lathe(b, 'castiron', tuple(c + Vector((0, 0, 0.45))), [(0.2, 0), (0.18, 0.12), (0.05, 0.16)], col=(1, 1, 1), sides=12)
    cyl(b, 'iron', tuple(c + Vector((0, 0, 0.62))), tuple(c + Vector((0.3, 0, 0.66))), 0.02)
    box(b, 'pine', c.x - 0.12, c.y - 0.27, c.z + 0.1, c.x + 0.12, c.y - 0.25, c.z + 0.2, col=(0.4, 0.28, 0.16))


def flour_barrel(b, c):
    c = Vector(c)
    lathe(b, 'pine', tuple(c), [(0.75, 0), (0.85, 1.25), (0.75, 2.5)], col=(0.6, 0.48, 0.34), sides=18)
    for z in (0.3, 1.25, 2.2):
        lathe(b, 'iron', tuple(c + Vector((0, 0, z))), [(0.8 + (0.04 if z == 1.25 else 0), 0), (0.8 + (0.04 if z == 1.25 else 0), 0.1)], sides=18)
    lathe(b, 'sacking', tuple(c + Vector((0, 0, 2.5))), [(0.72, 0), (0.7, 0.05), (0.0, 0.08)], col=(1, 1, 1), sides=18)


def sack(b, c, h=1.6):
    lathe(b, 'sacking', c, [(0.55, 0), (0.62, 0.3), (0.6, h * 0.7), (0.35, h), (0.12, h + 0.15)], col=(1, 1, 1), sides=14)


def boots(b, c, yaw):
    L = Local(c[0], c[1], c[2], yaw)
    for s_ in (-0.25, 0.25):
        obox(b, 'leather', L(s_, 0.25, 0.08), L.yaw, 0.15, 0.45, 0.08, col=(1, 1, 1))
        cyl(b, 'leather', L(s_, -0.1, 0.0), L(s_, -0.12, 1.25), 0.2, col=(1, 1, 1), sides=10, r1=0.18)


def hat(b, c, col=(0.42, 0.36, 0.28)):
    lathe(b, 'cloth', c, [(0.75, 0), (0.75, 0.03), (0.32, 0.05), (0.3, 0.45), (0.0, 0.5)], col=col, sides=18)


def gun_belt(b, c, yaw):
    """Cartridge belt and holstered revolver hung on a horn/peg."""
    L = Local(c[0], c[1], c[2], yaw)
    b.tube('leather', [m(L(-0.5, 0, 0)), m(L(-0.45, -0.05, -1.0)), m(L(0, -0.08, -1.3)), m(L(0.45, -0.05, -1.0)), m(L(0.5, 0, 0))], 0.12 * FT, sides=6)
    obox(b, 'leather', L(0.3, -0.12, -1.1), L.yaw, 0.12, 0.05, 0.4, col=(0.8, 0.8, 0.8))
    cyl(b, 'iron', L(0.3, -0.15, -0.75), L(0.33, -0.15, -0.45), 0.05)


def lariat(b, c, yaw):
    """Coiled rawhide/grass rope hung on a peg."""
    L = Local(c[0], c[1], c[2], yaw)
    for k in range(6):
        r = 0.55 + 0.03 * k
        pts = [m(L(r * math.cos(t), -0.05 - 0.02 * k, -0.6 + r * math.sin(t))) for t in [i * 2 * math.pi / 20 for i in range(21)]]
        b.tube('pole', pts, 0.03 * FT, sides=5, cap=False)


def view_camera(b, c, yaw):
    """Field view camera on a wooden tripod. T.R. photographed the ranch himself and kept a darkroom in the cellar
    (Taylor; Mattison); the camera's make is not known, so this is a generic 5x8 field camera of the 1880s."""
    L = Local(c[0], c[1], c[2], yaw)
    for a in (0, 2.1, 4.2):
        cyl(b, 'pine', L(0, 0, 4.4), L(1.3 * math.cos(a), 1.3 * math.sin(a), 0), 0.06, col=(0.62, 0.45, 0.28), sides=6)
    obox(b, 'paint', L(0, 0, 4.85), L.yaw, 0.45, 0.4, 0.4, col=(0.45, 0.28, 0.16))           # rear standard / box
    obox(b, 'cloth', L(0, -0.55, 4.85), L.yaw, 0.38, 0.25, 0.36, col=(0.12, 0.1, 0.1))         # bellows
    obox(b, 'paint', L(0, -0.85, 4.85), L.yaw, 0.32, 0.06, 0.32, col=(0.45, 0.28, 0.16))      # front standard
    cyl(b, 'nickel', L(0, -0.9, 4.85), L(0, -1.15, 4.85), 0.12, col=(0.7, 0.62, 0.4), sides=14)   # brass lens
    obox(b, 'cloth', L(0, 0.55, 4.95), L.yaw, 0.5, 0.25, 0.45, col=(0.08, 0.08, 0.08))         # focusing cloth


def chamber_pot(b, c):
    lathe(b, 'ware', c, [(0.25, 0), (0.38, 0.25), (0.36, 0.5), (0.42, 0.55)], col=(0.93, 0.92, 0.88), sides=16)


def candlestick(b, c):
    c = Vector(c)
    lathe(b, 'tin', tuple(c), [(0.22, 0), (0.22, 0.03), (0.05, 0.06), (0.05, 0.25), (0.08, 0.27)], col=(0.65, 0.65, 0.6), sides=12)
    cyl(b, 'ware', tuple(c + Vector((0, 0, 0.27))), tuple(c + Vector((0, 0, 0.75))), 0.04, col=(0.9, 0.87, 0.78), sides=8)


def towel(b, c, yaw, w=0.8, h=1.2, col=(0.9, 0.88, 0.82)):
    L = Local(c[0], c[1], c[2], yaw)
    obox(b, 'ticking', L(0, 0, -h / 2), L.yaw, w / 2, 0.02, h / 2, col=col, tile=0.4)


def details(b, rng):
    import props
    # ---- sitting room
    view_camera(b, (25.6, 22.2, FL), math.radians(200))
    gun_belt(b, (29.1, 19.0, FL + 5.6), math.radians(-90))
    lariat(b, (27.0, 14.1, FL + 6.0), math.radians(180))
    detail.felt_hat(b, (27.0, 28.2, FL + 2.475))                     # on the writing table
    box(b, 'paper', 22.2, 17.7, FL + 2.38, 22.9, 18.3, FL + 2.39, col=(0.82, 0.78, 0.68))     # newspaper by the checkers
    for k in range(4):   # split firewood stacked beside the hearth
        for j in range(3):
            cyl(b, 'bark', (16.0 + j * 0.42, 25.6, FL + 0.2 + k * 0.38), (16.0 + j * 0.42, 27.2, FL + 0.2 + k * 0.38), 0.18)
    # buffalo robe thrown over T.R.'s rocker
    skin(b, 'buffalo', 19.2, 20.9, FL + 1.6, 3.2, 2.2, 1.0, rng, legs=False)
    # ---- T.R.'s bedroom
    boots(b, (23.0, 9.0, FL), 0.0)
    chamber_pot(b, (27.2, 2.6, FL))
    candlestick(b, (28.2, 11.5, FL + 1.48))
    towel(b, (19.35, 3.0, FL + 2.45), math.radians(90))
    for k in range(3):
        obox(b, 'books', (27.9 + 0.02 * k, 11.3, FL + 1.53 + 0.08 * k), 0.3 * k, 0.25, 0.35, 0.04, col=(1, 1, 1), tile=0.27)
    obox(b, 'duck', (26.0, 12.7, FL + 0.5), 0.0, 0.7, 0.35, 0.5, col=(0.7, 0.62, 0.48), tile=0.5)   # canvas war bag
    # ---- kitchen
    kettle(b, (10.55, 23.1, FL + 2.57))
    detail.coffee_pot(b, (10.55, 22.3, FL + 2.57), angle=math.radians(-90))
    skillet(b, (11.45, 23.1, FL + 2.57), angle=math.radians(-90))
    coffee_mill(b, (3.4, 25.3, FL + 2.47))
    flour_barrel(b, (1.8, 21.0, FL))
    sack(b, (3.4, 20.7, FL)); sack(b, (3.0, 21.9, FL), h=1.2)
    shelf_with(b, IX0 + 0.05, 27.5, IX0 + 1.0, 33.5, FL + 4.6, rng, items=9)
    shelf_with(b, IX0 + 0.05, 27.5, IX0 + 1.0, 33.5, FL + 5.7, rng, items=8)
    bucket(b, 5.2, 33.2); cyl(b, 'tin', (5.2, 33.2, FL + 0.9), (5.7, 33.6, FL + 1.3), 0.03, col=(0.7, 0.7, 0.68))   # dipper
    detail.dish_pan(b, (7.1, 25.4, FL + 2.45))
    towel(b, (13.85, 24.6, FL + 3.4), math.radians(90), col=(0.86, 0.84, 0.8))
    can(b, (2.2, 33.0, FL), r=0.3, h=0.9)                         # kerosene can
    # ---- dining room: lamp and coffee pot on the table
    lamp(b, (7.0, 7.5, FL + 2.475))
    detail.coffee_pot(b, (7.6, 6.6, FL + 2.475), angle=math.radians(150))
    detail.sugar_bowl(b, (6.4, 8.3, FL + 2.475))
    # ---- north rooms: hats and coats on pegs, sewing basket, child's toy (Taylor: carved wooden toy)
    hat(b, (11.0, 48.0, FL + 1.68), col=(0.25, 0.22, 0.2))
    lathe(b, 'pine', (6.5, 56.5, FL), [(0.0, 0), (0.45, 0.02), (0.5, 0.35), (0.52, 0.38)], col=(0.65, 0.52, 0.32), sides=14)
    obox(b, 'pine', (9.0, 54.0, FL + 0.12), 0.4, 0.3, 0.12, 0.12, col=(0.7, 0.55, 0.35))


def interior_lights():
    """Daylight through the windows + warm lamplight and firelight for the interior renders.
    Each window gets an area light just inside the glass, facing into the room (sky light through the opening)."""
    import house
    for wall, ops in house.OPENINGS.items():
        org, u, n, L = house.WALLS[wall]
        for kind, c in ops:
            if kind != 'w':
                continue
            p = Vector(house.wpt(wall, c, -TW - 0.15, (house.WIN['sill'] + house.WIN['head']) / 2))
            ld = bpy.data.lights.new(f'win_{wall}_{c}', 'AREA'); ld.shape = 'RECTANGLE'
            ld.size = house.WIN['w'] * FT; ld.size_y = (house.WIN['head'] - house.WIN['sill']) * FT
            ld.energy = 40; ld.color = (0.92, 0.95, 1.0)
            ob = bpy.data.objects.new(ld.name, ld); ob.location = m(p)
            ob.rotation_euler = (-Vector(n)).to_track_quat('-Z', 'Y').to_euler()
            bpy.context.scene.collection.objects.link(ob)
    for name, loc, energy, color, size in (('fire_glow', (15.0, 23.0, FL + 0.7), 35, (1.0, 0.42, 0.12), 0.4),
                                           ('lamp_desk', (28.6, 27.0, FL + 3.6), 35, (1.0, 0.75, 0.45), 0.15),
                                           ('lamp_table', (23.2, 17.5, FL + 3.4), 25, (1.0, 0.75, 0.45), 0.15),
                                           ('kitchen_lantern', (6.4, 24.1, FL + 3.0), 20, (1.0, 0.75, 0.45), 0.15)):
        ld = bpy.data.lights.new(name, 'POINT'); ld.energy = energy; ld.color = color; ld.shadow_soft_size = size * FT
        ob = bpy.data.objects.new(name, ld); ob.location = m(loc); bpy.context.scene.collection.objects.link(ob)


def build_interior(b, rng, mats):
    b.group = 'interior'
    floor_and_ceiling(b, rng)
    b.group = 'interior'
    partitions(b, rng)
    sitting_room(b, rng)
    tr_bedroom(b, rng)
    kitchen(b, rng)
    dining_room(b, rng)
    north_rooms(b, rng)
    details(b, rng)


import detail                       # draft 5: detailed props replace the first-pass builders above
detail.install(globals())
