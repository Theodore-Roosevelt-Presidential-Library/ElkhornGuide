import sys, math, random, json, os
sys.path.insert(0, os.path.dirname(__file__))
import bpy
from mathutils import Vector
import lib, house, props, outbuildings
from lib import FT

OUT = lib.M + '/out'
os.makedirs(OUT, exist_ok=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def world(hdri='kloofendal_48d_partly_cloudy_puresky', strength=0.9, rot=0.0):
    w = bpy.data.worlds.new('sky'); bpy.context.scene.world = w; w.use_nodes = True
    nt = w.node_tree; bg = nt.nodes['Background']
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(lib.M + f'/hdri/{hdri}.hdr')
    mp = nt.nodes.new('ShaderNodeMapping'); tc = nt.nodes.new('ShaderNodeTexCoord')
    mp.inputs['Rotation'].default_value = (0, 0, rot)
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], env.inputs['Vector'])
    nt.links.new(env.outputs['Color'], bg.inputs['Color']); bg.inputs['Strength'].default_value = strength


def sun(az_deg, el_deg, energy=4.0):
    ld = bpy.data.lights.new('sun', 'SUN'); ld.energy = energy; ld.angle = math.radians(0.6)
    ld.color = (1.0, 0.96, 0.9)
    ob = bpy.data.objects.new('sun', ld); bpy.context.scene.collection.objects.link(ob)
    az = math.radians(az_deg); el = math.radians(el_deg)
    d = Vector((math.sin(az) * math.cos(el), math.cos(az) * math.cos(el), math.sin(el)))   # direction TO the sun
    ob.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()


def ground(b, mats, size_ft=1000):
    b.group = 'ground'
    s = size_ft / 2
    cx, cy = 15, 30
    b.quad_auto('grass', [lib.Vector(((cx - s) * FT, (cy - s) * FT, 0)), lib.Vector(((cx + s) * FT, (cy - s) * FT, 0)),
                         lib.Vector(((cx + s) * FT, (cy + s) * FT, 0)), lib.Vector(((cx - s) * FT, (cy + s) * FT, 0))], 2.0)
    # beaten earth around the house (scoria spread between house, shed, well) - slightly above grass
    b.quad_auto('ground', [lib.Vector((-12 * FT, -14 * FT, 0.004)), lib.Vector((44 * FT, -14 * FT, 0.004)),
                          lib.Vector((44 * FT, 72 * FT, 0.004)), lib.Vector((-12 * FT, 72 * FT, 0.004))], 2.5)


def camera(name, pos_ft, look_bearing, hfov, pitch=0.0, res=(1131, 800)):
    cd = bpy.data.cameras.new(name); cd.sensor_fit = 'HORIZONTAL'; cd.sensor_width = 36
    cd.angle = math.radians(hfov)
    ob = bpy.data.objects.new(name, cd); bpy.context.scene.collection.objects.link(ob)
    ob.location = Vector(pos_ft) * FT
    b = math.radians(look_bearing)
    d = Vector((math.sin(b), math.cos(b), math.tan(math.radians(pitch))))
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()
    return ob


def prairie_material(mats):
    """Grass albedo broken up with large-scale noise toward dry soil + late-summer straw tones."""
    mt = mats['grass']; nt = mt.node_tree
    bsdf = nt.nodes['Principled BSDF']
    src = bsdf.inputs['Base Color'].links[0].from_socket
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 0.04; nz.inputs['Detail'].default_value = 6
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    nz2 = nt.nodes.new('ShaderNodeTexNoise'); nz2.inputs['Scale'].default_value = 0.6; nz2.inputs['Detail'].default_value = 4
    nt.links.new(tc.outputs['Object'], nz2.inputs['Vector'])
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[0].color = (0.30, 0.28, 0.17, 1)
    ramp.color_ramp.elements[1].position = 0.7; ramp.color_ramp.elements[1].color = (0.47, 0.41, 0.26, 1)
    nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac'])
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MIX'
    mix.inputs['Factor'].default_value = 0.35
    nt.links.new(src, mix.inputs[6]); nt.links.new(ramp.outputs['Color'], mix.inputs[7])
    mul = nt.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY_ADD'
    mul.inputs[1].default_value = 0.5; mul.inputs[2].default_value = 0.78
    nt.links.new(nz2.outputs['Fac'], mul.inputs[0])
    mix2 = nt.nodes.new('ShaderNodeMix'); mix2.data_type = 'RGBA'; mix2.blend_type = 'MULTIPLY'; mix2.inputs['Factor'].default_value = 1.0
    nt.links.new(mix.outputs[2], mix2.inputs[6]); nt.links.new(mul.outputs[0], mix2.inputs[7])
    nt.links.new(mix2.outputs[2], bsdf.inputs['Base Color'])


def build_all(seed=7, site=True):
    reset()
    mats = lib.build_materials()
    mats['curtain'] = lib.flat_material('curtain', lib.srgb('#d9d4c8'), 0.9)
    b = lib.Builder(mats, seed)
    rng = random.Random(seed)
    house.build_house(b, rng)
    props.build_props(b, rng)
    if site:
        outbuildings.build_outbuildings(b, random.Random(seed + 1))
    ground(b, mats)
    prairie_material(mats)
    objs = b.emit()
    return mats, objs


def render(cam, path, samples=48, res=(1131, 800)):
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.device = 'CPU'
    sc.render.threads_mode = 'AUTO'
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'AgX'
    sc.view_settings.look = 'AgX - Base Contrast' if 'AgX - Base Contrast' in [i.identifier for i in sc.view_settings.bl_rna.properties['look'].enum_items] else 'None'
    sc.render.image_settings.file_format = 'JPEG'
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    which = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['veranda']
    mats, objs = build_all(site=os.environ.get('SITE', '1') == '1')
    print('objects', len(objs), 'faces', sum(len(o.data.polygons) for o in objs))
    world(strength=0.6)
    sun(135, 40, 3.6)
    bpy.context.scene.view_settings.exposure = -0.3
    cams = {
        'veranda': camera('cam_veranda', (40.71, -14.69, 5.0), 338.44, 39.3),
        'house_se': camera('cam_house_se', (102.0, -98.0, 5.0), 326, 48.0),
        'site': camera('cam_site', (60.0, -700.0, 330.0), 352, 55.0, pitch=-24),
        'barn': camera('cam_barn', (-60.0, 120.0, 12.0), 320, 55.0, pitch=-4),
        'stables': camera('cam_stables', (-80.0, 118.0, 5.0), 356, 52.0),
        'smithy': camera('cam_smithy', (200.0, -270.0, 10.0), 290, 55.0, pitch=-3),
        'oblique': camera('cam_oblique', (75.0, -55.0, 22.0), 318, 50.0, pitch=-12),
        'river': camera('cam_river', (15 + 600 * math.sin(math.radians(106)), 30 + 600 * math.cos(math.radians(106)), 5.0), 286, 12.0),
    }
    for w in which:
        render(cams[w], OUT + f'/{w}.jpg', samples=int(os.environ.get('SAMPLES', 32)),
               res=(int(os.environ.get('RX', 1131)), int(os.environ.get('RY', 800))))
    bpy.ops.wm.save_as_mainfile(filepath=lib.M + '/out/elkhorn.blend')
